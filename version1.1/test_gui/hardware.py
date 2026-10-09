"""The jobs the test screen can ask the machine to run.

WHAT THIS FILE IS
    Everything in here touches hardware. It is kept apart from serve.py so
    the HTTP layer never drives a pump directly -- a request handler runs on
    whichever thread the server happened to give it, and two of those inside
    the I2C bus or the HX711 at once corrupt each other's reads.

    So: one worker thread, one job at a time, and the handler only starts a
    job and reads its progress.

WHY IT BORROWS FROM prime_all
    Priming logic lives in pump_control/prime_all.py and is imported, not
    copied. pump_priming.py is the cautionary tale: it took its own copy of
    the HX711 driver, the original was fixed, and the copy kept a 10 ms
    timeout against a chip that needs 87 ms. One implementation, one place
    to fix it.

WHAT IT REFUSES TO DO
    Run anything while an order is in progress. process_runner owns the
    pumps, the panel and the scale during a drink; a test screen reaching
    in at the same time would fight it for the I2C bus and could pour into
    a customer's cup. The check is the same flock order/run_flow.py takes,
    plus a look at the runner's port.
"""

from __future__ import annotations

import fcntl
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any

from configuration import machine


PROJECT_DIR = Path(__file__).resolve().parent.parent

# Both belong to order/run_flow.py. Held or open means an order owns the
# machine right now.
FLOW_LOCK_FILE = PROJECT_DIR / "order" / ".run_flow.lock"
RUNNER_PORT = machine.RUNNER_PORT

# How long a panel LED stays on during the lamp test, per lamp.
LED_STEP_SECONDS = 0.35

# Mỗi nhóm đèn sáng bao lâu ở bước cuối. Dài hơn một bước đơn lẻ vì đây là
# lúc người ta nhìn cả cụm để so sáng/tối giữa các đèn.
LED_GROUP_SECONDS = 0.8

# How long the button test listens before giving up on the rest.
BUTTON_TEST_SECONDS = 30.0
BUTTON_POLL_SECONDS = 0.05


class Job:
    """One test run, and everything the screen needs to draw it.

    Deliberately plain: a status word, a growing list of log lines and a
    results table. The screen polls it; nothing is pushed. That keeps the
    hardware thread free of any idea that a browser exists.
    """

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.reset()

    def reset(self, name: str = "", total: int = 0) -> None:
        with self.lock:
            self.name = name
            self.state = "idle"          # idle | running | done | failed
            self.message = ""
            self.lines: list[str] = []
            self.results: list[dict[str, Any]] = []
            self.pressed: list[int] = []
            self.started = time.monotonic()
            self.total = total
            self.finished = 0
            self.stop = threading.Event()

    def log(self, text: str) -> None:
        with self.lock:
            self.lines.append(text)
            # A test screen is for watching, not archaeology. The tail is
            # what matters and an unbounded list is a slow leak.
            del self.lines[:-200]

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "name": self.name,
                "state": self.state,
                "message": self.message,
                "lines": list(self.lines),
                "results": list(self.results),
                "pressed": sorted(self.pressed),
                "total": self.total,
                "finished": self.finished,
                "elapsed": round(time.monotonic() - self.started, 1),
            }


JOB = Job()
_worker: threading.Thread | None = None

# Held across the whole check-then-start, because they must be one step.
# ThreadingHTTPServer runs each request on its own thread, so two clicks
# arriving together could both see "not busy" and both spawn a worker --
# two threads inside the same I2C bus and the same HX711, which is the one
# thing this file exists to prevent.
_start_lock = threading.Lock()


def pouring() -> bool:
    """Is a drink actually being made right now?

    The runner's port is open only while process_runner is alive, which is
    only during a drink. This is the hard one: while it is true,
    process_runner owns the pumps, the panel and the scale outright.
    """
    return _port_open(RUNNER_PORT)


def flow_running() -> bool:
    """Is order/run_flow.py up at all?

    True for its whole life, including the long stretches between orders
    when it is only waiting for a scan. On a machine in service that is the
    normal state -- so this alone must NOT stop the test screen, or the
    screen could only ever be used on a machine that was switched off.
    """
    try:
        handle = open(FLOW_LOCK_FILE, "a")
    except OSError:
        return False        # no lock file yet: run_flow has never run

    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(handle, fcntl.LOCK_UN)
        return False
    except OSError:
        return True
    finally:
        handle.close()


def order_in_progress() -> str:
    """Why a test job cannot start now, or "" when one may.

    Three states, not two, and the middle one is the one that matters:

        pouring                  refuse. Another process is driving the
                                 hardware this instant.

        run_flow up, test mode   refuse, and say how to fix it. run_flow is
        NOT requested            idle but a scan could arrive at any moment
                                 and start an order on top of the test.

        run_flow up, test mode   allow. run_flow has been asked to hold and
        requested                will not start an order until the flag
                                 clears -- see order/run_flow.py.

    The first version collapsed the middle two and refused whenever
    run_flow was running at all. That is the machine's normal state, so it
    made this screen unreachable in practice.
    """
    if pouring():
        return (f"Máy đang pha một đơn (cổng {RUNNER_PORT} đang mở). "
                f"Đợi pha xong rồi thử lại.")

    if flow_running() and not test_mode_open():
        return ("order/run_flow.py đang chạy. Bấm nút bảng "
                f"{TOGGLE_PANEL_ID} để tạm dừng nhận đơn, rồi test.")

    return ""


def test_mode_open() -> bool:
    """Has the machine been put into test mode by the panel button?"""
    return bool(read_test_mode().get("open"))


def _port_open(port: int) -> bool:
    """Is something listening on this port right now?"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.2)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def busy() -> bool:
    """Is a test job already running?"""
    return JOB.snapshot()["state"] == "running"


# The load cell's two pins, matching loadcell/loadcell.py, which claims
# them with these literals at import time. _open_loadcell() below names
# them the same way; if they ever move, all three have to move together.
LOADCELL_SCK_PIN = 4
LOADCELL_DT_PIN = 18


def _free_gpio_line(slot: int | str | None) -> None:
    """Hand one GPIO line back so ANOTHER PROCESS can claim it.

    The implementation moved to pump_control/gpio_lines.py, because the
    pump path needs the identical thing and two copies of a rule this
    subtle drift apart. The reasoning that was written here is now in
    that module's docstring; the short version is that gpiozero's
    .close() only re-claims the line as an input, so `gpioinfo` still
    reports it "[used]" and process_runner still dies with 'GPIO busy'.
    Only lgpio.gpio_free() releases it for real.

    TAKES A SLOT OR A NUMBER, AND CONVERTS IN HERE
        Callers used to write _free_gpio_line(gpio_number(x)), and
        gpio_number was never imported in this file -- so both call sites
        raised NameError instead of freeing anything. One of them sat
        inside `except Exception: pass` and silently did nothing; the
        other was in _hold_stop_locked(), where it killed the watchdog
        thread and left a pump marked held for the life of the process.

        Doing the conversion in here is what stops that coming back: the
        one function every caller already goes through is also the one
        place that has to know how a slot is spelled, and it is already
        wrapped so a failure cannot escape.

    Best effort by design: cleanup that raises is worse than cleanup that
    quietly does nothing.
    """
    try:
        from database.db_core import gpio_number
        from pump_control.gpio_lines import free_gpio_line

        number = gpio_number(slot)

        if number is not None:
            free_gpio_line(number)
    except Exception:      # noqa: BLE001 - cleanup must never raise
        pass


def _cleanup_loadcell() -> None:
    """Close the load cell devices AND actually release their pins.

    Both halves are needed: .close() resets gpiozero's own state,
    _free_gpio_line() is what lets the next order's process_runner claim
    GPIO 4/18 at all. See _free_gpio_line() for why one without the
    other silently does nothing.
    """
    try:
        import loadcell.loadcell as _lc
        if _lc.SCK is not None:
            try:
                _lc.SCK.close()
            except Exception:
                pass
        if _lc.DT is not None:
            try:
                _lc.DT.close()
            except Exception:
                pass
        _lc.SCK = None
        _lc.DT = None
    except Exception:
        pass

    # Outside the try above on purpose: the pins have to be released even
    # if importing loadcell.loadcell is what failed -- a part-way import
    # can leave a line claimed with no device object to close.
    _free_gpio_line(LOADCELL_SCK_PIN)
    _free_gpio_line(LOADCELL_DT_PIN)


def release_all_gpio() -> None:
    """Hand back every GPIO line the test screen can claim, whatever
    happened while it was open.

    WHY A CATCH-ALL AND NOT JUST PER-JOB CLEANUP
        Every path that claims a line already releases it -- a hold ends
        in _hold_stop_locked(), a job ends in start()'s finally. This
        exists for the paths nobody thought of: a job that died between
        claiming a pump and reaching its own finally, a future test that
        opens a pin and forgets, a browser tab closed mid-prime.

        The machine has exactly one moment where "nothing in this process
        should be holding hardware" is guaranteed true -- leaving test
        mode -- so that is where this runs. After it, the next order's
        process_runner can always claim what it needs.

    Safe to call at any time this process is not mid-test: freeing a line
    this process never claimed is a no-op, and it cannot touch a line
    held by another process (the handle is per-process).
    """
    # Pumps first: importing prime_all pulls in loadcell.loadcell, which
    # claims the scale's pins all over again -- so the scale is released
    # after, not before.
    try:
        from pump_control.prime_all import pump_lines

        for line in pump_lines():
            _free_gpio_line(line["gpio"])
    except Exception:      # noqa: BLE001 - cleanup must never raise
        pass

    _cleanup_loadcell()


def _open_loadcell() -> None:
    """Claim the load cell GPIO pins again if a previous job released them.

    loadcell.loadcell claims GPIO 4/18 at import time and never re-creates
    them; _cleanup_loadcell() above sets SCK/DT back to None once a job is
    done so process_runner's subprocess can claim the same pins for the
    next order. This is the other half: hand them back before the next
    job that needs the scale.
    """
    import loadcell.loadcell as _lc

    # Gọi driver mở chân, KHÔNG tự tạo OutputDevice/DigitalInputDevice ở
    # đây: bản sao cũ quên đặt trở kéo lên cho DT, nên mỗi lần test_gui mở
    # lại cân là lặng lẽ khôi phục lỗi "dây đứt đọc ra -399.4 g".
    _lc.open_pins()


def start(name: str, target, total: int = 0) -> tuple[bool, str]:
    """Begin one job on the worker thread. Returns (started, why not)."""
    global _worker

    def run() -> None:
        # Borrow the button chip for the whole job. The panel test reads
        # 0x20 directly, and since run_flow now hosts this server the
        # watcher thread is in the SAME process -- two readers on one I2C
        # bus, which is the fault this project has already lost orders to.
        # Every job takes it, not just the panel one: a job that fails
        # halfway must not leave the chip half-shared.
        from panel_control import button_watch

        borrowed = button_watch.pause_active()

        try:
            target(JOB)
            with JOB.lock:
                if JOB.state == "running":
                    JOB.state = "done"
        except Exception as error:      # noqa: BLE001 - shown on the screen
            JOB.log(f"LỖI: {error}")
            with JOB.lock:
                JOB.state = "failed"
                JOB.message = str(error)
        finally:
            _cleanup_loadcell()
            if borrowed:
                button_watch.resume_active()

    with _start_lock:
        if busy():
            return False, "Đang chạy một bài test khác."

        reason = order_in_progress()

        if reason:
            return False, reason

        JOB.reset(name, total)

        with JOB.lock:
            JOB.state = "running"

        # Started while the lock is still held, so the next request cannot
        # slip between "marked running" and "actually running".
        _worker = threading.Thread(target=run, name=f"test-{name}",
                                   daemon=True)
        _worker.start()

    return True, ""


def stop() -> None:
    """Ask the running job to stop at its next safe point."""
    JOB.stop.set()


# ─────────────────────────────── PRIMING ───────────────────────────────

# ============================================================
# HOLD-TO-RUN
#
# Press a button and the pump runs; let go and it stops. Useful for
# clearing a line by eye rather than by weight.
#
# WHY THIS IS NOT SIMPLY start/stop
#     Between "pressed" and "released" is a network. If the tab is
#     closed, the wifi drops, the browser crashes or the tablet sleeps,
#     the release never arrives -- and a pump left running empties a
#     bottle onto the floor and keeps going.
#
#     So the browser does not ask the pump to RUN; it asks it to run for
#     the next moment, again and again, several times a second. Silence
#     is what stops it. Nothing has to go right for the pump to stop --
#     something has to keep going right for it to continue.
# ============================================================

# How long a single "still holding" message keeps the pump alive. The
# page sends them about three times as often, so one lost message is
# survivable and two are not.
HOLD_TIMEOUT_SECONDS = 1.0

# A pump may not be held longer than this however continuously the
# button is pressed. Covers a wedged key, a stuck touchscreen, and a
# finger resting on a tablet in a bag.
HOLD_MAX_SECONDS = 60.0

# How often the watchdog looks. Well inside HOLD_TIMEOUT_SECONDS.
HOLD_WATCH_SECONDS = 0.1

# How long a released press is remembered, so a heartbeat still in
# flight when the button came up cannot switch the pump back on. Only
# has to outlast one request crossing the network.
HOLD_MEMORY_SECONDS = 5.0

_hold_lock = threading.Lock()
# "gpio" is carried alongside "pwm" so _hold_stop_locked() can hand the
# line back by number. Closing the PWMLED is not enough on its own --
# see _free_gpio_line().
_hold: dict[str, Any] = {"pump": None, "pwm": None, "gpio": None,
                         "token": "", "deadline": 0.0, "started": 0.0}
_hold_watcher: threading.Thread | None = None

# Presses that have already ended: token -> when it ended.
_hold_released: dict[str, float] = {}


def _hold_stop_locked(reason: str) -> None:
    """Switch the held pump off. The caller already holds _hold_lock.

    CLEARING THE STATE IS IN A `finally`
        Everything above it talks to hardware, and hardware is where the
        surprises are. When one of those steps raised, this function
        walked out with _hold still naming a pump: the screen then
        refused every other pump with "Bơm 3 đang được giữ", and because
        hold_pump() only restarts the watchdog on the branch where no
        pump is held, nothing was left that could ever clear it. A
        restart of the service was the only way out.

        The bookkeeping is this process's own and cannot fail. It must
        not be hostage to a pin that would not close.
    """
    pwm = _hold["pwm"]
    gpio = _hold["gpio"]

    try:
        if pwm is not None:
            try:
                pwm.value = 0
                pwm.close()
            except Exception as error:      # noqa: BLE001 - must still clear
                print(f"[hold] pump would not switch off cleanly: {error}",
                      file=sys.stderr, flush=True)

        # pwm.close() switches the pump off but leaves the line claimed by
        # this process, so the next order's process_runner could not take
        # it ('GPIO busy' on that pump). Freeing it is what actually hands
        # it back -- see _free_gpio_line().
        if gpio is not None:
            _free_gpio_line(gpio)

        if _hold["pump"] is not None:
            held = time.monotonic() - _hold["started"]
            print(f"[hold] pump {_hold['pump']} off after {held:.1f}s "
                  f"({reason})", flush=True)
    finally:
        if _hold["token"]:
            _hold_released[_hold["token"]] = time.monotonic()

        _hold.update({"pump": None, "pwm": None, "gpio": None, "token": "",
                      "deadline": 0.0, "started": 0.0})

    # Forget presses that ended long enough ago to be beyond any
    # in-flight request.
    cutoff = time.monotonic() - HOLD_MEMORY_SECONDS
    for old_token in [t for t, when in _hold_released.items() if when < cutoff]:
        _hold_released.pop(old_token, None)


def _hold_watchdog() -> None:
    """Stop the pump the moment the messages stop arriving.

    The body is wrapped because this thread is the only thing that can
    switch a pump off when the browser goes away, and a thread that dies
    takes that guarantee with it silently. It died exactly once for real
    -- on the NameError described in _free_gpio_line() -- and the machine
    then held a pump on until the service was restarted. Whatever goes
    wrong on one pass, there has to be another pass.
    """
    while True:
        time.sleep(HOLD_WATCH_SECONDS)

        try:
            with _hold_lock:
                if _hold["pump"] is None:
                    continue

                now = time.monotonic()

                if now >= _hold["deadline"]:
                    _hold_stop_locked("no longer held")
                elif now - _hold["started"] >= HOLD_MAX_SECONDS:
                    _hold_stop_locked(
                        f"held longer than {HOLD_MAX_SECONDS:.0f}s")
        except Exception as error:      # noqa: BLE001 - must keep watching
            print(f"[hold] watchdog pass failed: {error}",
                  file=sys.stderr, flush=True)


def hold_pump(pump_number: int, token: str = "") -> tuple[bool, str]:
    """Start the pump, or keep one already running alive.

    Called repeatedly while the button is down. The first call opens the
    pump; every later one just pushes the deadline out.

    WHY EACH PRESS CARRIES A TOKEN
        The messages are asynchronous, so one sent a moment before the
        button came up can arrive a moment AFTER the release did. Without
        a token that late arrival looks like a fresh press: the pump
        switches back on and runs until the watchdog notices, about a
        second of pouring nobody asked for.

        The token names one press. Once that press has been released the
        token is dead, and anything still carrying it is ignored.
    """
    global _hold_watcher

    reason = order_in_progress()

    if reason:
        return False, reason

    if busy():
        return False, "Đang chạy một bài kiểm tra khác."

    from pump_control.prime_all import pump_lines

    line = next((item for item in pump_lines()
                 if item["pump"] == pump_number), None)

    # Importing prime_all pulls in loadcell.loadcell, which claims GPIO
    # 4 and 18 at IMPORT time and never lets go on its own. Hold-to-run
    # only needs the pump's own pin from pump_lines() -- it never reads
    # the scale -- so the scale's pins are handed straight back here.
    #
    # Without this, one press of a pump button on the test screen left
    # this process holding 4/18 for good, and the next order's
    # process_runner subprocess died with "GPIO busy" trying to claim
    # them. Placed before every return below, not just the successful
    # one, so a refused press cannot leak them either. The jobs that DO
    # use the scale reclaim it themselves through _open_loadcell().
    _cleanup_loadcell()

    if line is None:
        return False, f"Không có bơm số {pump_number}."

    with _hold_lock:
        # A straggler from a press that has already ended.
        if token and token in _hold_released:
            return False, "Lần giữ này đã kết thúc."

        if _hold["pump"] not in (None, pump_number):
            return False, f"Bơm {_hold['pump']} đang được giữ."

        # Same pump, different press: the first must be released before
        # the second starts, or two overlapping presses would share one
        # deadline and neither could stop the other.
        if _hold["pump"] == pump_number and token and _hold["token"] \
                and token != _hold["token"]:
            return False, "Lần giữ trước chưa kết thúc."

        now = time.monotonic()

        if _hold["pump"] is None:
            from gpiozero import PWMLED

            from order.process_runner import PUMP_FREQUENCY_HZ

            pwm = PWMLED(line["gpio"], frequency=PUMP_FREQUENCY_HZ)
            pwm.value = 1.0
            _hold.update({"pump": pump_number, "pwm": pwm,
                          "gpio": line["gpio"],
                          "token": token, "started": now})
            print(f"[hold] pump {pump_number} on", flush=True)

            if _hold_watcher is None or not _hold_watcher.is_alive():
                _hold_watcher = threading.Thread(
                    target=_hold_watchdog, name="pump-hold", daemon=True)
                _hold_watcher.start()

        _hold["deadline"] = now + HOLD_TIMEOUT_SECONDS
        held = now - _hold["started"]

    return True, f"{held:.1f}"


def release_pump(token: str = "") -> tuple[bool, str]:
    """Stop immediately, without waiting for the watchdog.

    The token is remembered as ended, so a heartbeat still crossing the
    network cannot restart the pump behind the release.
    """
    with _hold_lock:
        if token and _hold["pump"] is None:
            # Released twice, or released before the first beat arrived.
            # Remember it anyway -- that is the case this exists for.
            _hold_released[token] = time.monotonic()
            return True, ""

        if token and _hold["token"] and token != _hold["token"]:
            # A release for an older press; the current one keeps running.
            _hold_released[token] = time.monotonic()
            return True, ""

        _hold_stop_locked("released")

    return True, ""


def held_pump() -> int | None:
    """Which pump is being held, if any. For the status endpoint."""
    with _hold_lock:
        return _hold["pump"]


def prime_job(pumps: list[int] | None):
    """Build the worker that primes the given pumps (None = all of them)."""

    def run(job: Job) -> None:
        import collections
        import json

        from configuration.configuration import PUMP_CALIB_FILE
        from loadcell.loadcell import WINDOW_SIZE, load_calibration, tare
        from loadcell.loadcell_robust import read_weight_robust
        from pump_control import prime_all

        _open_loadcell()
        load_calibration()

        try:
            with open(PUMP_CALIB_FILE) as handle:
                calibration = json.load(handle)
        except (OSError, ValueError):
            calibration = {}
            job.log("Chưa có hiệu chuẩn bơm — dùng thời gian tối đa.")

        lines = prime_all.pump_lines()

        if pumps:
            lines = [line for line in lines if line["pump"] in set(pumps)]

        if not lines:
            raise RuntimeError("Không có bơm nào để mồi.")

        with job.lock:
            job.total = len(lines)

        window: collections.deque = collections.deque(maxlen=WINDOW_SIZE)

        for _ in range(WINDOW_SIZE * 2):
            read_weight_robust(window)
            time.sleep(0.02)

        job.log("Kiểm tra cân...")
        healthy, message = prime_all.check_scale(window)
        job.log(f"  {message}")

        if not healthy:
            # The same refusal prime_all makes, for the same reason: every
            # stop condition below depends on this reading.
            raise RuntimeError(
                "Cân chưa tin được nên không mồi nước. " + message)

        job.log("Trừ bì ly...")
        tare(30)
        window.clear()

        for _ in range(WINDOW_SIZE * 2):
            read_weight_robust(window)
            time.sleep(0.02)

        for line in lines:
            if job.stop.is_set():
                job.log("Đã dừng theo yêu cầu.")
                break

            job.log(f"Bơm {line['pump']} ({line['name']})...")
            result = prime_all.prime_one(
                line, window, prime_all.PRIME_TARGET_GRAM,
                calibration, dry_run=False,
            )

            with job.lock:
                job.results.append(result)
                job.finished += 1

            job.log(f"  {result['result']}: {result['gram']:.1f} g "
                    f"trong {result['seconds']:.1f}s "
                    f"{result['note']}")

        good = sum(1 for r in job.snapshot()["results"]
                   if r["result"] == prime_all.RESULT_PRIMED)
        with job.lock:
            job.message = f"{good}/{job.finished} đường đạt yêu cầu."

    return run


# ────────────────────────────── PANEL LEDS ──────────────────────────────

def led_job(job: Job) -> None:
    """Light every panel lamp in turn, then all together.

    One at a time first, so a lamp that never lights can be told apart from
    one that is wired to the wrong position -- both look identical when
    they all come on at once.
    """
    from configuration.machine import PANEL_MAX_LEDS_ON
    from panel_control.panel import (
        ADDR_LED, ALL_HIGH, I2C_BUS, PANEL_COUNT, PCF8575, build_led_word,
    )

    device = PCF8575(I2C_BUS, ADDR_LED)

    try:
        device.write_all(ALL_HIGH)      # everything off
        job.log(f"Bật lần lượt {PANEL_COUNT} đèn...")

        with job.lock:
            job.total = PANEL_COUNT + 1

        for panel_id in range(PANEL_COUNT):
            if job.stop.is_set():
                job.log("Đã dừng theo yêu cầu.")
                break

            device.write_all(build_led_word([panel_id]))
            job.log(f"  đèn {panel_id} đang sáng")

            with job.lock:
                job.finished += 1

            time.sleep(LED_STEP_SECONDS)

        # Từng NHÓM, không phải cả 16 cùng lúc.
        #
        # Bản trước bật cả mười sáu đèn trong 1,2 giây. Đèn sáng nghĩa là
        # chip PCF8575 hút dòng về GND, mà nó chỉ chịu khoảng 100 mA cho cả
        # gói -- mười sáu đèn vượt xa mức đó. Chip latch-up: ngừng trả lời
        # địa chỉ I2C của nó cho tới khi ai đó rút điện. Đo được trên máy
        # này 08/09/2026: sau mỗi lần chạy test, i2cdetect chỉ còn 0x20,
        # mất 0x21, và chỉ cắm lại nguồn mới thấy lại.
        #
        # Chia nhóm vẫn cho thấy mọi đèn cùng sáng theo cụm, mà không lần
        # nào vượt giới hạn. Số đèn mỗi nhóm ở configuration/machine.py.
        if not job.stop.is_set():
            job.log(f"Bật theo nhóm {PANEL_MAX_LEDS_ON} đèn...")

            for start in range(0, PANEL_COUNT, PANEL_MAX_LEDS_ON):
                if job.stop.is_set():
                    break

                group = range(start, min(start + PANEL_MAX_LEDS_ON,
                                         PANEL_COUNT))
                device.write_all(build_led_word(group))
                job.log(f"  đèn {group.start}–{group.stop - 1} đang sáng")
                time.sleep(LED_GROUP_SECONDS)

            device.write_all(ALL_HIGH)

            with job.lock:
                job.finished += 1

        with job.lock:
            job.message = "Xong. Đèn nào không sáng là đèn đó hỏng hoặc sai dây."
    finally:
        # Always leave the panel dark, however this ended.
        try:
            device.write_all(ALL_HIGH)
        except Exception:      # noqa: BLE001
            pass
        device.close()


# ───────────────────────────── PANEL BUTTONS ─────────────────────────────

def button_job(job: Job) -> None:
    """Light one lamp at a time and wait for its button to be pressed.

    Pairing each lamp with its own button is what makes this a wiring test
    rather than a button test: pressing the lit one proves the LED map and
    the button map agree, which is the mistake that actually happens.
    """
    from panel_control.panel import (
        ADDR_BUTTON, ADDR_LED, ALL_HIGH, I2C_BUS, PANEL_COUNT, PCF8575,
        build_led_word, button_pin_to_panel_id,
    )

    leds = PCF8575(I2C_BUS, ADDR_LED)
    buttons = PCF8575(I2C_BUS, ADDR_BUTTON)

    try:
        leds.write_all(ALL_HIGH)
        buttons.write_all(ALL_HIGH)     # release the inputs

        with job.lock:
            job.total = PANEL_COUNT

        job.log(f"Bấm nút đang sáng. Bỏ qua sau {BUTTON_TEST_SECONDS:g}s.")
        deadline = time.monotonic() + BUTTON_TEST_SECONDS

        for panel_id in range(PANEL_COUNT):
            if job.stop.is_set() or time.monotonic() > deadline:
                job.log("Hết giờ hoặc đã dừng.")
                break

            leds.write_all(build_led_word([panel_id]))
            job.log(f"  đang chờ nút {panel_id}...")
            seen = False

            while time.monotonic() < deadline and not job.stop.is_set():
                state = buttons.read_all()

                for bit in range(PANEL_COUNT):
                    # Active low: a 0 bit is a pressed button.
                    if not state & (1 << bit):
                        pressed_id = button_pin_to_panel_id(bit)

                        with job.lock:
                            if pressed_id not in job.pressed:
                                job.pressed.append(pressed_id)

                        if pressed_id == panel_id:
                            seen = True
                        else:
                            job.log(f"  ! nút {pressed_id} được bấm, "
                                    f"đang chờ {panel_id} — kiểm tra dây")

                if seen:
                    break

                time.sleep(BUTTON_POLL_SECONDS)

            with job.lock:
                job.finished += 1
                job.results.append({
                    "panel": panel_id,
                    "result": "OK" if seen else "KHÔNG BẤM",
                })

            job.log(f"  nút {panel_id}: {'nhận được' if seen else 'không thấy'}")

            # Wait for release, so one long press does not answer the next
            # prompt as well.
            while (not job.stop.is_set()
                   and buttons.read_all() != ALL_HIGH
                   and time.monotonic() < deadline):
                time.sleep(BUTTON_POLL_SECONDS)

        ok = sum(1 for r in job.snapshot()["results"] if r["result"] == "OK")
        with job.lock:
            job.message = f"{ok}/{PANEL_COUNT} nút phản hồi đúng đèn."
    finally:
        try:
            leds.write_all(ALL_HIGH)
        except Exception:      # noqa: BLE001
            pass
        leds.close()
        buttons.close()


# ────────────────────────────── SCALE CHECK ──────────────────────────────

def scale_job(job: Job) -> None:
    """Read the load cell and say whether it can be trusted."""
    import collections

    from loadcell.loadcell import WINDOW_SIZE, load_calibration
    from loadcell.loadcell_robust import read_weight_robust
    from pump_control import prime_all

    _open_loadcell()
    load_calibration()
    window: collections.deque = collections.deque(maxlen=WINDOW_SIZE)

    for _ in range(WINDOW_SIZE * 2):
        read_weight_robust(window)
        time.sleep(0.02)

    job.log("Đang lấy mẫu cân...")
    healthy, message = prime_all.check_scale(window)
    job.log(message)

    current = prime_all.steady_read(window)

    if current is not None:
        job.log(f"Khối lượng hiện tại: {current:.2f} g")

    with job.lock:
        job.message = message
        job.results.append({
            "healthy": healthy,
            "gram": round(current, 2) if current is not None else None,
        })

    if not healthy:
        raise RuntimeError(message)


# ══════════════════════════════════════════════════════════════════════
# TEST MODE
# ══════════════════════════════════════════════════════════════════════
#
# The flag itself, and the thread that watches panel button 15, live in
# panel_control/button_watch.py and are owned by order/run_flow.py.
#
# This module only READS the flag. It used to own the watcher too, which
# meant button 15 worked only while this server happened to be running, and
# this server had to guess whether an order was in progress by probing a
# port. run_flow is always up on a machine in service and starts the runner
# itself, so it knows both things first-hand.

from panel_control.button_watch import (        # noqa: E402
    MODE_FILE as TEST_MODE_FILE,
    TOGGLE_PANEL_ID,
    is_open as test_mode_open,
    read_mode as read_test_mode,
    write_mode as write_test_mode,
)
