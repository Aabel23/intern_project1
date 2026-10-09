"""Drive one whole order, from the scanned code to the finished drink.

WHAT THIS FILE IS
    The conductor. Every part of the order already exists on its own --
    the scanner writes codes, qr_to_recipe builds a recipe, process_runner
    pours it -- and this is what runs them in order and hands off between
    them. Nothing here talks to hardware or to MySQL directly.

THE FLOW OF ONE ORDER
    0.  Start scan/scanner.py, which reads the USB scanner and writes
        scan/raw_qr.json. Without it nothing ever fills that file and this
        loop waits for ever -- so this owns it rather than assuming
        somebody remembered to start it in another terminal.

    1.  Wait for a new code in scan/raw_qr.json. The store screen shows a
        QR, the handheld scanner reads it, and scan/scanner.py overwrites
        that file. "New" means the code or its timestamp changed, so
        scanning the same drink twice runs twice.

    2.  order/qr_to_recipe.py turns the code into order/current_recipe.json:
        the SKU finds the base recipe in the database, and the pairs in the
        payload adjust it -- a chosen weight replaces an amount, a boolean
        keeps or drops a topping.

    3.  Start order/process_runner.py, which serves the bartender screen on
        GUI_PORT and stops at its first gate, waiting for the cup.

    4.  Only once that server is actually accepting connections, write
        order/handoff.json. The store screen polls that file and sends the
        browser to the bartender screen. Writing it earlier would send the
        browser to a port nothing was listening on yet.

    5.  Wait for the runner to finish, then clear the handoff and both
        order files and go back to step 1 for the next customer. That
        clearing happens however the order ended -- finished, cancelled or
        failed -- so nothing stale is ever left for the next one.

WHY THE BROWSER IS MOVED BY A FILE
    A Python process cannot navigate a browser. It may not even be on the
    same machine -- the shop screen could be a tablet pointed at the Pi.
    So the store page polls order/handoff.json and moves itself when the
    order_id changes. That works for any browser on any host, which
    webbrowser.open() would not: that opens a window on whatever machine
    runs this script.

    The page builds the address from its own location.hostname and the
    port in the handoff file, so reaching the shop screen on localhost, on
    the LAN address or over Tailscale all send the browser somewhere it
    can actually reach.

WHY TWO PORTS
    This script's runner serves the bartender screen on GUI_PORT (8000)
    because that server also answers /api/confirm, /api/process/button and
    /api/process/detect -- the three requests the screen makes. A plain
    file server cannot release the machine's gates. The store screen can
    be served by anything, including the same port when a run is active.

ONLY ONE FLOW AT A TIME
    An advisory lock on order/.run_flow.lock is taken at startup and held
    until the process ends. A second instance is told who holds it and
    exits; with --wait it queues instead and takes over when the first
    finishes. The kernel releases the lock however the process dies, so a
    crash never leaves the machine locked out.

RUNNING IT
    python3 -m order.run_flow                  # serve orders until stopped
                                               # (starts the scanner too)
    python3 -m order.run_flow --no-scanner     # when scan.scanner runs
                                               # separately already
    python3 -m order.run_flow --once           # one order, then exit
    python3 -m order.run_flow --dry-run        # rehearse: no pumps, no stock,
                                               # and no screen -- the runner
                                               # serves nothing under dry-run
    python3 -m order.run_flow --payload 0006...  # skip the scanner
    python3 -m order.run_flow --no-ticket        # bench: any code, reusable

    Ctrl+C stops between orders, and interrupts the runner during one.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

if __package__ in {None, ""}:
    project_dir = str(Path(__file__).resolve().parent.parent)

    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

from configuration import machine
from database import error_log, order_ticket
from panel_control import button_watch
from order.qr_to_recipe import (
    CURRENT_RECIPE_FILE,
    RAW_QR_FILE,
    OrderError,
    ScanError,
    busy_steps,
    load_current_recipe,
    process_payload,
)

from flexmix_debug import trace          # noqa: E402


ORDER_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ORDER_DIR.parent

HANDOFF_FILE = ORDER_DIR / "handoff.json"

# A refused scan, for the store screen to pop up. Polled by
# store_gui/drinks-pos.js on the same tick as the handoff above.
SCAN_NOTICE_FILE = ORDER_DIR / "scan_notice.json"

# How the store screen should dress a notice. A misread is not a fault and
# must not look like one: the customer has done nothing wrong and the fix is
# in their hands, so it gets a calmer box that asks them to try again.
NOTICE_KIND_REFUSED = "refused"      # the code was read and is not valid
NOTICE_KIND_RESCAN = "rescan"        # the code was not read properly
NOTICE_KIND_FAULT = "fault"          # the machine broke
NOTICE_KIND_RESTART = "restart"      # panel button 14; back in seconds

# Held for the life of the process so only one flow can drive the machine.
LOCK_FILE = ORDER_DIR / ".run_flow.lock"

# An append-only account of every order. process_runner writes to the
# terminal, which scrolls away and is gone once the window closes -- and
# "the machine stopped and I do not know why" is unanswerable without it.
FLOW_LOG = ORDER_DIR / "flow.log"

# How long to leave the cancelled recipe readable before killing the runner
# that serves it. The bartender screen polls about eight times a second, so
# this is several chances to see it -- long enough to be reliable, short
# enough that nobody notices Ctrl+C taking a moment.
CANCEL_NOTICE_SECONDS = 0.7

# The runner's own server. Loopback only: no browser reaches it, because
# store_gui/serve.py relays the bartender screen's controls to it. It stays
# a separate process on purpose -- see start_runner() -- so a crash mid-pour
# cannot take the always-on server with it.
GUI_PORT = machine.RUNNER_PORT
GUI_PATH = "/bartender_gui/index.html"


def store_port() -> int:
    """The one public port. Read from the server that owns it."""
    from store_gui.serve import DEFAULT_PORT

    return DEFAULT_PORT

SCAN_POLL_SECONDS = 0.5

# How long to wait for the runner's server to start listening before giving
# up on it. Generous: the runner imports gpiozero and opens the I2C bus
# first, which is slow on a cold Pi.
SERVER_START_TIMEOUT_SECONDS = 30.0
SERVER_POLL_SECONDS = 0.25

# Long enough for scanner.py to open the port and fail if it cannot.
SCANNER_START_SECONDS = 2.0

# How long to leave the finished order on disk before wiping it. The
# bartender screen shows a thank-you and counts down RETURN_SECONDS (5) in
# bartender_gui/js/guide.js before returning to the store screen, and it is
# still polling current_recipe.json the whole time. Clearing the moment the
# runner exits would blank the screen mid-countdown.
CLEAR_DELAY_SECONDS = 8.0


class FlowError(Exception):
    """Raised when an order cannot be carried through."""


def acquire_single_instance_lock(
    path: Path,
    wait: bool = False,
) -> tuple[object | None, str]:
    """Take the flow lock. Returns (handle, holder) -- handle is None if busy.

    One machine, one flow. Two instances would both watch raw_qr.json, both
    build a recipe from the same scan, and both start a runner: one wins
    port 8000 and the other dies, but not before the losing runner has been
    handed a recipe. The port check at startup does not catch this, because
    two IDLE instances conflict over nothing until a code arrives.

    An advisory lock rather than a PID file: the kernel drops it when the
    process ends however it ends, including kill -9 and a power cut, so
    there is no stale lock to clean up by hand.

    The file is opened for append, never truncated on the way in -- opening
    it "w" would erase the holder's own PID and leave nothing to report.
    """
    handle = open(path, "a+", encoding="utf-8")
    flags = fcntl.LOCK_EX if wait else fcntl.LOCK_EX | fcntl.LOCK_NB

    try:
        fcntl.flock(handle.fileno(), flags)
    except OSError:
        handle.seek(0)
        holder = handle.read().strip() or "không rõ"
        handle.close()
        return None, holder

    handle.seek(0)
    handle.truncate()
    handle.write(f"{os.getpid()}\n")
    handle.flush()
    return handle, str(os.getpid())


def log_event(message: str) -> None:
    """Append one line to flow.log, and echo it to the terminal.

    Never raises: a full or read-only disk must not take the machine down
    in the middle of a drink.
    """
    line = f"{now_text()} {message}"
    print(f"[flow] {message}", flush=True)

    try:
        with open(FLOW_LOG, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


def now_text() -> str:
    """Local time as ISO 8601 with an offset, as the rest of the project."""
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


@trace
def read_scan(path: Path) -> tuple[str, str] | None:
    """Return (code, timestamp) from raw_qr.json, or None if there is none.

    A missing or malformed file is not an error here: the scanner may not
    have written anything yet, and this is called in a polling loop.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            content = json.load(handle)
    except (FileNotFoundError, ValueError, OSError):
        return None

    if isinstance(content, list):
        content = content[-1] if content else None

    if not isinstance(content, dict):
        return None

    code = content.get("qr_code") or content.get("payload")

    if not code:
        return None

    return str(code), str(content.get("timestamp", ""))


# What store_gui/serve.py writes into raw_qr.json when an order is started
# from the QR popup instead of the scanner. The scanner writes no source at
# all, so anything else -- including nothing -- means a real scan.
SOURCE_STORE_SCREEN = "store_screen"


@trace
def scan_source(path: Path) -> str:
    """Return where the code in raw_qr.json came from, or "" if unsaid.

    Read separately from read_scan() rather than widened into its tuple:
    that tuple is compared against the last one to notice a NEW scan, and
    the answer to "is this a different scan" must not start depending on
    where the scan came from.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            content = json.load(handle)
    except (FileNotFoundError, ValueError, OSError):
        return ""

    if isinstance(content, list):
        content = content[-1] if content else None

    if not isinstance(content, dict):
        return ""

    return str(content.get("source") or "")


@trace
def wait_for_new_scan(path: Path, seen: tuple[str, str] | None) -> tuple[str, str]:
    """Block until raw_qr.json holds a scan different from `seen`.

    Compares the code AND its timestamp, so the same drink ordered twice in
    a row is two orders rather than one ignored repeat.
    """
    print(f"[flow] Đang chờ mã QR mới trong {path.name}... (Ctrl+C để dừng)",
          flush=True)

    while True:
        current = read_scan(path)

        if current is not None and current != seen:
            return current

        time.sleep(SCAN_POLL_SECONDS)


def port_is_open(port: int, host: str = "127.0.0.1") -> bool:
    """Return whether something is accepting connections on this port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.4)
        return probe.connect_ex((host, port)) == 0


@trace
def wait_for_server(port: int, process: subprocess.Popen) -> None:
    """Block until the runner's server answers, or the runner dies first.

    Raises FlowError rather than waiting out the timeout when the runner
    has already exited -- that is the common case when a recipe is bad,
    and its own message is more useful than "the server never started".
    """
    deadline = time.monotonic() + SERVER_START_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise FlowError(
                f"process_runner đã thoát sớm (mã {process.returncode}) "
                "trước khi mở được màn hình pha chế."
            )

        if port_is_open(port):
            return

        time.sleep(SERVER_POLL_SECONDS)

    raise FlowError(
        f"Màn hình pha chế không mở được cổng {port} sau "
        f"{SERVER_START_TIMEOUT_SECONDS:g}s."
    )


@trace
def write_handoff(path: Path, document: dict, port: int) -> None:
    """Tell the store screen to move to the bartender screen.

    Written atomically, because the store screen polls this file about once
    a second and must never read it half-written.

    Only the port and path are given, not a whole URL: the page builds the
    address from its own hostname, so whichever address the shop screen
    used to reach the store page keeps working.
    """
    save_handoff(path, {
        "order_id": document.get("order_id"),
        "drink_id": document.get("drink_id"),
        "drink_name": document.get("drink_name"),
        "gui_port": port,
        "gui_path": GUI_PATH,
        "created_at": now_text(),
    })


def save_handoff(path: Path, payload: dict) -> None:
    """Write the handoff atomically. Never seen half-written by the poller."""
    temporary = path.with_name(f".{path.name}.tmp")

    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())

    os.replace(temporary, path)


@trace
def mark_handoff_finished(path: Path) -> None:
    """Say the drink is DONE while this flow tidies up after it.

    WHY THE HANDOFF CANNOT SIMPLY GO HERE
        clear_order_files() below empties scan/raw_qr.json, so a label
        scanned during the tidy-up is wiped instead of served -- silently,
        which is the exact failure the store screen's banner exists to
        prevent. The machine really is not ready yet, so the file stays.

    WHY THE FLAG IS NEEDED ANYWAY
        "Busy" and "making YOUR drink" are not the same thing for these
        seconds. The bartender screen hands the browser back 5s after the
        drink finishes (RETURN_SECONDS in bartender_gui/js/guide.js) while
        this flow holds the handoff for CLEAR_DELAY_SECONDS from the
        runner's exit -- so the customer lands on the store screen holding
        a finished drink and was told, for about four seconds, that the
        machine was still pouring it and that they should go and finish or
        cancel the order. Both halves of that were false.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return          # already cleared, or never written: nothing to correct

    payload["finished"] = True
    payload["finished_at"] = now_text()

    try:
        save_handoff(path, payload)
    except OSError as error:
        # Cosmetic only -- the banner keeps the old wording for a few
        # seconds. Not worth failing a poured drink over.
        print(f"[flow] Không cập nhật được {path.name}: {error}",
              file=sys.stderr)


@trace
def write_scan_notice(path: Path, message: str, payload: str,
                      title: str = "", kind: str = NOTICE_KIND_REFUSED) -> None:
    """Put a refused scan on the store screen.

    WHY THIS FILE EXISTS
        A rejected code used to be a line in this terminal, which is behind
        the machine and facing away from the person holding the label. The
        customer scanned, nothing happened, and nothing on any screen said
        why. The one message that matters most -- "this code has already
        been used" -- was the one nobody could see.

    WHY ONLY BEFORE THE HANDOFF
        Written for failures that happen while the customer is still
        looking at the store screen: a refused ticket, a code for a drink
        with no recipe, a machine that would not start. Once the handoff is
        written the browser has moved to the bartender screen, which shows
        its own errors -- a notice raised then would be read by nobody and
        then ambush the next customer when the store screen came back.

    The id is what makes the page treat this as new. Two identical refusals
    a minute apart are two events the customer needs to see, and comparing
    message text would collapse them into one.
    """
    notice = {
        "id": uuid.uuid4().hex,
        "kind": kind,            # how the page should dress it
        "title": title,          # blank means the page's own default
        "message": message,
        "payload": payload,
        "created_at": now_text(),
    }

    temporary = path.with_name(f".{path.name}.tmp")

    try:
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(notice, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temporary, path)
    except OSError as error:
        # Never worth failing an order over. The message still reaches the
        # terminal, which is where it went before this existed.
        print(f"[flow] Không báo được lên màn hình bán hàng: {error}",
              file=sys.stderr, flush=True)


# How long to keep the store screen alive after writing the restart
# notice.
#
# It polls once a second (HANDOFF_POLL_MS in drinks-pos.js), so the box
# appears somewhere in the first second and the rest is reading time.
# Two seconds left as little as one on screen before everything went
# dark, which reads as nothing having happened at all. Five gives a
# customer time to read a sentence in their own language and understand
# that the blank screen coming next is expected.
STORE_RESTART_NOTICE_SECONDS = 5.0


def warn_store_screen_of_restart() -> None:
    """Put "the machine is restarting" on the store screen, then wait.

    Panel button 14 pressed with no order open: the customer is looking at
    the store screen, which is about to go blank for a few seconds. The
    bartender screen has its own card for the same press (see
    order/process_runner.py), but there is no bartender screen when
    nothing is being poured.

    Read on the way DOWN and gone by the time the screen returns:
    startup clears it with every other notice. Coming back to a popup
    about a restart that has already finished is noise, so the whole job
    of this warning is done in the seconds below.
    """
    write_scan_notice(
        SCAN_NOTICE_FILE,
        "Máy sẽ sẵn sàng lại sau vài giây. Quý khách vui lòng đợi.",
        "",
        title="Máy đang khởi động lại",
        kind=NOTICE_KIND_RESTART,
    )
    print("[flow] Đã báo màn hình bán hàng: máy sắp khởi động lại.",
          flush=True)
    time.sleep(STORE_RESTART_NOTICE_SECONDS)


@trace
def clear_scan_notice(path: Path) -> None:
    """Take any old refusal down before a new order begins."""
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError as error:
        print(f"[flow] Không xóa được {path.name}: {error}",
              file=sys.stderr, flush=True)


@trace
def reset_machine_hardware(reason: str) -> None:
    """Put the machine back to rest: pumps off and free, panel LEDs dark.

    WHY THIS IS NEEDED AT ALL
        Both process_runner and panel_worker tidy up in a finally, which
        covers every ordinary end of an order and none of the others. A
        process that is signalled rather than asked -- systemd restarting
        the service, panel button 14, a kill, a power cut -- never runs
        them. What is left behind is a PCF8575 still holding the last LED
        word it was sent, and pump pins still doing whatever the kernel
        last had them do.

        So the machine could come up with the lights of a drink nobody is
        making, and in the worst case a pump still turning.

    WHEN IT RUNS
        Only when there is no order: at startup, before the first scan is
        taken, and after each runner exits, before the button watcher
        takes the panel back. Never while a drink is being poured, where
        it would fight the process doing the pouring for the same pins.

    Never fatal. This makes the machine tidy; it cannot be a reason the
    machine will not start.
    """
    print(f"[flow] Đưa phần cứng về trạng thái nghỉ ({reason})...", flush=True)

    try:
        from pump_control.pump_ml_parallel import all_pumps_off

        all_pumps_off()
    except Exception as error:      # noqa: BLE001 - tidy-up, not a gate
        print(f"[flow] Không tắt được bơm: {error}", file=sys.stderr, flush=True)

    try:
        from panel_control.panel import reset_panel

        reset_panel()
        print("[flow] Đã tắt toàn bộ đèn bảng nút.", flush=True)
    except Exception as error:      # noqa: BLE001 - tidy-up, not a gate
        print(f"[flow] Không reset được bảng đèn: {error}",
              file=sys.stderr, flush=True)


@trace
def clear_order_files(recipe_path: Path, raw_qr_path: Path) -> None:
    """Wipe the finished order so nothing stale is left for the next one.

    Both files are emptied to `{}` rather than deleted: they stay valid
    JSON, so the screens and qr_to_recipe read them as "no order" instead
    of erroring on a missing file.

    Emptying raw_qr.json also means the next identical scan is seen as new.
    Left in place, a customer ordering the same drink twice in a row would
    write a byte-identical file and the watcher would wait for ever.

    Either path may be None, to keep that file. A failed order keeps its
    recipe: it is the record of which step stopped and why.
    """
    for path in (recipe_path, raw_qr_path):
        if path is None:
            continue

        try:
            temporary = path.with_name(f".{path.name}.tmp")
            temporary.write_text("{}\n", encoding="utf-8")
            os.replace(temporary, path)
            print(f"[flow] Đã xóa nội dung {path.name}.", flush=True)
        except OSError as error:
            print(f"[flow] Không xóa được {path.name}: {error}",
                  file=sys.stderr, flush=True)


@trace
def announce_cancelled(recipe_path: Path) -> None:
    """Write "cancelled" into the recipe so the screen can go home at once.

    The bartender screen polls this file through the runner's HTTP server
    several times a second. Writing here while that server is still up is
    the only channel left to it -- run_flow cannot reach the browser, and
    the moment the runner is terminated the page can reach nothing at all.

    So the order is: mark the file, pause long enough for one poll to land,
    and only then kill the runner. Without the pause the file changes and
    the server dies in the same instant, and the screen would fall back to
    the 15-second lost-contact timeout -- which eventually gets there, but
    tells the customer the machine broke when in fact somebody cancelled.

    Best effort throughout. A cancel must not be able to fail.
    """
    try:
        document = load_current_recipe(recipe_path) or {}

        if not document.get("order_id"):
            return          # nothing running; nothing to tell anyone

        document["cancelled_at"] = now_text()
        document["error"] = "Đơn đã bị hủy."
        document["updated_at"] = document["cancelled_at"]

        temporary = recipe_path.with_name(f".{recipe_path.name}.tmp")

        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(document, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temporary, recipe_path)
    except (OSError, ValueError) as error:
        print(f"[flow] Không báo được lệnh hủy lên màn hình: {error}",
              file=sys.stderr, flush=True)
        return

    # Waiting for the customer on the store screen when the browser lands
    # back there. The bartender screen's own card is gone by then -- it
    # navigated away -- so without this they arrive at the menu with no
    # explanation of why their drink stopped.
    write_scan_notice(
        SCAN_NOTICE_FILE,
        f"{document.get('drink_name') or 'Đơn này'} đã bị hủy. "
        "Vui lòng đặt lại đơn mới.",
        "",
        title="Đơn đã bị hủy",
        kind=NOTICE_KIND_FAULT,
    )

    # One poll of the bartender screen is ~120 ms; this leaves room for
    # several, and it is time a person spends letting go of Ctrl+C anyway.
    time.sleep(CANCEL_NOTICE_SECONDS)


@trace
def record_error(message: str, **context) -> None:
    """Put one flow-level fault in the error_log table. Never raises.

    The runner records what happens DURING a drink; this records what
    happens around it -- a code refused before the machine ever started, a
    runner that would not come up. Those never reach process_runner, so
    without this they would exist only in this terminal.

    It took a `category` until 2026-09-07, when that column was dropped.
    What kind of fault it is has to read from the sentence now, so the
    callers below say it in words.
    """
    try:
        error_log.log_error(message, **context)
    except Exception:      # noqa: BLE001 - never worsen an existing failure
        pass


TEST_MODE_POLL_SECONDS = 1.0


def test_mode_open() -> bool:
    """Has panel button 15 taken the machine out of service?

    Delegated to panel_control/button_watch.py, which also writes it, so
    there is one definition of what the flag means. A missing or unreadable
    file reads as "not in test mode", so a maintenance screen that was
    never started can never stop the shop by failing.
    """
    return button_watch.is_open()


def test_mode_id() -> str:
    """Which test-mode generation the machine is on. '' when never set.

    button_watch.write_mode() stamps a fresh id on EVERY flip, so this
    changes twice over one test session -- once on, once off. Comparing it
    against the last id we tidied up after is what lets this loop notice a
    session that began and ended entirely while it was blocked somewhere
    else. See wait_while_test_mode().
    """
    return str(button_watch.read_mode().get("id") or "")


# The test-mode generation whose GPIO this process has already handed
# back. Starts empty, so a run_flow that comes up after a crash mid-test
# tidies once on its first pass.
_test_mode_tidied_id: str = ""


def wait_while_test_mode() -> None:
    """Hold here until the machine is put back into service, then tidy up.

    Leaving test mode is the one moment where nothing in this process is
    meant to be holding hardware, so it is also where every GPIO line the
    test screen could have claimed is handed back -- see
    test_gui.hardware.release_all_gpio() for why closing a device is not
    enough to release its line. Without this, a pump run from the test
    screen left its line claimed and the next order's process_runner died
    with 'GPIO busy' on that pump.

    WHY THE RELEASE IS NOT INSIDE THE `if`
        It used to be: return early when test mode is shut, otherwise wait
        for it to close and release afterwards. Both of those are
        point-in-time reads, and this function is called from a loop that
        spends nearly all its time blocked in wait_for_new_scan() polling
        for a QR code. Turn test mode on, prime a pump, turn it off again
        while that block is in progress and NEITHER read ever sees it
        open -- so the release never ran and the pump's line stayed
        claimed for the life of the process.

        The mode file's id closes that gap: it moves on every flip, so a
        session this loop never witnessed still leaves a trace it can
        compare against. Now the release fires on the evidence that a
        session happened, not on having watched it end.
    """
    global _test_mode_tidied_id

    if test_mode_open():
        log_event("Chế độ test đang bật (nút bảng 15) — tạm dừng nhận đơn.")

        while test_mode_open():
            time.sleep(TEST_MODE_POLL_SECONDS)

        log_event("Đã tắt chế độ test — tiếp tục nhận đơn.")

    generation = test_mode_id()

    if generation != _test_mode_tidied_id:
        # Recorded before the release, not after: a release that throws
        # must not queue itself up to run again on every later order.
        # release_test_gpio() already swallows its own failures.
        _test_mode_tidied_id = generation
        release_test_gpio()


def release_test_gpio() -> None:
    """Hand back every GPIO the test screen may still be holding.

    Never raises: a machine that cannot tidy up must still go back into
    service, and the next order will report any pin it genuinely cannot
    claim.
    """
    try:
        from test_gui.hardware import release_all_gpio

        release_all_gpio()
    except Exception as error:      # noqa: BLE001 - must not block service
        print(f"[flow] Không giải phóng được GPIO sau chế độ test: {error}",
              file=sys.stderr, flush=True)


def warm_test_gui() -> bool:
    """Bring up the test screen's hardware helpers. False if unavailable.

    WHY THERE IS NO SERVER HERE ANY MORE
        There used to be one, on its own port. Every screen in this system
        is served from store_gui/serve.py now -- one address, up for as
        long as main.py is -- and that server answers the test screen's
        endpoints by calling test_gui.serve.handle_get/handle_post
        directly. It runs in this same process, so those are a function
        call away; a second port only ever added an address to get wrong.

        This still happens here, and early, for the reason the server was
        here: importing test_gui.hardware opens the panel and the load
        cell, and doing it on the first request would put that cost on a
        button press.

    Failure is not fatal: it costs the test screen, not the shop.
    """
    try:
        import test_gui.serve                        # noqa: F401
    except Exception as error:      # noqa: BLE001 - the shop comes first
        print(f"[flow] Không nạp được màn hình test: {error}",
              file=sys.stderr, flush=True)
        return False

    return True


@trace
def release_stranded_tickets() -> list[str]:
    """Free any ticket a previous run died holding. Returns the
    payload_hash values freed.

    Reported rather than done quietly: a freed ticket means a customer was
    charged for a drink the machine did not make, and that is worth a line
    in the log and a look at the machine.

    A database that cannot be reached is not fatal here. The machine can
    still serve customers whose codes are not stranded, and the next
    startup will try again -- refusing to run at all would turn one stuck
    ticket into a shop that cannot sell anything.
    """
    try:
        keys = order_ticket.release_stranded()
    except Exception as error:      # noqa: BLE001 - must not block startup
        print(f"[flow] Không kiểm tra được vé QR treo: {error}",
              file=sys.stderr, flush=True)
        return []

    for ticket_key in keys:
        # log_event echoes to the terminal itself, so this is one line on
        # screen and one in flow.log -- where it matters most, since the
        # terminal has usually scrolled away by the time anyone asks why a
        # customer's code stopped working.
        log_event(
            f"Vé QR (mã {ticket_key[:8]}...) còn treo từ lần chạy trước "
            f"(đơn hỏng giữa chừng) -- đã trả lại, khách quét lại được."
        )

    return keys


@trace
def settle_ticket(
    ticket_key: str | None, *, poured: bool, no_qr: bool = False,
) -> None:
    """Close out the QR ticket this order was started from.

    `ticket_key` is the payload's own SHA-256 hash (document["ticket_key"]
    from order/qr_to_recipe.py) -- protocol v1.4 payloads carry no serial,
    so the hash is what order_ticket.py looks a ticket up by. See
    database/order_ticket.py.

    Poured: the ticket is spent and the label is now worthless, which is
    the whole point of it. That is the ending however the order began.

    Not poured -- a fault, a cancel, a runner that never started -- and it
    came from a SCAN: the ticket goes back to 'unused' so the same label
    works again. The customer paid and got nothing, and a machine that
    eats the code as well as the order leaves them unable to prove either.

    Not poured and started from the store screen with no scan: there is no
    label to hand back, so 'unused' would be a lie about a code that
    exists nowhere. It ends at 'noqr_err'. See database/order_ticket.py.

    Failures here are reported but never raised. This runs inside the
    finally that also clears the order files, and a ticket that cannot be
    settled must not stop the next customer from being served -- a stuck
    'in_progress' row ages out at TICKET_LIFETIME_HOURS on its own.
    """
    if ticket_key is None:
        return

    short = ticket_key[:8]

    if poured:
        action = "đánh dấu đã dùng"
    elif no_qr:
        action = "đánh dấu lỗi (chạy không quét)"
    else:
        action = "trả lại"

    try:
        if poured:
            changed = order_ticket.complete(ticket_key)
        elif no_qr:
            changed = order_ticket.mark_failed(ticket_key)
        else:
            changed = order_ticket.release(ticket_key)
    except Exception as error:      # noqa: BLE001 - must not break cleanup
        print(f"[flow] Không {action} được vé QR (mã {short}...): {error}",
              file=sys.stderr, flush=True)
        return

    if changed:
        print(f"[flow] Đã {action} vé QR (mã {short}...).", flush=True)
    else:
        # Not an error worth shouting about: it means the row was not
        # in_progress, which is what a --no-ticket run or a second settle
        # of the same order looks like.
        log_event(f"Vé QR (mã {short}...) không ở trạng thái đang pha, bỏ qua.")


@trace
def clear_handoff(path: Path) -> None:
    """Drop the handoff so a reloaded store screen does not jump again."""
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError as error:
        print(f"[flow] Không xóa được {path.name}: {error}", file=sys.stderr)


def reap_orphan_scanners() -> int:
    """Kill scanners left behind by a previous run. Returns how many.

    WHY THIS IS NEEDED
        The scanner is a child of this process and is stopped in the finally
        below -- but a finally does not run when the parent is killed with
        SIGTERM, or dies with the machine. The child survives, gets
        reparented to init, and keeps the serial port locked EXCLUSIVELY.
        Every later run then fails to open it:

            Could not exclusively lock port /dev/serial/by-id/... :
            [Errno 11] Resource temporarily unavailable

        The flow carries on watching raw_qr.json, so it looks like it is
        working -- but nothing is writing that file any more, and no scan
        ever arrives. A machine that silently stops taking orders.

    WHAT IT WILL AND WILL NOT KILL
        Only processes running scan.scanner whose parent is init, which is
        the signature of an orphan. A scanner someone started deliberately
        in another terminal has that terminal as its parent and is left
        alone -- as is anything else on the machine. And this only runs
        when this flow is about to start a scanner of its own, so
        --no-scanner never touches anybody else's.
    """
    killed = 0

    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue

        try:
            cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ")

            if b"scan.scanner" not in cmdline:
                continue

            # Field 4 of /proc/<pid>/stat is the parent pid. Reading it
            # from stat rather than status because the comm field can
            # contain spaces and brackets; the ppid is positional after
            # the closing bracket.
            stat = (entry / "stat").read_text()
            ppid = int(stat[stat.rindex(")") + 2:].split()[1])

            if ppid != 1:
                continue        # someone is still looking after it

            os.kill(int(entry.name), signal.SIGTERM)
            killed += 1
            log_event(f"Đã dọn máy quét mồ côi (PID {entry.name}) "
                      f"còn giữ cổng từ lần chạy trước.")
        except (OSError, ValueError, IndexError):
            continue            # it exited under us, or is not ours to read

    if killed:
        # Give the kernel a moment to release the port before the new
        # scanner tries to claim it.
        time.sleep(1.0)

    return killed


@trace
def start_scanner() -> subprocess.Popen | None:
    """Start scan/scanner.py, the thing that actually fills raw_qr.json.

    Watching that file is useless on its own -- something has to read the
    USB scanner and write it. Owning that here is what makes this one
    command instead of two, and means the scanner stops when this does.

    Its output is left on this terminal on purpose, so "Đã quét: ..."
    appears the moment a code is read and a silent scanner is obvious.

    Returns None if it could not start. That is not fatal: a scanner
    already running elsewhere holds the port exclusively, and its writes
    feed this loop just as well.
    """
    reap_orphan_scanners()

    command = [sys.executable, "-m", "scan.scanner"]
    print(f"[flow] Chạy máy quét: {' '.join(command)}", flush=True)

    process = subprocess.Popen(command, cwd=str(PROJECT_DIR))

    # Give it long enough to fail on a busy or missing port.
    time.sleep(SCANNER_START_SECONDS)

    if process.poll() is not None:
        print(
            f"[flow] Máy quét thoát ngay (mã {process.returncode}). "
            "Có thể một bản scanner khác đang giữ cổng -- vẫn tiếp tục "
            "theo dõi raw_qr.json.",
            file=sys.stderr, flush=True,
        )
        return None

    return process


@trace
def start_runner(
    recipe_path: Path,
    port: int,
    *,
    dry_run: bool,
    no_inventory: bool,
) -> subprocess.Popen:
    """Launch process_runner as its own process.

    A subprocess rather than an import: the runner owns pumps, the panel
    and the load cell, installs its own signal handling, and runs threads.
    Keeping it separate means a crash mid-pour cannot take this loop with
    it, and Ctrl+C reaches the runner directly.
    """
    # The recipe is positional, not a --recipe option.
    command = [
        sys.executable, "-m", "order.process_runner",
        str(recipe_path),
        "--serve", str(port),
    ]

    if dry_run:
        command.append("--dry-run")

    if no_inventory:
        command.append("--no-inventory")

    print(f"[flow] Chạy: {' '.join(command)}", flush=True)

    return subprocess.Popen(command, cwd=str(PROJECT_DIR))


@trace
def run_one_order(
    payload: str,
    *,
    raw_qr_path: Path,
    port: int,
    dry_run: bool,
    no_inventory: bool,
    force: bool,
    use_ticket: bool = True,
    no_qr: bool = False,
    watcher=None,
) -> int:
    """Carry one scanned code all the way to a finished drink.

    no_qr says the code was handed over by the store screen rather than
    scanned off a label. It changes exactly one thing: what the ticket is
    settled to when the drink does not happen.
    """
    log_event(f"=== Đơn mới: {payload}")

    # --- 2. code -> recipe, and the ticket is claimed here -----------------
    # Also off under --dry-run, whatever --no-ticket says. A rehearsal must
    # not spend a code a customer is holding: the pumps do not run, so they
    # would be left with a label that had already bought a drink nobody
    # poured.
    claiming = use_ticket and not dry_run

    # Any old refusal comes down now. Whatever happens next -- a drink or a
    # new refusal -- is about THIS scan, and leaving the previous one up
    # would have the customer reading someone else's error.
    clear_scan_notice(SCAN_NOTICE_FILE)

    try:
        document = process_payload(
            payload,
            output_path=CURRENT_RECIPE_FILE,
            dry_run=False,
            force=force,
            use_ticket=claiming,
        )
    except ScanError as error:
        # The digits did not survive the scan -- a bad CRC, a wrong length,
        # a stray character. Handled BEFORE its parent below because it is
        # a subclass and would otherwise be caught as an order refusal.
        #
        # Deliberately NOT recorded in error_log. Nothing is wrong with the
        # machine: a creased label or a scanner caught at an angle produces
        # this, and the answer is to scan again. Logging every misread as a
        # fault would bury the real ones.
        log_event(f"Quét lỗi (không ghi vào error_log): {error}")
        write_scan_notice(
            SCAN_NOTICE_FILE,
            "Không đọc được mã QR. Vui lòng quét lại.",
            payload,
            title="Lỗi khi quét mã",
            kind=NOTICE_KIND_RESCAN,
        )
        raise FlowError(str(error)) from error

    except OrderError as error:
        # The code WAS read correctly and is being refused: used, expired,
        # not from this machine, no such drink. Scanning it again will be
        # refused again, so this is a real event worth recording.
        write_scan_notice(SCAN_NOTICE_FILE, str(error), payload,
                          kind=NOTICE_KIND_REFUSED)
        # Hashed straight from the raw digits rather than read out of a
        # parsed order: this ran BECAUSE verification or claiming failed,
        # so there is no parsed order to ask, and unlike the old serial
        # field a payload's hash needs no decryption to compute. Without
        # it the log says a code was refused but not which one.
        # "Vé QR" in the sentence because error_log.category, which used
        # to carry that word, is gone -- and a refused ticket has to be
        # tellable from a hardware fault at a glance.
        record_error(f"Vé QR: {error}")
        raise FlowError(str(error)) from error

    ticket_key = document.get("ticket_key") if claiming else None

    # --- 3. start the machine and its screen -------------------------------
    # Guarded separately from the block below, which only begins once there
    # is a runner to wait on. A failure to start leaves the ticket claimed
    # with nothing that will ever settle it, so it is handed back here --
    # the customer's code is not spent on a machine that never moved.
    # Hand the button chip over before the runner is started, and take it
    # back in the finally below. panel_control/panel.py runs its own reader
    # inside process_runner for the length of the order; two readers on one
    # I2C bus is the fault that has already cost this machine whole orders.
    if watcher is not None:
        watcher.pause()

    try:
        runner = start_runner(
            CURRENT_RECIPE_FILE, port,
            dry_run=dry_run, no_inventory=no_inventory,
        )
    except Exception as error:
        if watcher is not None:
            watcher.resume()

        settle_ticket(ticket_key, poured=False, no_qr=no_qr)
        clear_order_files(None, raw_qr_path)
        message = f"Máy pha không khởi động được: {error}"
        # Still pre-handoff, so the store screen is what the customer is
        # looking at. Their ticket has just been handed back, and the
        # notice is the only thing that tells them to try again.
        write_scan_notice(SCAN_NOTICE_FILE, message, payload)
        # The exception's class name was in a `detail` blob; it is in the
        # sentence now, because that is the half of this entry that says
        # WHICH way the runner failed to start.
        #
        # Tagged with the ticket even though it has just been handed back
        # by settle_ticket() above: the row still exists and is still the
        # one the customer holds a label for, and "the machine would not
        # start for this ticket" is exactly what somebody looking at that
        # row later needs to find.
        record_error(
            f"{message} [{type(error).__name__}]",
            drink_id=document.get("drink_id"),
            drink_name=document.get("drink_name"),
            ticket_serial=document.get("ticket_serial"),
        )
        raise FlowError(message) from error

    # None until process_runner exits. The finally block below has to tell
    # "it exited non-zero" from "it never got that far" -- the second
    # happens on Ctrl+C and when the server never comes up, and reading an
    # unassigned name there would replace the real error with an
    # UnboundLocalError.
    code: int | None = None
    cancelled = False

    try:
        if dry_run:
            # process_runner suppresses its own screen under --dry-run
            # (it checks `serve is not None and not dry_run`), and its
            # gates pass without waiting, so there is nothing to hand the
            # browser over to. Waiting for a port that will never open
            # would just time out.
            print("[flow] --dry-run: không mở màn hình pha chế, "
                  "không chuyển màn hình bán hàng.", flush=True)
            code = runner.wait()
        else:
            wait_for_server(port, runner)

            # --- 4. only now is there something for the browser to go to --
            write_handoff(HANDOFF_FILE, document, port)
            print(f"[flow] Màn hình pha chế sẵn sàng trên cổng {port}; "
                  f"đã báo cho màn hình bán hàng chuyển sang.", flush=True)
            print("[flow] Máy đang chờ đặt ly...", flush=True)

            code = runner.wait()

            # The screen is counting down on the finished recipe; let it
            # finish before the file it is reading disappears. Skipped
            # under dry-run, where no screen was ever shown.
            # Only for a drink that finished. The wait exists so the
            # thank-you countdown is not cut off by the recipe being
            # cleared underneath it -- but a FAILED order keeps its recipe
            # anyway, and every second spent here is a second before the
            # store screen can tell the customer the machine has a
            # problem. Waiting to announce a fault helps nobody.
            if code == 0:
                # Before the wait, not after it: this wait IS the window
                # in which the store screen needs to know the drink is done.
                mark_handoff_finished(HANDOFF_FILE)
                print(f"[flow] Đợi {CLEAR_DELAY_SECONDS:g}s cho màn hình pha "
                      "chế hiển thị lời cảm ơn...", flush=True)
                time.sleep(CLEAR_DELAY_SECONDS)

        return code

    except KeyboardInterrupt:
        log_event("Dừng theo yêu cầu, đang đợi máy dừng...")
        # Told to the screen BEFORE the runner is killed. The bartender
        # screen reads the recipe through the runner's own server, so once
        # that process is gone there is no way left to reach it -- it would
        # sit on a half-poured drink until the 15s lost-contact timeout gave
        # up, and then blame the network for something a person did.
        announce_cancelled(CURRENT_RECIPE_FILE)
        runner.terminate()
        runner.wait()
        cancelled = True     # deliberate: nothing to investigate
        raise

    except FlowError as error:
        log_event(f"Đơn hỏng: {error}")
        runner.terminate()
        runner.wait()
        raise

    finally:
        poured = code == 0

        # Somebody pressed "Hủy đơn" on the bartender screen.
        # process_runner stamps that into the recipe; from out here a
        # cancelled order and a broken machine both look like a non-zero
        # exit code, and telling the customer "máy đang gặp sự cố" when a
        # member of staff simply stopped the order sends them to complain
        # about a fault that does not exist.
        finished = load_current_recipe(CURRENT_RECIPE_FILE)
        cancelled = cancelled or bool(finished.get("cancelled_at"))

        # A cancel is not a failure to investigate, but it is not a poured
        # drink either -- the customer gets their code back and the files
        # are cleared as if the order had never started.
        ended_cleanly = poured or cancelled

        log_event(
            f"Đơn {document.get('order_id')} kết thúc, "
            f"process_runner thoát với mã "
            f"{'(chưa chạy)' if code is None else code}."
        )

        # --- 5. the order is over, however it ended ----------------------
        # In the finally rather than on the success path, so a cancelled
        # order does not leave a half-finished recipe for the next one.
        clear_handoff(HANDOFF_FILE)
        settle_ticket(ticket_key, poured=poured, no_qr=no_qr)

        # The runner has exited, so the panel is ours again. Before the
        # watcher starts reading it, put the hardware back to rest: a
        # runner that was killed rather than finished leaves its LEDs lit
        # and, if it died mid-pour, a pump running.
        reset_machine_hardware("đơn kết thúc")

        if watcher is not None:
            watcher.resume()

        if poured:
            clear_order_files(CURRENT_RECIPE_FILE, raw_qr_path)
        elif cancelled:
            # Nothing to investigate, so the recipe goes like a finished
            # one -- but the customer still arrives at the store screen
            # needing to know why their drink stopped, and it was not a
            # fault.
            clear_order_files(CURRENT_RECIPE_FILE, raw_qr_path)

            drink = str(finished.get("drink_name") or "Đơn này")
            write_scan_notice(
                SCAN_NOTICE_FILE,
                f"{drink} đã bị hủy. Vui lòng đặt lại đơn mới.",
                "",
                title="Đơn đã bị hủy",
                kind=NOTICE_KIND_FAULT,
            )
        else:
            # An order that FAILED is the one case worth keeping. The
            # recipe records which step stopped and the error the runner
            # wrote into it, and that is the only account of what went
            # wrong once the runner's own output has scrolled away.
            # raw_qr.json still goes, so the next scan is not blocked.
            clear_order_files(None, raw_qr_path)

            # Said again on the store screen, because that is where the
            # browser goes next and the bartender screen's card goes with
            # it. A customer who walked away from a broken machine and came
            # back to a normal menu would have no idea anything was wrong,
            # and would order again into the same fault.
            reason = str(load_current_recipe(CURRENT_RECIPE_FILE).get("error")
                         or "").strip()
            write_scan_notice(
                SCAN_NOTICE_FILE,
                "Máy đang gặp sự cố nên chưa pha xong đồ uống. "
                "Vui lòng liên hệ quản trị viên."
                + (f"\n\nChi tiết: {reason}" if reason else ""),
                "",
                title="Máy đang gặp sự cố",
                kind=NOTICE_KIND_FAULT,
            )

            print(
                f"[flow] Đơn KHÔNG hoàn tất. Giữ lại "
                f"{CURRENT_RECIPE_FILE.name} de xem loi:\n"
                f"[flow]   {CURRENT_RECIPE_FILE}",
                file=sys.stderr, flush=True,
            )


@trace
def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a shell-friendly exit code."""
    parser = argparse.ArgumentParser(
        description="Chạy trọn vẹn một đơn: quét mã -> pha -> xong.",
    )
    parser.add_argument(
        "--raw-qr", type=Path, default=RAW_QR_FILE,
        help=f"File mã đã quét (mặc định {RAW_QR_FILE}).",
    )
    parser.add_argument(
        "--port", type=int, default=GUI_PORT,
        help=f"Cổng của màn hình pha chế (mặc định {GUI_PORT}).",
    )
    parser.add_argument(
        "--payload",
        help="Dùng mã này ngay, bỏ qua việc chờ máy quét.",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Chỉ chạy một đơn rồi thoát.",
    )
    parser.add_argument(
        "--no-scanner", action="store_true",
        help="Đừng tự chạy máy quét (khi đã chạy scan.scanner riêng).",
    )
    parser.add_argument(
        "--wait", action="store_true",
        help=(
            "Nếu đã có flow khác đang chạy thì chờ đến lượt, thay vì thoát."
        ),
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Diễn tập: không chạy bơm, không trừ kho.",
    )
    parser.add_argument(
        "--no-inventory", action="store_true",
        help="Không trừ nguyên liệu khỏi database.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Ghi đè công thức kể cả khi đơn cũ đang chạy dở.",
    )
    parser.add_argument(
        "--test-port", type=int, default=button_watch.DEFAULT_TEST_PORT,
        help=f"Cổng của màn hình test tay "
             f"(mặc định {button_watch.DEFAULT_TEST_PORT}).",
    )
    parser.add_argument(
        "--no-test-gui", action="store_true",
        help="Không mở màn hình test tay trong tiến trình này.",
    )
    parser.add_argument(
        "--no-ticket", action="store_true",
        help="Bỏ qua vé QR dùng một lần. Chỉ dùng để thử máy.",
    )
    args = parser.parse_args(argv)

    # One flow at a time. Taken before the port check so the message is
    # about the flow, not about a port another flow happens to be using.
    lock, holder = acquire_single_instance_lock(LOCK_FILE, wait=args.wait)

    if lock is None:
        print(
            f"LỖI: đã có một flow khác đang chạy (PID {holder}). "
            "Đợi nó xong, hoặc chạy lại với --wait để tự xếp hàng.",
            file=sys.stderr,
        )
        return 1

    if args.wait:
        print(f"[flow] Đã giành được quyền chạy (PID {holder}).", flush=True)

    if port_is_open(args.port):
        print(
            f"LỖI: cổng {args.port} đã có tiến trình khác chiếm. "
            "Đóng process_runner đang chạy rồi thử lại.",
            file=sys.stderr,
        )
        return 1

    # Whether an order is really in progress is answered by the port check
    # above, not by this file: "status": "running" only means a runner was
    # running when it last wrote, which stays true forever if that runner
    # was killed. Nothing is listening, so nothing is pouring, and a status
    # left over from a cancelled order is a ghost. Say so and carry on
    # rather than refusing to start.
    busy = busy_steps(load_current_recipe(CURRENT_RECIPE_FILE))

    if busy:
        print(
            f"[flow] {CURRENT_RECIPE_FILE.name} còn trạng thái đang chạy "
            f"(bước {', '.join(busy)}) từ một đơn đã dừng. Không có máy nào "
            f"phục vụ trên cổng {args.port}, nên bỏ qua đơn đó.",
            flush=True,
        )

    # --- recover what the last run left behind -----------------------------
    # Two things outlive a flow that died badly, and both stop the next
    # customer being served. This is the only moment they can be judged: the
    # single-instance lock is held and the runner's port is free, so nothing
    # is pouring and nothing else is about to.
    #
    # 1. A ticket stuck in_progress. Its order will never finish and never
    #    settle it, so the customer's code is refused for a drink nobody is
    #    making. It goes back to unused and the label works again -- see
    #    release_stranded() for why that is the safer of the two mistakes
    #    available to something that cannot know how the order started.
    if not args.no_ticket:
        release_stranded_tickets()

    # 2. The ghost recipe above. Saying "bỏ qua đơn đó" was not enough --
    #    process_payload checks the same file again and refused the first
    #    scan with "đang chạy dở", which is how a dead order used to block
    #    the machine until somebody deleted the file by hand. Forcing past
    #    it keeps the failed recipe readable until the next order replaces
    #    it, which is what it was kept for.
    stale_recipe = bool(busy)

    clear_handoff(HANDOFF_FILE)
    # A refusal from a previous run of this script is not this run's news.
    # Nor is a restart notice: it is read on the way DOWN, and carrying it
    # over meant the store screen came back to a popup about something
    # that had already finished happening.
    clear_scan_notice(SCAN_NOTICE_FILE)

    # Test mode is a state somebody is standing at the machine holding, not
    # a setting. A flag left over from a previous run means that run ended
    # without unwinding -- a power cut, a SIGTERM from systemd, a kill --
    # and honouring it would bring the machine up refusing every order with
    # no visible cause. Starting up IS being put back into service.
    if button_watch.is_open():
        log_event("Xoá chế độ test còn sót từ lần chạy trước.")
        button_watch.write_mode(False, args.test_port)
    seen = read_scan(args.raw_qr)
    orders = 0

    scanner = None if args.no_scanner else start_scanner()

    # Panel button 15, watched from here rather than from the test screen's
    # server: this is the process that is always up on a machine in
    # service, and the one that knows when a drink is being poured. Under
    # --dry-run there is no panel to read.
    watcher = None

    if not args.dry_run and not args.no_test_gui:
        # Served by store_gui/serve.py on the one public port, so the
        # address printed here is that port's, not a second one.
        if warm_test_gui():
            print("[flow] Màn hình test tay: "
                  f"http://<máy này>:{store_port()}/test_gui/index.html",
                  flush=True)

    # Whatever ended the last run -- a restart, a crash, the power -- this
    # process is the first thing up, and nothing else will tidy what it
    # left. Done before the watcher opens the button chip, so the two are
    # never on the bus at once.
    if not args.dry_run:
        reset_machine_hardware("khởi động")

    if not args.dry_run:
        watcher = button_watch.ButtonWatcher(
            port=args.test_port,
            on_restart=warn_store_screen_of_restart,
        )
        watcher.start()
        print(f"[flow] Nút bảng {button_watch.TOGGLE_PANEL_ID} bật/tắt chế "
              f"độ test; nút {button_watch.RESTART_PANEL_ID} khởi động lại "
              f"{button_watch.SERVICE_NAME}.", flush=True)

        # If this process exists because somebody pressed button 14, the
        # kiosk browser is still showing the page it had when the previous
        # backend died. Nothing else brings it back -- see the KIOSK
        # REFRESH note in panel_control/button_watch.py. Does nothing on an
        # ordinary boot.
        button_watch.refresh_kiosk_if_requested()

    try:
        while True:
            # Panel button 15 puts the machine into test mode. Held HERE,
            # before a scan is taken, so an order is never started on top of
            # someone priming a pump by hand -- and so a customer's scan is
            # not consumed and thrown away while the machine is out of
            # service. They can scan again when it comes back.
            wait_while_test_mode()

            if args.payload and orders == 0:
                payload = args.payload
                # --payload is a developer's shortcut, not the store
                # screen's button. Treated as a scan, so a code passed in
                # by hand comes back to 'unused' the way scanning it would.
                no_qr = False
            else:
                seen = wait_for_new_scan(args.raw_qr, seen)
                payload = seen[0]
                no_qr = scan_source(args.raw_qr) == SOURCE_STORE_SCREEN

                if no_qr:
                    log_event("Đơn chạy từ màn hình bán, không quét mã QR.")

            # Checked again: the button may have been pressed while this
            # was blocked waiting for a scan.
            if test_mode_open():
                log_event("Máy đang ở chế độ test, bỏ qua mã vừa quét.")
                wait_while_test_mode()
                seen = read_scan(args.raw_qr)
                continue

            try:
                code = run_one_order(
                    payload,
                    raw_qr_path=args.raw_qr,
                    port=args.port,
                    dry_run=args.dry_run,
                    no_inventory=args.no_inventory,
                    force=args.force or orders > 0 or stale_recipe,
                    use_ticket=not args.no_ticket,
                    no_qr=no_qr,
                    watcher=watcher,
                )
                print(f"[flow] Đơn xong (mã thoát {code}).", flush=True)
                # raw_qr.json was just emptied, so the next scan of any
                # code -- including the same drink again -- reads as new.
                seen = None
            except FlowError as error:
                print(f"[flow] LỖI: {error}", file=sys.stderr, flush=True)

                if args.once:
                    return 1

            orders += 1

            if args.once:
                return 0

    except KeyboardInterrupt:
        print("\n[flow] Đã dừng.", flush=True)
        return 0

    finally:
        clear_handoff(HANDOFF_FILE)

        if watcher is not None:
            # Also clears the flag, so the store screen is not left pointing
            # at a test screen and the next run does not start up paused.
            watcher.stop()


        if scanner is not None and scanner.poll() is None:
            scanner.terminate()
            scanner.wait()
            print("[flow] Đã dừng máy quét.", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
