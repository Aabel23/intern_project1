"""Check the panel hardware by hand, without running a drink.

WHAT THIS FILE IS
    A bench tool, not part of making a drink. It talks to the same two
    PCF8575 boards panel_control/panel.py drives, so it can tell a
    wiring fault from a software one before blaming either.

THE HARDWARE
    Two PCF8575 expanders on I2C bus 1, both active low:

        0x21   sixteen LEDs      0 = on
        0x20   sixteen buttons   0 = pressed

    A "panel" is one LED and one button as a pair, numbered 0-15. The two
    boards do NOT use the same pin for the same panel -- panel 6 is LED
    pin P14 on 0x21 and button pin P9 on 0x20. LED_PIN_MAP and
    BUTTON_PIN_MAP in panel.py own that translation; nothing here or in
    the database repeats it.

THE MODES, ROUGHLY IN THE ORDER WORTH RUNNING THEM

    probe    Read both boards once. Confirms they answer at all and
             reports any button that reads pressed while untouched.
             NOTE: the LED board's state cannot be read back -- an LED
             clamps the weak PCF8575 pull-up, so every output pin reads 0
             whatever was written. Only your eyes confirm the LEDs.

    leds     All sixteen on together, then one at a time, 0 to 15. Watch
             for a lamp that never lights or lights out of order.

    buttons  Light one LED and wait for its own button, panel by panel.
             Reports any press that arrives on a different panel than the
             one lit, which is how a swapped pair of wires shows up.

    monitor  Print the panel ID of whatever is pressed, for 30 seconds.
             Use this to map physical positions to panel numbers.

    worker   Drive the real panel_worker through its queues, proving the
             production path and not just this file's own I2C calls.

BEFORE RUNNING
    Only one process may own the panel. Stop anything else that talks to
    it first -- order/process_runner.py, or a machine service -- or the
    two will fight over the same boards and both will misbehave.

    python3 -m panel_control.panel_test probe
    python3 -m panel_control.panel_test leds
"""

from __future__ import annotations

import argparse
import queue
import threading
from time import monotonic, sleep

from panel_control.panel import (
    ADDR_BUTTON,
    ADDR_LED,
    ALL_HIGH,
    BUTTON_PIN_MAP,
    I2C_BUS,
    LED_PIN_MAP,
    PANEL_COUNT,
    PCF8575,
    build_led_word,
    button_pin_to_panel_id,
    panel_worker,
)
from configuration.machine import PANEL_MAX_LEDS_ON


LED_STEP_SECONDS = 0.25

# How long each GROUP of lamps stays lit -- see run_leds() for why the test
# never lights all sixteen together.
LED_GROUP_SECONDS = 0.8
BUTTON_POLL_SECONDS = 0.02
BUTTON_TIMEOUT_SECONDS = 15.0
MONITOR_SECONDS = 30.0


def open_devices() -> tuple[PCF8575, PCF8575]:
    """Open both expanders and put them in their idle state."""
    led_device = PCF8575(
        I2C_BUS,
        ADDR_LED,
    )
    button_device = PCF8575(
        I2C_BUS,
        ADDR_BUTTON,
    )

    # LEDs off, and the button pins released so they can be read.
    led_device.write_all(ALL_HIGH)
    button_device.write_all(ALL_HIGH)

    return (
        led_device,
        button_device,
    )


def close_devices(
    led_device: PCF8575 | None,
    button_device: PCF8575 | None,
) -> None:
    """Turn every LED off and release both I2C handles."""
    if led_device is not None:
        try:
            led_device.write_all(ALL_HIGH)
        except OSError:
            pass
        led_device.close()

    if button_device is not None:
        button_device.close()


def pressed_panel_ids(
    previous_state: int,
    current_state: int,
) -> list[int]:
    """Return the panel IDs whose button went from released to pressed."""
    # Active low, so a press is a one-to-zero transition.
    pressed_mask = (
        previous_state
        & ~current_state
        & 0xFFFF
    )

    return [
        button_pin_to_panel_id(bit_index)
        for bit_index in range(PANEL_COUNT)
        if pressed_mask & (1 << bit_index)
    ]


# ============================================================
# PROBE
# ============================================================

def run_probe() -> int:
    """Read both boards once and report whether they answered."""
    led_device = None
    button_device = None

    try:
        led_device, button_device = open_devices()

        # Both boards answered if these reads did not raise.
        led_device.read_all()
        button_state = button_device.read_all()

        print(
            f"LED board    0x{ADDR_LED:02X}: answered. "
            "Its state cannot be read back, because an LED clamps the "
            "weak PCF8575 pull-up, so every output pin reads 0. "
            "Only your eyes can confirm the LEDs."
        )
        print(
            f"BUTTON board 0x{ADDR_BUTTON:02X}: answered, "
            f"0x{button_state:04X}"
        )

        held = sorted(
            button_pin_to_panel_id(bit_index)
            for bit_index in range(PANEL_COUNT)
            if not button_state & (1 << bit_index)
        )

        if not held:
            print(
                "No button is held down, which is the expected idle state."
            )
            return 0

        print(
            "Buttons reading as pressed while nothing is touched: "
            + ", ".join(str(panel_id) for panel_id in held)
        )
        print(
            "A button stuck low never produces a released-to-pressed "
            "edge, so panel_worker can never report it."
        )
        return 1

    except OSError as error:
        print(f"I2C error: {error}")
        print(
            "Check the wiring and that i2cdetect shows "
            f"0x{ADDR_LED:02X} and 0x{ADDR_BUTTON:02X}."
        )
        return 1

    finally:
        close_devices(
            led_device,
            button_device,
        )


# ============================================================
# LEDS
# ============================================================

def run_leds() -> int:
    """Light every LED together, then walk through them one at a time."""
    led_device = None
    button_device = None

    try:
        led_device, button_device = open_devices()

        # In GROUPS, never all sixteen at once.
        #
        # A lit lamp is the PCF8575 sinking current through its GND pin, and
        # the package takes only about 100 mA. Sixteen lamps is far past
        # that, and the chip answers by latching up -- it stops
        # acknowledging its I2C address until the power is pulled. Measured
        # on this machine on 2026-09-08: after every run of the lamp test
        # i2cdetect showed 0x20 but not 0x21, and 0x21 returned only after
        # unplugging the panel.
        #
        # Group size lives in configuration/machine.py, because the safe
        # number depends on what one lamp actually draws.
        print(f"LEDs on, {PANEL_MAX_LEDS_ON} at a time.")

        for start in range(0, PANEL_COUNT, PANEL_MAX_LEDS_ON):
            group = range(start, min(start + PANEL_MAX_LEDS_ON, PANEL_COUNT))
            print(f"  panels {group.start}-{group.stop - 1}")
            led_device.write_all(build_led_word(group))
            sleep(LED_GROUP_SECONDS)

        print("All LEDs off.")
        led_device.write_all(ALL_HIGH)
        sleep(0.5)

        print("One LED at a time, panel 0 to 15.")

        for panel_id in range(PANEL_COUNT):
            print(
                f"  panel {panel_id:>2}  (chip pin P{LED_PIN_MAP[panel_id]})"
            )
            led_device.write_all(
                build_led_word([panel_id])
            )
            sleep(LED_STEP_SECONDS)

        led_device.write_all(ALL_HIGH)
        print("Done. Every LED should have lit exactly once, in order.")
        return 0

    except OSError as error:
        print(f"I2C error: {error}")
        return 1

    finally:
        close_devices(
            led_device,
            button_device,
        )


# ============================================================
# BUTTONS
# ============================================================

def wait_for_press(
    button_device: PCF8575,
    previous_state: int,
    timeout_seconds: float,
) -> tuple[list[int], int]:
    """Wait for the next press and return the panel IDs and the new state."""
    deadline = monotonic() + timeout_seconds

    while monotonic() < deadline:
        current_state = button_device.read_all()
        panel_ids = pressed_panel_ids(
            previous_state,
            current_state,
        )
        previous_state = current_state

        if panel_ids:
            return (
                panel_ids,
                previous_state,
            )

        sleep(BUTTON_POLL_SECONDS)

    return (
        [],
        previous_state,
    )


def run_buttons() -> int:
    """Light one LED at a time and confirm its own button reports back."""
    led_device = None
    button_device = None
    wrong: list[tuple[int, list[int]]] = []
    missing: list[int] = []

    try:
        led_device, button_device = open_devices()
        previous_state = button_device.read_all()

        print(
            "Press the button whose LED is lit. "
            f"Each one waits up to {BUTTON_TIMEOUT_SECONDS:g}s, "
            "then moves on."
        )
        print("Ctrl-C stops the test early.\n")

        for panel_id in range(PANEL_COUNT):
            led_device.write_all(
                build_led_word([panel_id])
            )
            print(
                f"  panel {panel_id:>2} lit "
                f"(LED P{LED_PIN_MAP[panel_id]}, "
                f"button P{BUTTON_PIN_MAP[panel_id]}) ... ",
                end="",
                flush=True,
            )

            panel_ids, previous_state = wait_for_press(
                button_device,
                previous_state,
                BUTTON_TIMEOUT_SECONDS,
            )

            if not panel_ids:
                print("no press (timeout)")
                missing.append(panel_id)
                continue

            if panel_ids == [panel_id]:
                print("OK")
                continue

            print(
                "MISMATCH, reported "
                + ", ".join(str(value) for value in panel_ids)
            )
            wrong.append(
                (panel_id, panel_ids)
            )

        led_device.write_all(ALL_HIGH)

        print("\nResult:")
        print(
            f"  matched  : {PANEL_COUNT - len(wrong) - len(missing)}"
            f" of {PANEL_COUNT}"
        )

        if missing:
            print(
                "  no press : "
                + ", ".join(str(panel_id) for panel_id in missing)
            )

        for expected, reported in wrong:
            print(
                f"  mismatch : LED {expected} lit, "
                f"button reported {reported}"
            )

        return 0 if not wrong and not missing else 1

    except KeyboardInterrupt:
        print("\nStopped by operator.")
        return 1

    except OSError as error:
        print(f"I2C error: {error}")
        return 1

    finally:
        close_devices(
            led_device,
            button_device,
        )


# ============================================================
# MONITOR
# ============================================================

def run_monitor() -> int:
    """Print the panel ID of every button pressed, with its LED lit."""
    led_device = None
    button_device = None

    try:
        led_device, button_device = open_devices()
        previous_state = button_device.read_all()
        deadline = monotonic() + MONITOR_SECONDS

        print(
            f"Press any button for {MONITOR_SECONDS:g}s. "
            "Its LED lights while it is recognised. Ctrl-C stops."
        )

        while monotonic() < deadline:
            current_state = button_device.read_all()
            panel_ids = pressed_panel_ids(
                previous_state,
                current_state,
            )
            previous_state = current_state

            for panel_id in panel_ids:
                print(
                    f"  panel {panel_id:>2}  "
                    f"(button P{BUTTON_PIN_MAP[panel_id]})"
                )
                led_device.write_all(
                    build_led_word([panel_id])
                )

            sleep(BUTTON_POLL_SECONDS)

        led_device.write_all(ALL_HIGH)
        print("Monitor finished.")
        return 0

    except KeyboardInterrupt:
        print("\nStopped by operator.")
        return 0

    except OSError as error:
        print(f"I2C error: {error}")
        return 1

    finally:
        close_devices(
            led_device,
            button_device,
        )


# ============================================================
# WORKER
# ============================================================

def run_worker() -> int:
    """Drive the production panel_worker through its own queues."""
    panel_command_queue: queue.Queue[tuple[str, object]] = queue.Queue()
    button_event_queue: queue.Queue[int] = queue.Queue()
    stop_event = threading.Event()

    thread = threading.Thread(
        target=panel_worker,
        args=(
            panel_command_queue,
            button_event_queue,
            stop_event,
        ),
        name="panel-thread",
        daemon=True,
    )
    thread.start()
    sleep(0.5)

    if not thread.is_alive():
        print("panel_worker stopped immediately; see the error above.")
        return 1

    requested = [1, 5, 9, 13]

    try:
        print(
            "Enabling panels "
            + ", ".join(str(panel_id) for panel_id in requested)
            + ". Press them in any order."
        )
        panel_command_queue.put(
            ("show", requested)
        )

        waiting = set(requested)
        deadline = monotonic() + BUTTON_TIMEOUT_SECONDS * 2

        while waiting and monotonic() < deadline:
            try:
                panel_id = button_event_queue.get(
                    timeout=0.2,
                )
            except queue.Empty:
                continue

            button_event_queue.task_done()

            if panel_id in waiting:
                waiting.discard(panel_id)
                print(
                    f"  panel {panel_id} accepted, "
                    f"{len(waiting)} left"
                )
            else:
                print(
                    f"  panel {panel_id} arrived but was not requested"
                )

        if waiting:
            print(
                "Never received: "
                + ", ".join(str(panel_id) for panel_id in sorted(waiting))
            )
            return 1

        print("panel_worker delivered every requested button.")
        return 0

    except KeyboardInterrupt:
        print("\nStopped by operator.")
        return 1

    finally:
        panel_command_queue.put(
            ("clear", None)
        )
        sleep(0.2)
        stop_event.set()
        thread.join(
            timeout=5.0
        )


# ============================================================
# COMMAND LINE
# ============================================================

MODES = {
    "probe": run_probe,
    "leds": run_leds,
    "buttons": run_buttons,
    "monitor": run_monitor,
    "worker": run_worker,
}


def main() -> int:
    """Run one panel test mode."""
    parser = argparse.ArgumentParser(
        description="Test the sixteen panel LEDs and buttons.",
    )
    parser.add_argument(
        "mode",
        choices=sorted(MODES),
        help="Which test to run.",
    )
    arguments = parser.parse_args()

    return MODES[arguments.mode]()


if __name__ == "__main__":
    raise SystemExit(main())
