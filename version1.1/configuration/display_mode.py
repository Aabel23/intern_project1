"""What resolution the kiosk screen runs at.

WHAT THIS DECIDES
    One thing: the mode X is driving the customer's panel at. Nothing on
    any page changes shape because of it -- the store screen is fluid and
    lays itself out to whatever it is given.

WHY IT IS WORTH A SETTING AT ALL
    It is the only lever that measurably changes how the menu FEELS on
    this hardware. The Pi 5's V3D composites every frame of a scroll, and
    that cost is very close to linear in the number of pixels:

        1920x1200   2,304,000 px    the panel's own mode
        1600x900    1,440,000 px    1.6x less work
        1280x800    1,024,000 px    2.25x less work

    Measured on this machine on 2026-09-09: at 1920x1200 a finger swipe
    down the menu visibly stutters; at 1280x800 the same swipe is smooth.
    Nothing about the page was changed between those two -- same markup,
    same photographs, same JavaScript. The photographs had already been
    reduced from 2752x1536 to 800px and it made no difference, because
    decoding was never the bottleneck. Rasterising was.

    The panel reports itself as 216x135mm, so 1920x1200 on it is roughly
    224 PPI. A customer stands at arm's length. There are pixels being
    paid for here that nobody can see.

WHY A FILE AND NOT THE DATABASE
    The same three reasons order_mode.py keeps its two switches in one:
    it has to answer when MySQL does not, it is machine configuration
    rather than business data, and there is one machine and one answer.

WHY NOTHING HERE IS EVER APPLIED AT BOOT BY THE BACKEND
    deploy/kiosk/flexmix-backend.service starts BEFORE X does -- see its
    own comment. An xrandr call from main.py would land before there is a
    display server to talk to and fail every time. The saved mode is
    applied by deploy/kiosk/kiosk-openbox-autostart.sh instead, which by
    definition runs inside the session it is configuring:

        python3 -m configuration.display_mode --apply-saved

THE MODE LIST IS NEVER TYPED
    Only what `xrandr --query` reports for the connected output is
    offered, and write() refuses anything else. A mode a panel cannot do
    is a black screen, and this machine has no keyboard or mouse to
    recover one with. The admin page pairs that with a 20-second revert
    for the same reason: see admin_gui/serve.py.
"""

from __future__ import annotations

import json
import os
import re
import subprocess

from configuration.configuration import runtime_path

# Lives outside the source tree -- see configuration/configuration.py for
# why. Note that write() below calls mkdir() on this file's parent, so
# /var/lib/flexmix has to exist already AND be owned by the service user:
# /var/lib is not writable by flexxource, so saving a mode into a directory
# nobody created raises PermissionError from the admin page. It is
# deploy/install.sh that creates it.
MODE_FILE = runtime_path("display_mode.json")

# The X display the kiosk session owns. The backend runs as the same user
# but is started by systemd without a DISPLAY, so every call here has to
# name it; ~/.Xauthority is found from HOME and needs no help.
DISPLAY = ":0"

# How long xrandr is given before we stop waiting for it. It normally
# answers in milliseconds; a hang means X is gone, and a request that
# blocks the admin API forever is worse than one that fails.
TIMEOUT = 10


class DisplayModeError(Exception):
    """A mode change that must not be made."""


def _xrandr(*args: str) -> str:
    """Run xrandr in the kiosk's X session and return its stdout."""
    result = subprocess.run(
        ["xrandr", *args],
        env={**os.environ, "DISPLAY": DISPLAY},
        capture_output=True, text=True, timeout=TIMEOUT,
    )

    if result.returncode != 0:
        raise DisplayModeError(
            (result.stderr or "xrandr thất bại").strip().splitlines()[-1])

    return result.stdout


def query() -> dict:
    """The connected output, its modes, and which one is live now.

    Returns {"output": str|None, "current": str|None, "preferred": str|None,
             "modes": [{"name","width","height","pixels","current",
                        "preferred"}]}

    The output is discovered rather than named. This Pi exposes HDMI-1 and
    HDMI-2 and the panel is on the second one; hard-coding that would
    break the day somebody moves the cable, and the failure would be a
    dead settings page on a machine nobody can plug a keyboard into.
    """
    text = _xrandr("--query")
    output = current = preferred = None
    modes: list[dict] = []
    inside = False

    for line in text.splitlines():
        head = re.match(r"^(\S+) connected", line)

        if head:
            # First connected output wins. A kiosk has exactly one panel;
            # if a second is ever plugged in, the one X lists first is the
            # one the session is actually laid out on.
            if output is None:
                output, inside = head.group(1), True
            else:
                inside = False
            continue

        if re.match(r"^\S+ (dis)?connected", line):
            inside = False
            continue

        if not inside:
            continue

        row = re.match(r"^\s+(\d+)x(\d+)\s+(.*)$", line)

        if not row:
            continue

        width, height, rates = int(row.group(1)), int(row.group(2)), row.group(3)
        name = f"{width}x{height}"

        # xrandr marks the live mode with * and the panel's own preferred
        # mode with +, on whichever refresh rate carries them.
        is_current = "*" in rates
        is_preferred = "+" in rates

        if is_current:
            current = name

        if is_preferred:
            preferred = name

        modes.append({
            "name": name,
            "width": width,
            "height": height,
            "pixels": width * height,
            "current": is_current,
            "preferred": is_preferred,
        })

    return {"output": output, "current": current,
            "preferred": preferred, "modes": modes}


def read() -> dict:
    """The saved mode, or {"mode": None} meaning "the panel's own".

    A missing or corrupt file is not an error worth raising: the honest
    answer to "what did the shop choose" when nothing was ever chosen is
    "nothing", and the caller then uses the panel's preferred mode.
    """
    try:
        with open(MODE_FILE, encoding="utf-8") as handle:
            stored = json.load(handle)
    except (OSError, ValueError):
        return {"mode": None}

    mode = stored.get("mode")

    return {"mode": mode if isinstance(mode, str) and mode else None}


def write(mode: str | None) -> dict:
    """Save a mode. Does NOT apply it -- see apply().

    Refuses anything the connected output did not report. The admin page
    only ever offers what query() returned, so a rejection here means the
    request did not come from that page, or the panel changed underneath
    it. Either way a mode this screen cannot show is a screen nobody in
    the shop can fix.
    """
    if mode is not None:
        if not isinstance(mode, str):
            raise DisplayModeError("Chế độ không hợp lệ.")

        known = {row["name"] for row in query()["modes"]}

        if mode not in known:
            raise DisplayModeError(
                f"Màn hình không hỗ trợ chế độ {mode}.")

    temporary = MODE_FILE.with_name(f".{MODE_FILE.name}.tmp")

    try:
        MODE_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump({"mode": mode}, handle, indent=2)
            handle.write("\n")

        os.replace(temporary, MODE_FILE)
    finally:
        temporary.unlink(missing_ok=True)

    return {"mode": mode}


def apply(mode: str | None) -> dict:
    """Switch the panel now. Does NOT save -- see write().

    Applying and saving are separate on purpose. The admin page applies
    first, waits for a human to confirm they can still see the screen,
    and only then saves; a mode that turns out to be unreadable is
    reverted having left nothing behind to come back after a reboot.

    mode=None asks xrandr for the panel's own preferred mode.
    """
    state = query()

    if not state["output"]:
        raise DisplayModeError("Không tìm thấy màn hình nào đang cắm.")

    if mode is None:
        _xrandr("--output", state["output"], "--auto")
        return {"mode": None, "applied": state["preferred"]}

    if mode not in {row["name"] for row in state["modes"]}:
        raise DisplayModeError(f"Màn hình không hỗ trợ chế độ {mode}.")

    _xrandr("--output", state["output"], "--mode", mode)
    return {"mode": mode, "applied": mode}


def apply_saved() -> dict:
    """Put the saved mode back. Called once per session by the kiosk.

    Never raises: this runs from the autostart script, before the browser,
    and a shop that cannot start its screen because a resolution setting
    failed is far worse than one running at the panel's default.
    """
    try:
        mode = read()["mode"]

        if mode is None:
            return {"ok": True, "mode": None, "note": "dùng chế độ mặc định"}

        return {"ok": True, **apply(mode)}
    except Exception as error:                      # noqa: BLE001 - reported
        return {"ok": False, "error": str(error)}


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Độ phân giải màn hình kiosk.")
    parser.add_argument("--apply-saved", action="store_true",
                        help="Áp chế độ đã lưu (dùng trong autostart).")
    parser.add_argument("--list", action="store_true",
                        help="Liệt kê các chế độ màn hình hỗ trợ.")
    args = parser.parse_args(argv)

    if args.apply_saved:
        report = apply_saved()
        print(report.get("note") or report.get("error")
              or f"Đã áp {report.get('applied')}")
        return 0 if report.get("ok") else 1

    state = query()
    print(f"Cổng: {state['output']}   đang chạy: {state['current']}")
    saved = read()["mode"]
    print(f"Đã lưu: {saved or '(mặc định)'}\n")

    native = next((m["pixels"] for m in state["modes"] if m["preferred"]), 0)

    for row in state["modes"]:
        mark = "*" if row["current"] else " "
        rel = f"{native / row['pixels']:.2f}x nhẹ hơn" if native else ""
        print(f" {mark} {row['name']:<12} {row['pixels']:>9,} px  {rel}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
