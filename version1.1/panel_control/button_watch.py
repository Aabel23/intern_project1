"""Watch the panel's two service buttons while the machine is idle.

WHAT THIS IS
    A thread that reads the button chip while the machine is idle.

    Button 15 puts the machine into test mode; pressing it again takes it
    back out. The state lives in one small file that everything else
    reads.

    Button 14 restarts flexmix-backend.service -- the recovery anyone
    standing at the machine can reach without a keyboard or an SSH
    session. See RESTART_COMMAND for the sudoers rule it wants, and
    restart_backend() for what it does when that rule is missing.

    Button 14 is the one button that must also work while an order is
    open, because a stalled order is what people reach for it over. This
    thread cannot see it then -- see below -- so the panel reader inside
    process_runner answers it instead, through the same restart_backend()
    (panel_control/panel.py, order/process_runner.py's
    restart_backend_if_idle). Button 15 stays idle-only.

WHO OWNS IT
    order/run_flow.py, because that is the process that is always up on a
    machine in service, and because it is the process that STARTS the
    runner -- so it knows precisely when a drink is being poured and can
    stand this thread down for exactly that window.

    An earlier version had test_gui/serve.py own it, which meant button 15
    only worked if a second service happened to be running, and that
    service had to guess at whether an order was in progress by probing a
    port. Ownership belongs where the knowledge is.

WHY IT MUST STAND DOWN WHILE A DRINK IS POURED
    panel_control/panel.py runs its own reader inside process_runner and
    owns the button chip for the length of the order. Two readers on one
    I2C bus corrupt each other -- this machine has already lost whole
    orders to that. So run_flow pauses this thread before it starts the
    runner and resumes it after.

WHAT TEST MODE MEANS
    run_flow stops taking scans: a customer's code is left unread rather
    than consumed and thrown away, and no order can start on top of
    somebody priming a pump by hand. The test screen becomes usable, and
    the store screen jumps to it.

WHY A FILE
    A Python thread cannot navigate a browser, and the browser may be a
    tablet across the room. The pages poll this file and move themselves,
    exactly as they already do for order/handoff.json.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from configuration import machine


PROJECT_DIR = Path(__file__).resolve().parent.parent

# Read by store_gui/drinks-pos.js and test_gui/app.js. It lives beside the
# test screen because that is what it controls.
MODE_FILE = PROJECT_DIR / "test_gui" / "mode.json"

# Which panel position toggles test mode.
TOGGLE_PANEL_ID = machine.PANEL_BUTTON_TEST_MODE

# Which panel position restarts the backend service.
#
# 14 is free. An order's manual buttons come from the DATABASE -- a MANUAL
# ingredient's panel position is its ingredient.gpio, see
# database/export_data.py -- and those occupy 1 to 6 (Milk, Cream,
# Chocolate, Strawberry, Ice, Pearls). 15 is the test-mode toggle above.
# 0 and 7 to 13 are unassigned.
#
# Do NOT read bartender_gui/config/gui_config.json for this: its
# panel_buttons roster claims 11 to 15 and puts a "cup check" on 14. That
# file feeds gui_config.build_recipe(), a path real orders do not use, and
# it disagrees with the database. If it is ever wired up, move this button
# or fix that roster -- they cannot both own 14.
RESTART_PANEL_ID = machine.PANEL_BUTTON_RESTART

SERVICE_NAME = "flexmix-backend.service"

# -n so a machine without the sudoers rule below fails immediately instead
# of blocking this thread on a password prompt nobody can answer -- there
# is no terminal attached to a service.
#
# --no-block because this service is the one being restarted: systemctl
# would otherwise wait for a job whose first act is to kill the process
# waiting on it. The job is queued with systemd either way.
#
# ONLY REACHED WHEN NOT RUNNING UNDER systemd. Inside the unit, sudo cannot
# work at all -- CapabilityBoundingSet=CAP_SYS_NICE stops it becoming root --
# so restart_backend() skips it there and signals instead. See the comment
# in that function.
#
# For a hand-started main.py, root must allow it without a password:
#
#   echo 'flexxource ALL=(root) NOPASSWD: /usr/bin/systemctl restart --no-block flexmix-backend.service' \
#     | sudo tee /etc/sudoers.d/flexmix-restart
#   sudo chmod 440 /etc/sudoers.d/flexmix-restart
RESTART_COMMAND = (
    "sudo",
    "-n",
    "systemctl",
    "restart",
    "--no-block",
    SERVICE_NAME,
)

# --no-block returns as soon as the job is queued, so this only has to
# cover sudo itself deciding whether it is allowed.
RESTART_TIMEOUT_SECONDS = 10.0

# The port the test screen is served on, written into the file so the store
# screen knows where to send the browser.
# The one port everything is served from -- the test screen included. It
# used to be 8090, a second server of its own; a page sent there now would
# be sent to nothing. Kept as a number rather than imported from
# store_gui.serve so this module stays importable with no web stack.
DEFAULT_TEST_PORT = machine.STORE_PORT

# ---------------------------------------------------------------------------
# KIOSK REFRESH — the other half of what button 14 does
#
# Restarting the backend leaves the kiosk browser parked on whatever it had
# when its connection died. Usually that is a page whose CSS never arrived,
# so every dialog renders unstyled and stacked down the screen. Chromium
# does not exit, so nothing brings it back on its own.
#
# WHY THIS IS NOT DONE BY THE PROCESS THAT ASKED FOR THE RESTART
#   It cannot be. The unit has no KillMode, so systemd's default
#   control-group applies and every process in the cgroup is killed --
#   a detached child with start_new_session included. Anything this
#   process spawns dies with it.
#
#   So the dying process only leaves a marker, and the process systemd
#   starts in its place picks it up. That also removes the guesswork: the
#   new backend knows when it is actually serving, instead of a sleep
#   long enough to probably cover it.
#
# WHY CHROMIUM IS NOT KILLED FIRST, BEFORE THE RESTART
#   deploy/kiosk/kiosk-openbox-autostart.sh waits for the server exactly
#   once, before its respawn loop. Inside the loop it restarts Chromium
#   after one second with no wait at all -- so a browser killed while the
#   backend is down comes back to a connection error and stays there.
# ---------------------------------------------------------------------------

# Left by the process being restarted, read by the one that replaces it.
KIOSK_REFRESH_MARKER = PROJECT_DIR / "order" / ".kiosk_refresh"

# The page the kiosk sits on all day, and the readiness test the kiosk
# script itself uses -- same URL, so "up" means the same thing to both.
KIOSK_URL = f"http://localhost:{DEFAULT_TEST_PORT}/store_gui/drinks-pos.html"
KIOSK_CSS_URL = f"http://localhost:{DEFAULT_TEST_PORT}/store_gui/drinks-pos.css"

# What tells the kiosk's Chromium apart from any other browser on the box.
KIOSK_PROCESS_PATTERN = "chromium-browser/chrome --password-store"

# How long to wait for the new backend to answer before giving up. Longer
# than RestartSec plus the time main.py takes to bind, and short enough
# that a machine which is not coming back says so instead of hanging.
KIOSK_SERVER_WAIT_SECONDS = 90.0

# How long the kiosk script needs to notice Chromium is gone and start it
# again -- its loop sleeps 1s, Chromium itself takes a few more.
KIOSK_RESPAWN_SECONDS = 10

# A button press is held for a good fraction of a second, so this catches
# one comfortably. Deliberately slower than panel.py's 20 Hz: that runs for
# the length of one order, this runs all day, and every poll is traffic on
# a bus that has already proved fragile on this machine.
POLL_SECONDS = 0.25

# After an I2C error, wait before trying again rather than hammering a bus
# that is already unhappy.
ERROR_BACKOFF_SECONDS = 3.0

# A press shorter than this is contact bounce, not a second press.
DEBOUNCE_SECONDS = 0.35


def read_mode() -> dict[str, Any]:
    """What state the machine has been put in. {} if never set."""
    try:
        with open(MODE_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def is_open() -> bool:
    """Is the machine in test mode?

    A missing or unreadable file means no -- so a maintenance screen that
    was never started, or a folder that got cleaned out, can never take the
    shop out of service by failing.
    """
    return bool(read_mode().get("open"))


def write_mode(open_now: bool, port: int = DEFAULT_TEST_PORT) -> dict[str, Any]:
    """Record the state, atomically.

    `id` changes on every flip, which is what lets a page tell a new
    instruction from one it has already obeyed. Without it, reloading a
    page would make it jump again.
    """
    state = {
        "open": bool(open_now),
        "id": uuid.uuid4().hex,
        "port": int(port),
        "path": "/test_gui/index.html",
        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    temporary = MODE_FILE.with_name(f".{MODE_FILE.name}.tmp")

    try:
        MODE_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temporary, MODE_FILE)
    except OSError as error:
        print(f"[watch] không ghi được {MODE_FILE.name}: {error}")

    return state


# --------------------------------------------------------- restarting ----

def request_kiosk_refresh() -> None:
    """Leave a note asking the next backend to reload the kiosk browser.

    Best effort: a machine that cannot write this file still restarts, it
    just comes back with whatever the browser was showing. The restart is
    the part that matters.
    """
    try:
        KIOSK_REFRESH_MARKER.parent.mkdir(parents=True, exist_ok=True)
        KIOSK_REFRESH_MARKER.write_text(str(time.time()), encoding="utf-8")
    except OSError as error:
        print(f"[kiosk] không ghi được {KIOSK_REFRESH_MARKER.name}: {error}",
              flush=True)


def _server_is_up() -> bool:
    """Does the store screen actually answer yet?

    The same question the kiosk script asks, so both agree on what "up"
    means. A port that is merely open is not enough: main.py binds before
    every thread behind it is serving.
    """
    try:
        with urllib.request.urlopen(KIOSK_URL, timeout=2) as response:
            return response.status == 200
    except Exception:      # noqa: BLE001 - not up yet is the normal answer
        return False


def _refresh_kiosk_now() -> None:
    """Wait for this backend to be serving, then restart the browser on it."""
    deadline = time.monotonic() + KIOSK_SERVER_WAIT_SECONDS

    while time.monotonic() < deadline:
        if _server_is_up():
            break

        time.sleep(1.0)
    else:
        print(f"[kiosk] máy chủ chưa trả lời sau "
              f"{KIOSK_SERVER_WAIT_SECONDS:.0f}s — không làm mới trình duyệt.",
              flush=True)
        return

    # Killing it is the whole refresh: the kiosk autostart loop starts a
    # new Chromium a second later, and a new Chromium fetches the page,
    # the CSS and the menu again from a backend that is now up.
    script = (
        f"pkill -f '{KIOSK_PROCESS_PATTERN}' 2>/dev/null;"
        f" sleep {KIOSK_RESPAWN_SECONDS};"
        f" echo \"url: $(pgrep -af 'chrome --password-store'"
        f" | head -1 | grep -o 'http.*')\";"
        f" echo \"busybar html: $(curl -s {KIOSK_URL} | grep -c busybar)\";"
        f" echo \"busybar css: $(curl -s {KIOSK_CSS_URL} | grep -c busybar)\""
    )

    try:
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=KIOSK_RESPAWN_SECONDS + 30,
        )
    except (OSError, subprocess.SubprocessError) as error:
        print(f"[kiosk] không làm mới được trình duyệt: {error}", flush=True)
        return

    for line in (result.stdout or "").splitlines():
        if line.strip():
            print(f"[kiosk] {line.strip()}", flush=True)

    detail = (result.stderr or "").strip()

    if detail:
        print(f"[kiosk] {detail}", flush=True)


def refresh_kiosk_if_requested() -> None:
    """Called once at startup. Does nothing unless button 14 asked.

    The marker is removed BEFORE the work, not after: a refresh that fails
    halfway must not queue itself up to run again on every later start.
    """
    try:
        if not KIOSK_REFRESH_MARKER.exists():
            return

        KIOSK_REFRESH_MARKER.unlink()
    except OSError:
        return

    print("[kiosk] khởi động lại theo nút bảng — sẽ làm mới trình duyệt "
          "khi máy chủ sẵn sàng.", flush=True)

    threading.Thread(target=_refresh_kiosk_now,
                     name="kiosk-refresh", daemon=True).start()


def restart_backend(source: str = "") -> None:
    """Restart the backend service. Safe to call from any of its processes.

    This runs INSIDE the service being restarted, which is the point: the
    button exists for a machine that has stopped being useful, and the
    person standing at it should not need a keyboard, a screen or an SSH
    session to bring it back.

    Two callers, one action: the idle watcher below, and the panel reader
    inside process_runner (panel_control/panel.py), which owns the button
    chip while an order is open. Whoever sees the press asks for the same
    restart.
    """
    label = f"[watch] {source}: " if source else "[watch] "
    print(f"{label}khởi động lại {SERVICE_NAME}...", flush=True)

    # Written before the restart is asked for, because after it there is no
    # "after": systemd stops this process as soon as it has the job.
    request_kiosk_refresh()

    # Under systemd, go straight to the signal: sudo CANNOT work from inside
    # this unit, no matter what the sudoers rule says.
    #
    # flexmix-backend.service sets CapabilityBoundingSet=CAP_SYS_NICE, which
    # caps what any process in the unit may ever hold. sudo is setuid-root
    # and needs CAP_SETUID/CAP_SETGID to become root, so it fails at the
    # first step with "unable to change to root gid: Operation not
    # permitted" -- observed on this machine on 2026-09-08.
    #
    # Widening the bounding set to fix that would trade a real hardening
    # (see the unit's own comment: CAP_SYS_NICE is there so the load-cell
    # thread can hit SCHED_FIFO for ~0.3ms, and nothing more) for a path
    # that gains nothing -- _restart_by_signal() already produces the same
    # restart, needs no privilege at all, and is what actually ran every
    # time the button was pressed. So the sudo attempt is skipped rather
    # than repaired: it only ever added a ten-second timeout and two lines
    # of alarming log to a restart that was going to work anyway.
    if os.environ.get("INVOCATION_ID"):
        _restart_by_signal()
        return

    # Not under systemd -- somebody is running main.py by hand. The signal
    # path deliberately refuses that case (ending their process leaves
    # nothing to bring it back), so sudo is the only thing left to try.
    try:
        result = subprocess.run(
            RESTART_COMMAND,
            capture_output=True,
            text=True,
            timeout=RESTART_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as error:
        print(f"[watch] không chạy được systemctl: {error}", flush=True)
    else:
        if result.returncode == 0:
            # systemd has the job; it stops this process next.
            return

        detail = (result.stderr or result.stdout or "").strip()
        print(f"[watch] systemctl trả về {result.returncode}"
              + (f": {detail}" if detail else ""), flush=True)

    _restart_by_signal()


def _restart_by_signal() -> None:
    """Restart without sudo, by ending the process systemd is watching.

    The unit is Restart=always with RestartSec=3, so the service comes
    straight back -- the same restart the button asked for, minus the
    permission. It means the button works on a machine where the sudoers
    rule was never installed.

    The signal goes to the unit's MainPID, not to us: the press may have
    been read by process_runner, a child, and killing a child only ends
    the order. Reading MainPID needs no privilege, and neither does
    signalling a process this user already owns.

    Only under systemd. INVOCATION_ID is set for every process systemd
    starts, and absent when somebody is running main.py by hand in a
    terminal: ending it there would kill their machine with nothing to
    bring it back, which is not what the button promises.
    """
    if not os.environ.get("INVOCATION_ID"):
        print("[watch] không chạy dưới systemd -- bỏ qua lệnh khởi động "
              "lại. Xem hướng dẫn sudoers trong "
              "panel_control/button_watch.py.", flush=True)
        return

    main_pid = _service_main_pid()

    if main_pid is None:
        print("[watch] không tìm được MainPID của service.", flush=True)
        return

    print(f"[watch] kết thúc PID {main_pid} để systemd "
          f"(Restart=always) bật lại sau vài giây.", flush=True)

    if main_pid == os.getpid():
        # _exit, not sys.exit: this runs in a worker thread, where an
        # exception would be swallowed by the thread's own error handling
        # and leave the machine up as though nothing had been pressed.
        os._exit(1)

    try:
        os.kill(main_pid, signal.SIGTERM)
    except OSError as error:
        print(f"[watch] không gửi được SIGTERM tới {main_pid}: {error}",
              flush=True)


def _service_main_pid() -> int | None:
    """The PID systemd is watching for this unit, or None."""
    try:
        result = subprocess.run(
            ("systemctl", "show", "-p", "MainPID", "--value", SERVICE_NAME),
            capture_output=True,
            text=True,
            timeout=RESTART_TIMEOUT_SECONDS,
        )
        pid = int((result.stdout or "0").strip() or 0)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None

    return pid or None


# The watcher currently running, if any. Registered so that anything else
# needing the button chip -- the panel test on the maintenance screen --
# can borrow it for the duration without having to be handed a reference
# through three layers of call.
_active: "ButtonWatcher | None" = None


def pause_active() -> bool:
    """Hand the button chip to somebody else. True if there was a watcher."""
    if _active is None:
        return False

    _active.pause()
    return True


def resume_active() -> None:
    """Take the chip back."""
    if _active is not None:
        _active.resume()


class ButtonWatcher:
    """Polls the panel button in a thread. Pause it while pouring.

    pause() and resume() rather than stop() and start() because the I2C
    device is opened and closed around the pause: leaving it open while
    process_runner uses the same chip is the thing being avoided.
    """

    def __init__(self, port: int = DEFAULT_TEST_PORT,
                 on_change=None, on_restart=None) -> None:
        self.port = port
        self.on_change = on_change
        # Called just before the machine goes down, so whoever owns a
        # screen can warn the person in front of it. run_flow supplies
        # one; see warn_store_screen_of_restart there.
        self.on_restart = on_restart
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._thread: threading.Thread | None = None

    # --- lifecycle ------------------------------------------------------
    def start(self) -> None:
        global _active

        if self._thread is not None and self._thread.is_alive():
            return

        _active = self
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop,
                                        name="button-watch", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop watching and put the machine back into service.

        Clearing the flag matters: a run_flow that exits while test mode is
        on would otherwise leave the store screen pointing at a test screen
        nobody is serving, and the next run_flow would start up paused.
        """
        global _active

        self._stop.set()

        if _active is self:
            _active = None

        if self._thread is not None:
            self._thread.join(timeout=2.0)

        if is_open():
            write_mode(False, self.port)

    def pause(self) -> None:
        """Release the chip. Called before process_runner is started."""
        self._paused.set()

    def resume(self) -> None:
        """Take the chip back, once the order is over."""
        self._paused.clear()

    # --- the loop -------------------------------------------------------
    def _loop(self) -> None:
        from panel_control.panel import (
            ADDR_BUTTON, ALL_HIGH, I2C_BUS, PANEL_COUNT, PCF8575,
            button_pin_to_panel_id,
        )

        device = None

        # What each watched button does. Everything else on the panel
        # belongs to an order, and an order owns the chip through
        # panel_control/panel.py while this thread is paused.
        actions = {
            TOGGLE_PANEL_ID: self._toggle,
            RESTART_PANEL_ID: self._restart_backend,
        }

        was_pressed: set[int] = set()
        last_press: dict[int, float] = {}

        while not self._stop.is_set():
            if self._paused.is_set():
                device = self._close(device)
                self._stop.wait(0.5)
                continue

            try:
                if device is None:
                    device = PCF8575(I2C_BUS, ADDR_BUTTON)
                    device.write_all(ALL_HIGH)      # release the inputs

                state = device.read_all()

                # Active low: a 0 bit is a pressed button.
                pressed = {
                    button_pin_to_panel_id(bit)
                    for bit in range(PANEL_COUNT)
                    if not state & (1 << bit)
                } & actions.keys()

                now = time.monotonic()

                # The rising edge only, so holding a button does not fire
                # repeatedly and a bouncing contact counts once.
                for panel_id in sorted(pressed - was_pressed):
                    if now - last_press.get(panel_id, 0.0) <= DEBOUNCE_SECONDS:
                        continue

                    last_press[panel_id] = now
                    actions[panel_id]()

                was_pressed = pressed
            except Exception as error:      # noqa: BLE001 - the bus, usually
                print(f"[watch] lỗi đọc bảng nút: {error}", flush=True)
                device = self._close(device)
                self._stop.wait(ERROR_BACKOFF_SECONDS)
                continue

            self._stop.wait(POLL_SECONDS)

        self._close(device)

    def _toggle(self) -> None:
        state = write_mode(not is_open(), self.port)
        opened = state["open"]

        print(f"[watch] nút {TOGGLE_PANEL_ID}: "
              f"{'BẬT' if opened else 'TẮT'} chế độ test.", flush=True)

        if self.on_change is not None:
            try:
                self.on_change(opened)
            except Exception:      # noqa: BLE001 - a notice, not a gate
                pass

    def _restart_backend(self) -> None:
        """Panel 14, pressed while the machine is idle.

        Idle means the customer is looking at the STORE screen -- there is
        no order, so there is no bartender screen. The warning has to go
        there, and only the owner of that screen knows how to put it up,
        so it arrives as a callback rather than being done here.
        """
        if self.on_restart is not None:
            try:
                self.on_restart()
            except Exception as error:      # noqa: BLE001 - a notice, not a gate
                print(f"[watch] không báo được màn hình bán hàng: {error}",
                      flush=True)

        restart_backend(f"nút {RESTART_PANEL_ID}")

    @staticmethod
    def _close(device):
        if device is not None:
            try:
                device.close()
            except Exception:      # noqa: BLE001
                pass
        return None
