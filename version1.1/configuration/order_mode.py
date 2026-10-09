"""How the shop turns a placed order into a drink. Read by both screens.

WHAT THIS DECIDES
    Which of the two buttons the customer screen offers once an order is
    on the bill:

        printQR    "Print QR"                       -> /api/print
        runDirect  "Start on the machine (no scan)" -> /api/start

    Both on is the machine as it has always behaved: print normally, run
    direct when the printer or the scanner lets you down. Turning one off
    hides that button, which is how a shop says "we only do it this way".

    It does NOT change what an order IS. Both paths mint the same
    single-use ticket through order_ticket.issue(), so takings, stock and
    the Vé QR screen cannot tell them apart -- see the note above the
    Start button in store_gui/drinks-pos.js. This only decides which of
    them the counter is offered.

WHY A FILE AND NOT THE DATABASE
    The same three reasons panel_control/button_watch.py keeps test mode
    in one:

      * it has to answer when MySQL does not. A shop whose database is
        briefly unreachable still has to know how to take an order.
      * it is machine configuration, not business data. There is one
        machine, one answer, and no history worth keeping.
      * no migration, and the pattern is already proven on this hardware.

    It is NOT in localStorage, which is where it lived until 2026-09-07
    and why it controlled nothing: the admin console and the customer
    screen are different browsers, and often different devices.

BOTH OFF IS REFUSED
    An order screen with no button is a shop that cannot sell. write()
    raises rather than storing it -- see there for why that is a refusal
    and not a silent correction.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
MODE_FILE = BASE_DIR / "order_mode.json"

# What an installation with no file behaves like: exactly what the machine
# did before this setting existed. A new machine, a cleared folder or an
# unreadable file must never change how the shop sells -- so the fallback
# is the old behaviour, not "off".
DEFAULTS = {"printQR": True, "runDirect": True}

# The switches this module knows about. Adding a third way to start an
# order means adding it here, giving it a default, and drawing its button
# -- the readers below iterate this rather than naming the keys.
SWITCHES = tuple(DEFAULTS)


class OrderModeError(ValueError):
    """A mode that must not be stored."""


def read() -> dict[str, bool]:
    """The current mode. DEFAULTS if the file is missing or unreadable.

    Never raises. Every caller of this is on a path that has to answer --
    a customer screen drawing its buttons, an admin page painting a
    toggle -- and none of them is improved by an exception about a config
    file. A missing file means a machine that has never been configured,
    which is the same thing as a machine configured the old way.
    """
    try:
        with open(MODE_FILE, encoding="utf-8") as handle:
            stored = json.load(handle)
    except (OSError, ValueError):
        return dict(DEFAULTS)

    if not isinstance(stored, dict):
        return dict(DEFAULTS)

    # Key by key, so a file written by an older or newer version -- one
    # missing a switch, or carrying one this version does not know --
    # still yields a complete, valid answer.
    return {name: bool(stored.get(name, DEFAULTS[name])) for name in SWITCHES}


def write(mode: dict[str, Any]) -> dict[str, bool]:
    """Store the mode. Returns what was stored. Raises OrderModeError.

    WHY BOTH OFF IS REFUSED RATHER THAN CORRECTED
        With neither switch on, the customer screen has an order, a total
        and nothing to press. Silently turning one back on would leave the
        admin page showing a setting the shop did not choose, and the
        counter working in a mode nobody selected. The person doing it is
        one click away from fixing it, so the honest move is to say no and
        let them.

    Written atomically -- temp file then replace, fsync'd first -- because
    the customer screen reads this between an order being placed and its
    buttons being drawn. A half-written file there is a modal with no
    button on it.
    """
    wanted = {name: bool(mode.get(name, DEFAULTS[name])) for name in SWITCHES}

    if not any(wanted.values()):
        raise OrderModeError(
            "Phải bật ít nhất một cách nhận đơn — tắt cả hai thì màn hình "
            "bán hàng không còn nút nào để bấm."
        )

    temporary = MODE_FILE.with_name(f".{MODE_FILE.name}.tmp")

    try:
        MODE_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(wanted, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temporary, MODE_FILE)
    except OSError as error:
        raise OrderModeError(f"Không lưu được chế độ bán hàng: {error}") from error

    return wanted
