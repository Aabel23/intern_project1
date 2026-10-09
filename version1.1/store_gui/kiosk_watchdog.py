"""Keep the kiosk screen alive through a graphics-stack leak we cannot fix.

WHAT GOES WRONG
    Something in Chromium drains this Pi's entire 320 MB CMA pool -- the
    contiguous memory the graphics stack allocates buffers from. CmaFree
    sits flat at ~300 MB for a quarter of an hour, then falls to zero in
    about a hundred seconds, and the renderer dies the moment a raster
    tile (1920x320, 2.4 MB contiguous) cannot be allocated. What the
    screen shows is "Aw, Snap! Error code: SIGTRAP".

    Measured 2026-09-01: 99 crashes in 29 hours, every one 1040 seconds
    after the last, day and night, with no customers and no orders.

NOT THIS PROJECT'S FAULT, AND NOT FIXABLE HERE
    A page holding nothing but a line of text and a one-second poll --
    no images, no animation, no clock, no menu grid -- drained the pool
    exactly the same way. So it is not the store page's rendering.

    Nor is it the GPU path: --disable-gpu was tried and the crash arrived
    on schedule with the identical signature. (--use-angle=gles-egl does
    remove three real GL initialisation errors, and is worth keeping for
    that, but it does not stop this.)

    The one useful thing that page proved: at zero CMA it kept running.
    Exhaustion alone does not kill a browser -- it kills whoever next
    asks for a big contiguous buffer, which the store page does and a
    line of text does not.

SO THIS MODULE GETS OUT OF THE WAY INSTEAD
    Two checks, in this order:

    1.  PROACTIVE. CmaFree is readable, and the drain is steep but not
        instant. Restarting on the way down costs a three-second reload
        at a moment of our choosing.

    2.  REACTIVE. If the wall is hit anyway, the BROWSER survives -- only
        the tab dies -- so the `while true` loop in
        deploy/kiosk/kiosk-openbox-autostart.sh never fires, because it
        only reopens Chromium when Chromium EXITS. The sad tab would
        otherwise stay up until somebody walked past, which is why the
        fault always looked like "it broke while nobody was using it".

    The second is the net under the first, and under whatever else a
    browser can die of that nobody has thought about yet.

HOW IT KNOWS
    Both screens poll this server constantly and neither one needs a
    customer to do it -- the store page every second (order/handoff.json,
    order/scan_notice.json, test_gui/mode.json), the bartender screen
    every 120ms while a drink pours. So traffic never stops on its own
    while a page is alive, and a long silence means no page is running.

    That is the whole signal, and it is why the check is safe: if nothing
    has asked this server for anything in three quarters of a minute,
    there is nobody mid-order to interrupt.

WHY IT CANNOT FIRE BY ACCIDENT
    Three guards, all of which must hold:

      * it has to have seen traffic at least once, so it does nothing on
        a machine where the kiosk was never started;
      * a Chromium whose command line carries the kiosk page has to be
        running right now, so it does nothing on a developer's machine
        and nothing while the browser is already restarting;
      * after acting it waits out a cooldown, so a browser that takes a
        few seconds to come up is not killed again on the way.

OPT-IN, NOT OPT-OUT
    It does nothing unless FLEXMIX_KIOSK_WATCHDOG=1 is set, and the only
    thing that sets it is deploy/kiosk/flexmix-backend.service -- the one
    server the kiosk is actually pointed at.

    That is not caution for its own sake. The guards below ask "is a
    kiosk browser running?", which is true for EVERY process on this
    machine, including a developer's `python3 -m store_gui.serve --port
    8123` on the side. Left opt-out, that second server would sit there,
    notice that nobody was talking to IT, and shut down the real kiosk's
    browser -- which is exactly what happened the first time this was
    tested. Defaulting off makes that impossible instead of unlikely.
"""

from __future__ import annotations

import os
import signal
import sys
import threading
import time


# The page whose presence in a command line identifies the kiosk browser.
# Only the top-level process carries the URL in either browser -- Chromium's
# renderers and GPU process do not, and Firefox's -contentproc children and
# crashhelper do not -- so this matches the one process worth killing.
KIOSK_URL_MARK = "store_gui/drinks-pos.html"

# ...and the process's own EXECUTABLE has to be one of these. Not a
# substring of the command line: a shell whose command line merely
# mentions both the page and a browser name matches that, and during
# testing this function duly offered up the shell it was being run from.
# /proc/<pid>/exe cannot be spoofed by what somebody typed.
#
# Both names on purpose: this kiosk moved from Chromium to Firefox in
# September 2026 (Chromium drained the Pi's CMA pool dry every 990
# seconds; Firefox ran 2222 seconds in the same conditions with CmaFree
# stable and recovering). Keeping both means the watchdog does not become
# the thing that breaks if either browser is put back.
BROWSER_MARKS = ("firefox", "chrome")

# How long the server must hear nothing before it decides the tab is dead.
# The busiest poll is 120ms and the quietest is one second, so anything
# past a few seconds is already abnormal; three quarters of a minute is
# far enough out that a stalled network read or a slow page load cannot
# reach it, and short enough that nobody is standing in front of a dead
# screen for long.
SILENCE_SECONDS = 45.0

# How often to look. Cheap -- it is a clock comparison and, only when
# that comparison fails, one pass over /proc.
CHECK_SECONDS = 5.0

# Chromium needs a moment to come up and start serving the page again.
# Without this the watchdog would kill the browser it has just restarted,
# over and over.
COOLDOWN_SECONDS = 90.0

# ---------------------------------------------------------------- CMA ---
# The Pi's contiguous-memory pool, which the graphics stack allocates
# buffers out of. On this machine something in Chromium drains all 320 MB
# of it -- measured 2026-09-01, and measured again with a page holding
# nothing but text and a poll, which drained it just the same. So the leak
# is not this project's page and cannot be fixed here.
#
# What CAN be done is get out of the way before it runs out. The drain is
# not gradual: CmaFree sits flat for a quarter of an hour, then falls from
# ~300 MB to zero in about a hundred seconds, and the renderer dies the
# moment a raster tile (1920x320, 2.4 MB contiguous) cannot be allocated.
#
# Restarting on the way down turns a crash plus 45 seconds of dead screen
# into a three-second reload at a moment of our choosing.
CMA_MEMINFO = "/proc/meminfo"

# Act below this. Far enough down that only a real drain reaches it --
# CmaFree never leaves ~300 MB otherwise -- and, at the ~3 MB/s the drain
# runs at, still some thirty seconds clear of the wall.
CMA_LOW_KB = 120 * 1024

# Two readings in a row, not one. A single sample could catch a legitimate
# dip -- the bartender screen loading its images, say -- and restarting
# the browser over one unlucky reading is worse than the crash it avoids.
CMA_STRIKES_NEEDED = 2

# order/handoff.json exists for exactly as long as a drink is being made.
# A proactive restart during one would take the pouring screen away from
# whoever is standing at the machine, so it waits. If the drain then
# reaches the wall, the crash and the reactive path below handle it -- no
# worse than before this check existed.
HANDOFF_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "order", "handoff.json")

ENABLE_ENV = "FLEXMIX_KIOSK_WATCHDOG"

_lock = threading.Lock()
_last_request = 0.0        # monotonic; 0.0 means "never seen any traffic"
_quiet_until = 0.0         # monotonic; the cooldown after a restart
_cma_strikes = 0           # consecutive low-CMA readings
_started = False


def note_request() -> None:
    """Called by the server for every request it answers.

    Deliberately the cheapest thing that could work: one clock read and
    one assignment under a lock, on a path that runs several times a
    second for as long as the shop is open.
    """
    global _last_request

    with _lock:
        _last_request = time.monotonic()


def kiosk_browser_pids() -> list[int]:
    """The top-level kiosk Chromium processes, by reading /proc.

    /proc rather than pgrep: no subprocess, nothing to fail if pgrep is
    missing, and no chance of matching the shell that launched it -- the
    autostart script's own command line is the path of the script, not
    the URL inside it.
    """
    found: list[int] = []

    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue

        try:
            with open(f"/proc/{entry}/cmdline", "rb") as handle:
                cmdline = handle.read().decode("utf-8", "replace")
        except OSError:
            continue        # the process ended while we were looking

        # The page has to be what this process was told to open...
        if KIOSK_URL_MARK not in cmdline:
            continue

        # ...and the process has to actually BE a browser. os.readlink
        # rather than os.path.realpath: the latter would follow a dead
        # link to nothing and quietly compare an empty string.
        try:
            binary = os.path.basename(os.readlink(f"/proc/{entry}/exe"))
        except OSError:
            continue        # gone, or not ours to look at

        if any(mark in binary for mark in BROWSER_MARKS):
            found.append(int(entry))

    return found


def restart_kiosk_browser() -> int:
    """Ask the kiosk browser to quit, so its launcher reopens it.

    SIGTERM, not SIGKILL: Chromium takes it as a clean shutdown, and the
    `while true` loop that started it opens a fresh window a second
    later. A kill -9 would leave the profile looking crashed and hand the
    next customer a "restore pages?" bubble on top of the menu.
    """
    pids = kiosk_browser_pids()

    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError as error:
            print(f"[watchdog] could not signal {pid}: {error}",
                  file=sys.stderr, flush=True)

    return len(pids)


def read_cma_free_kb() -> int | None:
    """CmaFree from /proc/meminfo, or None where there is no CMA at all.

    None is the normal answer on a machine that is not a Pi, and it
    switches the whole proactive check off rather than guessing.
    """
    try:
        with open(CMA_MEMINFO, "r", encoding="ascii") as handle:
            for line in handle:
                if line.startswith("CmaFree:"):
                    return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        pass

    return None


def drink_in_progress() -> bool:
    """True while the machine is making a drink."""
    return os.path.exists(HANDOFF_FILE)


def _check_cma(now: float) -> bool:
    """Restart the browser if the CMA pool is about to run out.

    Returns whether it acted. Kept apart from the silence check because
    the two answer different questions: this one asks "is it ABOUT to
    die", the other "has it already died".
    """
    global _cma_strikes

    free = read_cma_free_kb()

    if free is None or free >= CMA_LOW_KB:
        _cma_strikes = 0
        return False

    _cma_strikes += 1

    if _cma_strikes < CMA_STRIKES_NEEDED:
        print(f"[watchdog] CmaFree {free // 1024} MB is low "
              f"({_cma_strikes}/{CMA_STRIKES_NEEDED}) -- confirming",
              file=sys.stderr, flush=True)
        return False

    if not kiosk_browser_pids():
        _cma_strikes = 0
        return False

    # Deliberately not "restart anyway": see HANDOFF_FILE above.
    if drink_in_progress():
        print(f"[watchdog] CmaFree {free // 1024} MB is low but a drink is "
              f"being made -- leaving the screen alone",
              file=sys.stderr, flush=True)
        return False

    print(f"[watchdog] CmaFree down to {free // 1024} MB -- restarting the "
          f"browser before the pool runs out and the tab is killed",
          file=sys.stderr, flush=True)

    killed = restart_kiosk_browser()
    _cma_strikes = 0

    print(f"[watchdog] signalled {killed} browser process(es) early; "
          f"holding off for {COOLDOWN_SECONDS:.0f}s",
          file=sys.stderr, flush=True)
    return True


def _tick() -> None:
    """One check. Separated from the loop so a test can call it."""
    global _quiet_until

    now = time.monotonic()

    with _lock:
        last = _last_request
        quiet_until = _quiet_until

    # Never seen traffic: the kiosk has not started, or this server is
    # running on somebody's desk. Either way there is nothing to restart.
    if last == 0.0 or now < quiet_until:
        return

    # Ahead of the silence check on purpose. Getting out early is a
    # three-second reload; being caught by the wall is a crash plus the
    # forty-five seconds it takes this function to notice.
    if _check_cma(now):
        with _lock:
            _quiet_until = now + COOLDOWN_SECONDS
            globals()["_last_request"] = now
        return

    silence = now - last

    if silence < SILENCE_SECONDS:
        return

    # Silence alone is not enough. If no kiosk browser is running, then
    # nothing is meant to be polling and the silence is correct -- the
    # screen may simply be off, or somebody may have closed it on purpose.
    if not kiosk_browser_pids():
        return

    print(f"[watchdog] no request for {silence:.0f}s while the kiosk "
          f"browser is running -- its tab is dead, restarting it",
          file=sys.stderr, flush=True)

    killed = restart_kiosk_browser()

    with _lock:
        _quiet_until = now + COOLDOWN_SECONDS
        # Treated as fresh traffic so the next check measures from the
        # restart rather than from the last request before the crash.
        globals()["_last_request"] = now

    print(f"[watchdog] signalled {killed} browser process(es); "
          f"holding off for {COOLDOWN_SECONDS:.0f}s",
          file=sys.stderr, flush=True)


def _loop() -> None:
    while True:
        time.sleep(CHECK_SECONDS)

        try:
            _tick()
        except Exception as error:      # noqa: BLE001 - never kill the thread
            # A watchdog that dies of its own exception is worse than no
            # watchdog, because the screen it was guarding looks guarded.
            print(f"[watchdog] check failed: {error}",
                  file=sys.stderr, flush=True)


def start() -> bool:
    """Start the watcher thread. Returns whether it is running."""
    global _started

    # Off unless asked for. See OPT-IN above: the guards cannot tell this
    # server apart from any other on the machine, so the decision of
    # "which server is allowed to restart the browser" is made by whoever
    # starts it, not by the code.
    if os.getenv(ENABLE_ENV, "").strip() != "1":
        return False

    if _started:
        return True

    _started = True
    threading.Thread(target=_loop, name="kiosk-watchdog",
                     daemon=True).start()
    cma = read_cma_free_kb()
    cma_note = (f"CmaFree < {CMA_LOW_KB // 1024} MB "
                f"(now {cma // 1024} MB)" if cma is not None
                else "no CMA on this machine, proactive check off")

    print(f"[watchdog] on: restart the browser early on {cma_note}, "
          f"or after {SILENCE_SECONDS:.0f}s with no requests "
          f"(unset {ENABLE_ENV} to disable)",
          file=sys.stderr, flush=True)
    return True
