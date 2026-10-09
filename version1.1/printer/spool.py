"""Hand one finished payload to the label printer, out of process.

WHY A SUBPROCESS AND NOT A FUNCTION CALL
    printer_qr talks to USB hardware. A driver that hangs, a device that
    disappears mid-write, a C library that segfaults -- none of those may
    take the web server down with it, and none of them can be caught by
    an `except` in the same process. A child process can simply be given
    a deadline and abandoned.

WHY IT LIVES HERE
    There are two callers now: store_gui/serve.py printing a new label,
    and admin_gui/serve.py reprinting one that was lost. The second was
    going to be a copy of the first, and a copy is how the two drift --
    a timeout raised in one and not the other, an exit code read in one
    and not the other. One of them would then be wrong about whether a
    label came out, which is the one thing this code exists to know.

WHAT IT REFUSES TO DO
    It never mints a ticket and never touches the database. It renders
    and prints the digits it is given, exactly as given. A payload is
    single-use -- order_ticket.claim() takes it atomically -- so printing
    the same one twice is two pieces of paper and still one drink. That
    is only true because a reprint comes through here with a payload that
    already exists; anything that issued a NEW payload would be a second
    live code and a second sale.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# printer_qr.py needs Pillow, which is not installed in the project venv --
# only in the system interpreter. Running it with sys.executable would fail
# on `from PIL import Image`, so the system python3 is named explicitly.
PRINTER_PYTHON = "python3"

# Long enough for a label to render and feed, short enough that a dead
# printer does not hold a request thread for the rest of the day.
PRINT_TIMEOUT_SECONDS = 30.0

PROJECT_DIR = Path(__file__).resolve().parent.parent


class PrinterUnavailable(RuntimeError):
    """The child could not be started at all -- no interpreter."""


class PrinterTimeout(RuntimeError):
    """The child was started and did not finish in time."""


def send_payload(payload: str) -> tuple[bool, str]:
    """Print one payload. Returns (printed, what the printer said).

    Raises PrinterUnavailable or PrinterTimeout for the two failures that
    are about the printer rather than the label, so a caller can answer
    them with their own status code. Everything else comes back as
    (False, message) -- the child ran and said no.

    The payload is NOT validated here. Both callers already know their
    own answer to "is this a real payload": the store screen has just
    been handed one by the ticket endpoint, and the console has just read
    one out of the row it is reprinting. A third opinion in the middle
    could only ever disagree with them.
    """
    try:
        result = subprocess.run(
            [PRINTER_PYTHON, "-m", "printer.printer_qr",
             "--payload", str(payload)],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            timeout=PRINT_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as error:
        raise PrinterUnavailable(
            f"Khong chay duoc '{PRINTER_PYTHON}'."
        ) from error
    except subprocess.TimeoutExpired as error:
        raise PrinterTimeout("May in khong phan hoi.") from error

    # Recorded so a label can be traced back to the payload that made it.
    # Without this, "the wrong QR printed" is unanswerable after the fact:
    # the PNG it renders through is overwritten on every print.
    sys.stderr.write(
        f"[print] payload {payload} -> exit {result.returncode}\n"
    )
    sys.stderr.flush()

    # printer_qr.main() catches its own errors and prints "LOI: ...", so a
    # zero exit code alone does not mean the label was printed.
    output = (result.stdout + result.stderr).strip()
    printed = result.returncode == 0 and "LOI:" not in output

    return printed, output
