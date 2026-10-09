"""
cd /home/flexxource/hungvu/version1.0
python3 -m panel_control.panel_test probe      # done, exits 1 on the stuck button
python3 -m panel_control.panel_test leds       # all 16 on, then one at a time
python3 -m panel_control.panel_test buttons    # lights each LED, waits for its button
python3 -m panel_control.panel_test monitor    # press anything, prints the panel ID
python3 -m panel_control.panel_test worker     # exercises the real panel_worker queues
"""
from __future__ import annotations

import queue
import threading
from collections.abc import Callable, Iterable

from smbus2 import SMBus, i2c_msg

from configuration import machine


# Đấu dây nằm ở configuration/machine.py. Tên cũ giữ nguyên vì cả
# panel_test.py và button_watch.py đọc chúng qua module này.
I2C_BUS = machine.PANEL_I2C_BUS
ADDR_LED = machine.PANEL_I2C_ADDR_LED
ADDR_BUTTON = machine.PANEL_I2C_ADDR_BUTTON
PANEL_COUNT = machine.PANEL_COUNT

LED_PIN_MAP = (
    8, 9, 10, 11, 12, 13, 14, 15,
    0, 1, 2, 3, 4, 5, 6, 7,
)

BUTTON_PIN_MAP = (
    7, 6, 5, 4, 3, 8, 9, 10,
    11, 12, 13, 14, 15, 0, 1, 2,
)

BUTTON_PANEL_ID_BY_PIN = tuple(
    BUTTON_PIN_MAP.index(physical_pin)
    for physical_pin in range(PANEL_COUNT)
)

# PCF8575 panel is active-low.
# LED: 0 = on, 1 = off.
# Button: 0 = pressed, 1 = released.
ALL_HIGH = 0xFFFF
POLL_INTERVAL = 0.02


class PCF8575:
    """Provide minimal raw 16-bit operations for one PCF8575 device."""

    def __init__(self, bus_number: int, address: int) -> None:
        """Open one I2C bus handle for the selected PCF8575 address."""
        self.bus = SMBus(bus_number)
        self.address = address

    def write_all(self, value: int) -> None:
        """Write one active-high or active-low 16-bit word to the device."""
        state = value & 0xFFFF
        low_byte = state & 0xFF
        high_byte = (state >> 8) & 0xFF

        message = i2c_msg.write(
            self.address,
            [low_byte, high_byte],
        )
        self.bus.i2c_rdwr(message)

    def read_all(self) -> int:
        """Read the current logic level of all sixteen device pins."""
        message = i2c_msg.read(
            self.address,
            2,
        )
        self.bus.i2c_rdwr(message)

        data = list(message)
        return data[0] | (data[1] << 8)

    def close(self) -> None:
        """Close the I2C bus handle owned by this object."""
        self.bus.close()


def validate_panel_id(panel_id: int) -> int:
    """Validate and return a physical panel position from 0 to 15."""
    value = int(panel_id)

    # Đã fix: Giới hạn từ 0 đến 15 thay vì 1 đến 16
    if not 0 <= value < PANEL_COUNT:
        raise ValueError(
            f"panel_id must be from 0 to {PANEL_COUNT - 1}, received {value}"
        )

    return value


def panel_id_to_mask(panel_id: int) -> int:
    """Convert a logical panel ID into its physical LED bit mask."""
    logical_id = validate_panel_id(panel_id)
    return 1 << LED_PIN_MAP[logical_id]


def button_pin_to_panel_id(button_pin: int) -> int:
    """Translate one physical button bit into its logical panel ID."""
    physical_pin = validate_panel_id(button_pin)
    return BUTTON_PANEL_ID_BY_PIN[physical_pin]


def build_led_word(active_panel_ids: Iterable[int]) -> int:
    """Build the active-low 16-bit output word for all illuminated LEDs."""
    state = ALL_HIGH

    for panel_id in active_panel_ids:
        state &= ~panel_id_to_mask(panel_id)

    return state & 0xFFFF


def parse_show_payload(payload: object) -> set[int]:
    """Convert a panel command payload into a validated panel ID set."""
    if not isinstance(payload, (list, tuple, set)):
        raise TypeError("show payload must be a list, tuple or set")

    return {
        validate_panel_id(panel_id)
        for panel_id in payload
    }


def apply_panel_command(
    action: str,
    payload: object,
    lit_panel_ids: set[int],
    enabled_button_ids: set[int],
) -> bool:
    """Update logical panel state and return whether LEDs must be rewritten."""
    if action == "show":
        panel_ids = parse_show_payload(payload)

        lit_panel_ids.clear()
        lit_panel_ids.update(panel_ids)

        enabled_button_ids.clear()
        enabled_button_ids.update(panel_ids)

        # Cảnh báo, KHÔNG chặn bớt.
        #
        # Mỗi đèn sáng là chip PCF8575 hút dòng qua GND, và gói chỉ chịu
        # khoảng 100 mA -- xem PANEL_MAX_LEDS_ON trong configuration/
        # machine.py, và vì sao test đèn từng giết chip.
        #
        # Không tự tắt bớt: giữa lúc pha, một nút mà người pha cần bấm lại
        # không sáng thì tệ hơn rủi ro dòng. Công thức hiện tại nhiều nhất
        # là 3 nút một bước, còn dư biên. Nhưng im lặng chính là cách lỗi
        # trước sống sót lâu như vậy, nên chỗ này phải nói ra.
        if len(panel_ids) > machine.PANEL_MAX_LEDS_ON:
            print(
                f"[panel] CẢNH BÁO: bật {len(panel_ids)} đèn cùng lúc, "
                f"quá mức an toàn {machine.PANEL_MAX_LEDS_ON}. Chip có thể "
                f"latch-up và ngừng trả lời I2C cho tới khi cắt nguồn."
            )

        print(
            "[panel] LEDs on and buttons enabled: "
            f"{sorted(panel_ids)}"
        )
        return True

    if action == "done":
        panel_id = validate_panel_id(int(payload))
        lit_panel_ids.discard(panel_id)
        enabled_button_ids.discard(panel_id)
        print(f"[panel] LED {panel_id} off.")
        return True

    if action == "retry":
        panel_id = validate_panel_id(int(payload))

        if panel_id in lit_panel_ids:
            enabled_button_ids.add(panel_id)
            print(f"[panel] Button {panel_id} enabled again.")

        return False

    if action == "clear":
        lit_panel_ids.clear()
        enabled_button_ids.clear()
        print("[panel] All LEDs off and all buttons disabled.")
        return True

    print(f"[panel] Unknown command: {action}")
    return False


def reset_panel() -> None:
    """Put both chips back to rest: every LED off, every input released.

    panel_worker does this in its own finally, which covers every ordinary
    end of an order. It does NOT cover a process that never unwinds -- a
    SIGTERM from systemd, panel button 14, a power cut mid-drink -- and a
    PCF8575 holds whatever was last written to it. The LEDs of a drink
    nobody is making stay lit until something writes to the chip again.

    So this exists to be called when no order is running, by whoever is
    still alive to call it. Cheap, idempotent, and safe to run twice.
    """
    led_device = None
    button_device = None

    try:
        led_device = PCF8575(
            I2C_BUS,
            ADDR_LED,
        )
        led_device.write_all(ALL_HIGH)

        # The inputs are driven HIGH to release them, exactly as
        # panel_worker does on the way in. A pin left pulled low by a
        # half-configured chip reads as a button held down for ever.
        button_device = PCF8575(
            I2C_BUS,
            ADDR_BUTTON,
        )
        button_device.write_all(ALL_HIGH)
    finally:
        for device in (led_device, button_device):
            if device is None:
                continue

            try:
                device.close()
            except Exception:      # noqa: BLE001 - already leaving
                pass


def panel_worker(
    panel_command_queue: queue.Queue[tuple[str, object]],
    button_event_queue: queue.Queue[int],
    stop_event: threading.Event,
    service_panel_id: int | None = None,
    on_service_press: "Callable[[], None] | None" = None,
) -> None:
    """Control both PCF8575 boards and publish accepted button presses.

    service_panel_id names one button that belongs to the machine rather
    than to the order -- the restart button. It is answered here because
    this thread owns the button chip for the length of an order, so it is
    the only reader that can see the press while a drink is open. The
    caller decides what it does, and whether the moment is safe.

    stop_event is this thread's own flag in both directions: the caller
    sets it to bring the thread home, and the thread sets it to report
    that the chip has failed. What that failure MEANS is the caller's to
    decide -- see order/process_runner.py's link_panel_failure, which ends
    the order only when the recipe actually needs the panel.
    """
    led_device: PCF8575 | None = None
    button_device: PCF8575 | None = None

    lit_panel_ids: set[int] = set()
    enabled_button_ids: set[int] = set()
    previous_button_state = ALL_HIGH

    try:
        led_device = PCF8575(
            I2C_BUS,
            ADDR_LED,
        )
        button_device = PCF8575(
            I2C_BUS,
            ADDR_BUTTON,
        )

        # Turn off every LED.
        led_device.write_all(ALL_HIGH)

        # PCF8575 input pins must first be released by writing HIGH.
        button_device.write_all(ALL_HIGH)
        previous_button_state = button_device.read_all()

        print(
            f"[panel] Thread started. "
            f"LED=0x{ADDR_LED:02X}, BUTTON=0x{ADDR_BUTTON:02X}."
        )

        while not stop_event.is_set():
            led_state_changed = False

            while True:
                try:
                    action, payload = panel_command_queue.get_nowait()
                except queue.Empty:
                    break

                try:
                    changed = apply_panel_command(
                        action,
                        payload,
                        lit_panel_ids,
                        enabled_button_ids,
                    )
                    led_state_changed = led_state_changed or changed
                except (TypeError, ValueError) as error:
                    print(
                        f"[panel] Invalid command {action!r}: {error}"
                    )
                finally:
                    panel_command_queue.task_done()

            if led_state_changed:
                led_device.write_all(
                    build_led_word(lit_panel_ids)
                )

                # A button already held before activation is not a new press.
                previous_button_state = button_device.read_all()

            current_button_state = button_device.read_all()

            # Detect a new press as a transition from HIGH to LOW.
            pressed_mask = (
                previous_button_state
                & ~current_button_state
                & 0xFFFF
            )
            previous_button_state = current_button_state

            for bit_index in range(PANEL_COUNT):
                bit_mask = 1 << bit_index

                if not pressed_mask & bit_mask:
                    continue

                panel_id = button_pin_to_panel_id(bit_index)

                # Checked before the enabled test, because the service
                # button is never part of a step and would otherwise be
                # dropped as "not active" -- which is exactly what it was
                # doing. Only when the step has not claimed the same
                # position, so a recipe that ever uses it keeps it.
                if (
                    panel_id == service_panel_id
                    and on_service_press is not None
                    and panel_id not in enabled_button_ids
                ):
                    print(f"[panel] Service button {panel_id} pressed.")

                    try:
                        on_service_press()
                    except Exception as error:      # noqa: BLE001
                        print(
                            f"[panel] Service button {panel_id} failed: "
                            f"{error}"
                        )

                    continue

                if panel_id not in enabled_button_ids:
                    print(
                        f"[panel] Button {panel_id} ignored "
                        "because its step is not active."
                    )
                    continue

                # Lock immediately so one press cannot execute a step twice.
                enabled_button_ids.discard(panel_id)

                try:
                    button_event_queue.put(
                        panel_id,
                        timeout=0.2,
                    )
                    print(f"[panel] Button {panel_id} pressed.")
                except queue.Full:
                    enabled_button_ids.add(panel_id)
                    print("[panel] Button event queue is full.")

            stop_event.wait(POLL_INTERVAL)

    except Exception as error:
        print(f"[panel] Hardware error: {error}")
        stop_event.set()

    finally:
        if led_device is not None:
            try:
                led_device.write_all(ALL_HIGH)
            except Exception:
                pass
            led_device.close()

        if button_device is not None:
            button_device.close()

        print("[panel] Thread stopped. All LEDs are off.")
        
