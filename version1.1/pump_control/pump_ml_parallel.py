"""
python3 -m pump_control.pump_ml_parallel
pump_ml_parallel.py
===================
Bơm đúng số gram mong muốn chỉ dùng thông số calib — KHÔNG cần loadcell.
Phiên bản SONG SONG: tất cả các bơm trong lệnh chạy CÙNG LÚC.

Công thức:
    t = (gram_target - b) / a
    → Chạy bơm đúng t giây rồi tắt.

Cách dùng độc lập:
    python pump_ml_parallel.py

Cách import vào file khác:
    from pump_ml_parallel import pump_gram, pump_gram_multi_parallel

So sánh với pump_ml.py (tuần tự):
    pump_gram_multi([...])           → Bơm 1 xong → Bơm 2 xong → ...
    pump_gram_multi_parallel([...])  → Bơm 1 + Bơm 2 + ... chạy CÙNG LÚC
"""



import json
import threading
from time import monotonic, sleep

from gpiozero import PWMLED

from configuration.configuration import PUMP_CALIB_FILE
from pump_control.gpio_lines import free_gpio_line

# ── CẤU HÌNH ─────────────────────────────────────────────────────────────────
# Bảng đấu dây: xem configuration/machine.py. order/process_runner.py
# import PUMP_GPIO qua chính module này, nên tên vẫn phải lộ ra ở đây.
from configuration.machine import PUMP_GPIO

PUMP_EVENT_POLL_SECONDS = 0.05


def all_pumps_off(verbose: bool = True) -> list[int]:
    """Drive every pump pin low and release it. Returns the pumps settled.

    WHY IT IS NEEDED
        Every pump here is switched off in a finally, which a signal does
        not run: kill the process mid-pour -- systemd restarting the
        service, panel button 14, a crash -- and gpiozero never gets to
        clean up. The pin keeps whatever the kernel last had it doing,
        which for a pump that was running means it is still running, with
        nobody left watching it.

    OFF, CLOSE, FREE
        Opening a PWMLED drives its pin low before anything else, which
        is what stops a stranded pump. close() then resets gpiozero's own
        state -- but on the lgpio backend it does NOT hand the line back,
        so free_gpio_line() has to finish the job. Skip that last step and
        this routine becomes the bug it was written to prevent: it runs
        inside main.py, one long-lived process, so a line it keeps is a
        line every later order is refused. See pump_control/gpio_lines.py.

    Safe on a machine that has just booted and never pumped anything, and
    safe to run twice.
    """
    settled: list[int] = []

    for pump_number, gpio_pin in sorted(PUMP_GPIO.items()):
        try:
            pwm = PWMLED(gpio_pin, frequency=1000)

            try:
                pwm.off()
            finally:
                pwm.close()

            settled.append(pump_number)
        except Exception as error:      # noqa: BLE001 - report and carry on
            # One pin held by something else must not leave the other nine
            # untouched: this is the routine that makes the machine safe.
            print(f"[pump] Khong tat duoc bom #{pump_number} "
                  f"(GPIO {gpio_pin}): {error}")
        finally:
            # Outside the except on purpose: the line has to be released
            # whether opening it succeeded, failed, or half-succeeded.
            free_gpio_line(gpio_pin)

    if verbose:
        print(f"[pump] Da tat va giai phong {len(settled)}/{len(PUMP_GPIO)} bom.")

    return settled


class PumpInterruptedError(RuntimeError):
    """Raised when machine shutdown interrupts a timed pump."""


# ══════════════════════════════════════════════════════════════════════════════
# LOAD THÔNG SỐ CALIB
# ══════════════════════════════════════════════════════════════════════════════

def _load_pump_calib() -> dict:
    try:
        with open(PUMP_CALIB_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Khong tim thay '{PUMP_CALIB_FILE}'. "
            f"Hay chay calib_pump.py truoc."
        )


# ══════════════════════════════════════════════════════════════════════════════
# HÀM CHÍNH: BƠM MỘT BƠM (giữ nguyên từ pump_ml.py)
# ══════════════════════════════════════════════════════════════════════════════

def pump_gram(
    pump_number: int,
    gram_target: float,
    verbose: bool = True,
    run_event: threading.Event | None = None,
    stop_event: threading.Event | None = None,
) -> float:
    """
    Bơm đúng gram_target gram dựa trên thông số calib.
    Không cần loadcell — chỉ dùng sleep().

    Tham số:
        pump_number  — số bơm (1..10)
        gram_target  — số gram muốn bơm (ví dụ: 200.0)
        verbose      — True = in log, False = im lặng

    Trả về:
        float — số giây đã chạy bơm
    """

    pump_calib = _load_pump_calib()
    key = f"pump_{pump_number}"

    if key not in pump_calib:
        raise ValueError(
            f"Bom #{pump_number} chua duoc calib. "
            f"Chay calib_pump.py roi chon bom {pump_number}."
        )
    if pump_number not in PUMP_GPIO:
        raise ValueError(f"Bom #{pump_number} khong co trong bang PUMP_GPIO.")

    d = pump_calib[key]
    a = d["gram_per_sec"]   # tốc độ thực (g/s)
    b = d["dead_gram"]      # dead zone (g)

    # t = (gram_target - b) / a
    duration = (gram_target - b) / a
    if duration <= 0:
        raise ValueError(
            f"Thoi gian tinh ra am ({duration:.3f}s). "
            f"Kiem tra lai thong so calib bom #{pump_number}."
        )

    gpio_pin = PUMP_GPIO[pump_number]
    pwm = PWMLED(gpio_pin, frequency=1000)

    try:
        if verbose:
            print(f"  [Bom #{pump_number}] {gram_target:.1f}g → chay {duration:.3f}s  "
                  f"(a={a:.4f} b={b:.4f})")

        if run_event is None:
            # Preserve the legacy one-sleep timing path for every old caller.
            pwm.value = 1.0
            sleep(duration)
        else:
            remaining_duration = duration
            pwm_is_running = False

            while remaining_duration > 0:
                if (
                    stop_event is not None
                    and stop_event.is_set()
                ):
                    raise PumpInterruptedError(
                        f"Pump #{pump_number} interrupted by machine shutdown."
                    )

                if not run_event.is_set():
                    pwm.off()
                    pwm_is_running = False

                    run_event.wait(
                        timeout=PUMP_EVENT_POLL_SECONDS
                    )
                    continue

                if not pwm_is_running:
                    pwm.value = 1.0
                    pwm_is_running = True

                interval = min(
                    PUMP_EVENT_POLL_SECONDS,
                    remaining_duration,
                )
                started_at = monotonic()
                sleep(interval)
                elapsed = monotonic() - started_at

                # A non-advancing injected clock must not stall the pump loop.
                if elapsed <= 0:
                    elapsed = interval

                remaining_duration -= min(
                    elapsed,
                    remaining_duration,
                )
    finally:
        # off, close, FREE -- all three, in that order.
        #
        # off() stops the pump. close() resets gpiozero's own state. On
        # the lgpio backend neither hands the line back: it stays claimed
        # by this process, and the next process_runner -- a new process
        # for every drink -- dies with 'GPIO busy' on the same pump. Only
        # free_gpio_line() releases it. See pump_control/gpio_lines.py.
        try:
            pwm.off()
        finally:
            try:
                pwm.close()
            finally:
                free_gpio_line(gpio_pin)

    if verbose:
        print(f"  [Bom #{pump_number}] Xong.")

    return duration


# ══════════════════════════════════════════════════════════════════════════════
# HÀM MỚI: BƠM NHIỀU BƠM SONG SONG (tất cả cùng lúc)
# ══════════════════════════════════════════════════════════════════════════════

def pump_gram_multi_parallel(
    orders: list[tuple[int, float]],
    verbose: bool = True,
    run_event: threading.Event | None = None,
    stop_event: threading.Event | None = None,
) -> dict[int, float | Exception]:
    """
    Bơm nhiều bơm SONG SONG — tất cả khởi động CÙNG MỘT LÚC.
    Hàm chỉ trả về sau khi BƠM CUỐI CÙNG hoàn thành.

    Tham số:
        orders  — danh sách [(pump_number, gram_target), ...]
                  ví dụ: [(1, 150.0), (10, 100.0)]
        verbose — in log hay không

    Trả về:
        dict — { pump_number: duration_giây } cho mỗi bơm
               Nếu bơm nào lỗi, giá trị là Exception thay vì float.

    Ví dụ:
        pump_gram_multi_parallel([(1, 100), (10, 150)])
        # Bơm #1 và Bơm #10 chạy ĐỒNG THỜI
        # Tổng thời gian ≈ max(t1, t10) thay vì t1 + t10
    """
    if not orders:
        return {}

    results: dict[int, float | Exception] = {}
    lock = threading.Lock()

    def _worker(pump_number: int, gram_target: float):
        try:
            duration = pump_gram(
                pump_number,
                gram_target,
                verbose=verbose,
                run_event=run_event,
                stop_event=stop_event,
            )
            with lock:
                results[pump_number] = duration
        except Exception as e:
            with lock:
                results[pump_number] = e
            if verbose:
                print(f"  [Bom #{pump_number}] LOI: {e}")

    if verbose:
        pump_list = ", ".join(f"#{p} ({g:.1f}g)" for p, g in orders)
        print(f"\n  [SONG SONG] Khoi dong {len(orders)} bom cung luc: {pump_list}")

    # Tạo và khởi động tất cả thread cùng lúc
    threads = []
    for pump_number, gram_target in orders:
        t = threading.Thread(
            target=_worker,
            args=(pump_number, gram_target),
            daemon=True,
            name=f"pump-{pump_number}",
        )
        threads.append(t)

    # Kích hoạt tất cả thread gần như đồng thời
    for t in threads:
        t.start()

    # Chờ tất cả thread hoàn thành
    for t in threads:
        t.join()

    if verbose:
        print(f"\n  [SONG SONG] Tat ca {len(orders)} bom da hoan thanh.")
        for pump_number, gram_target in orders:
            val = results.get(pump_number)
            if isinstance(val, Exception):
                print(f"    Bom #{pump_number}: LOI — {val}")
            else:
                print(f"    Bom #{pump_number}: {gram_target:.1f}g xong trong {val:.3f}s")

    return results


# # ══════════════════════════════════════════════════════════════════════════════
# # CHẠY THỬ TRỰC TIẾP
# # ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 50)
    print("  THU NGHIEM BOM SONG SONG")
    print("=" * 50)

    print("\n  Nhap lenh theo dinh dang:  <so_bom> <gram>")
    print("  Vi du:  1 200             → Bom #1 bom 200g")
    print("  Vi du:  1 100 10 150      → Bom #1 (100g) + Bom #10 (150g) CUNG LUC")
    print("  Nhap 'q' de thoat.\n")

    while True:
        raw = input("  Lenh > ").strip().lower()
        if raw == "q":
            break

        tokens = raw.split()
        if len(tokens) < 2 or len(tokens) % 2 != 0:
            print("  Sai dinh dang. Vi du: 1 200  hoac  1 100 10 150")
            continue


        orders = []
        
        valid = True
        for i in range(0, len(tokens), 2):
            try:
                p = int(tokens[i])
                g = float(tokens[i + 1])
                orders.append((p, g))
            except ValueError:
                print(f"  Gia tri khong hop le: '{tokens[i]}' '{tokens[i+1]}'")
                valid = False
                break

        if not valid:
            continue

        pump_gram_multi_parallel(orders)
