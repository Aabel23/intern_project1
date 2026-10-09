"""Record machine faults in the database, and read them back.

WHAT THIS FILE IS
    The writer for the error_log table. Everything that can go wrong during
    an order -- a pump that did not deliver, a QR that was refused, a runner
    that would not start -- ends up here with enough context to answer
    "which pump, how often, on which drink".

    It is not the only record. order/flow.log is still written, and is the
    one that survives MySQL being unreachable. This is the one that can be
    queried.

THE ONE RULE
    Logging a fault must never cause one. Every function here swallows its
    own errors and reports them to stderr instead of raising: the caller is
    already handling a failure, and turning "the pump was short" into "the
    pump was short AND the database is down" helps nobody and can take an
    order down a path its author never considered.

    That is why log_error() returns an id or None rather than raising, and
    why nothing here is ever awaited or checked by the machine.

WHAT A GOOD ENTRY LOOKS LIKE
    severity    how loud it should read   'error'
    message     the sentence a person reads, numbers included

    severity is the only thing left to group by; everything else a person
    needs is in the sentence. Five columns were dropped on 2026-09-07 --
    source, order_id and detail because nothing read them, then category
    and ticket_key because the shop asked. What each one did is recorded
    in database/migrate_drop_error_columns.sql and
    database/migrate_drop_category_ticket.sql.

HOW A FAULT STILL NAMES ITS TICKET
    Dropping ticket_key cut the one join from a fault to the order that
    caused it, and the fault screen lost the link the shop used most. It
    is back, and it costs no column: the ticket's serial is written into
    the head of `message` itself, as a tag this module owns --

        [Ve #123] Buoc 2 bom thieu: 18.4g / 25g   (with real diacritics)

    `message` is TEXT and was always a free-form sentence, so nothing
    about the table changed and no migration was needed. Three functions
    are the whole format: tag_ticket() writes it, split_ticket() reads it
    back off a row, and ticket_like() turns a serial into the LIKE
    pattern that finds that ticket's faults. Everything that touches the
    tag goes through them -- admin_gui/serve.py included. Two spellings
    of it would agree today and drift apart the first time one is
    edited, and the failure is silent: a link that quietly matches
    nothing.

    Only rows written from 2026-09-07 onward carry a tag. Older rows show
    no ticket and nothing backfills them -- what you would backfill from
    was dropped with the column.

READING IT
    python3 -m database.error_log --recent 20
    python3 -m database.error_log --show 12        # one entry, in full
    python3 -m database.error_log --summary        # what fails most
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any


if __package__ in {None, ""}:
    project_dir = str(Path(__file__).resolve().parent.parent)

    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

from database.db_core import close_database_resources, connect_database


SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"

# Matches ck_error_log_severity in database.sql. Checked here so a typo is
# a corrected value rather than a constraint violation inside a failure
# handler.
VALID_SEVERITIES = (SEVERITY_INFO, SEVERITY_WARNING, SEVERITY_ERROR)

# message is TEXT, so this is only to stop a runaway traceback filling the
# table. The head of a message is the part that identifies it.
MESSAGE_LIMIT = 4000


# ---------------------------------------------------------------------------
# THE TICKET TAG
#
# The whole link from a fault to the order that caused it, and the only
# definition of it. See HOW A FAULT STILL NAMES ITS TICKET at the top.
#
# At the HEAD of the message on purpose. It survives MESSAGE_LIMIT (a
# runaway traceback truncates from the tail), it is the first thing a
# person reads off a raw row, and it lets the lookup be an anchored
# prefix rather than a scan for a tag that could be anywhere.
# ---------------------------------------------------------------------------
TICKET_TAG = "[Vé #{serial}] "

# Anchored, because that is where tag_ticket() puts it -- a tag found
# mid-sentence is text the machine happened to write, not a claim about
# which ticket this was.
TICKET_TAG_PATTERN = re.compile(r"^\[Vé #(\d+)\]\s*")


# Everything before the digits, and the LIKE pattern matching ANY tagged
# row -- for a reader counting faults across many tickets at once rather
# than listing one ticket's. Derived from TICKET_TAG rather than typed
# out again, so the tag has exactly one spelling in this codebase.
TICKET_TAG_HEAD = TICKET_TAG.split("{serial}")[0]
ANY_TICKET_LIKE = TICKET_TAG_HEAD + "%"

# How many characters of a message the tag can occupy at most.
# order_ticket.serial is INT UNSIGNED, so ten digits is the ceiling. A
# reader can ask the database for LEFT(message, TICKET_TAG_CHARS) and
# still hand the result to split_ticket() -- which is how the tickets
# screen counts faults without dragging every fault's full sentence
# across the wire, and without a second spelling of the tag living in
# SQL.
TICKET_TAG_CHARS = len(TICKET_TAG.format(serial="9" * 10))


def tag_ticket(message: str, serial: Any) -> str:
    """Put the ticket tag on a message. Unchanged if there is no ticket.

    A drink started from the store screen without a label still has a
    ticket, so most faults get one; the ones that do not are the faults
    around an order rather than inside it -- a code refused before any
    row was claimed, most of all.
    """
    try:
        return TICKET_TAG.format(serial=int(serial)) + str(message)
    except (TypeError, ValueError):
        # serial was None, or something that is not a number. A fault is
        # being recorded: an untagged sentence beats no sentence.
        return str(message)


def split_ticket(message: str) -> tuple[int | None, str]:
    """Take the tag back off. Returns (serial or None, the sentence).

    The reader half of tag_ticket(). The fault screen shows the serial as
    its own column and a link, so leaving `[Vé #123]` at the head of the
    sentence as well would say it twice on every row.
    """
    text = str(message or "")
    found = TICKET_TAG_PATTERN.match(text)

    if not found:
        return None, text

    return int(found.group(1)), text[found.end():]


def ticket_like(serial: Any) -> str:
    """The SQL LIKE pattern matching one ticket's faults.

    `[Vé #123]%`. Anchored by being a prefix pattern, so it cannot match
    a serial mentioned in the body of some other fault's sentence, and
    123 cannot match 1234 -- the closing bracket is in the pattern.

    Neither % nor _ can appear in it: everything before the digits is
    fixed and the digits come through int().
    """
    return TICKET_TAG.format(serial=int(serial)).rstrip() + "%"


def log_error(
    message: str,
    *,
    severity: str = SEVERITY_ERROR,
    drink_id: int | None = None,
    drink_name: str | None = None,
    step_label: str | None = None,
    step_type: str | None = None,
    ticket_serial: int | None = None,
) -> int | None:
    """Write one entry. Returns its id, or None if it could not be written.

    Six columns have been dropped from under this function: `ticket_serial`
    on 2026-08-27, then `source`, `order_id`, `detail`, `category` and
    `ticket_key` on 2026-09-07. What is left is a timestamped sentence
    with a severity, and the drink and step it happened on -- so whatever
    a person must know about a fault goes in `message`.

    `ticket_serial` is a keyword and not a column. It goes into the head
    of the sentence as a tag -- see HOW A FAULT STILL NAMES ITS TICKET at
    the top of this file. Pass it whenever the caller knows which order
    this happened to; leave it out when it genuinely does not, which is
    the case for a code refused before any ticket was claimed.

    Never raises. See THE ONE RULE at the top of this file.
    """
    try:
        if severity not in VALID_SEVERITIES:
            severity = SEVERITY_ERROR

        # Tagged BEFORE the truncation below, so a runaway traceback
        # loses its tail and keeps the half that says which order it
        # belongs to.
        if ticket_serial is not None:
            message = tag_ticket(message, ticket_serial)

        conn = None
        cursor = None

        try:
            conn = connect_database()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO error_log ("
                " severity, drink_id, drink_name, step_label, step_type,"
                " message"
                ") VALUES (%s,%s,%s,%s,%s,%s)",
                (
                    severity,
                    int(drink_id) if drink_id is not None else None,
                    str(drink_name)[:100] if drink_name else None,
                    str(step_label)[:16] if step_label else None,
                    str(step_type)[:16] if step_type else None,
                    str(message)[:MESSAGE_LIMIT],
                ),
            )
            error_id = int(cursor.lastrowid)
            conn.commit()
            return error_id
        finally:
            close_database_resources(cursor, conn)
    except Exception as error:      # noqa: BLE001 - logging must not throw
        # stderr rather than the table, for the obvious reason.
        print(f"[error_log] could not record the fault: {error}",
              file=sys.stderr, flush=True)
        return None


def log_step_failure(
    document: dict[str, Any],
    step: dict[str, Any],
    message: str,
    *,
    severity: str = SEVERITY_ERROR,
) -> int | None:
    """Record a failed step, pulling the drink and step out of the recipe.

    A convenience over log_error() because every call site inside the
    runner would otherwise repeat the same lookups.

    Thin now. It used to gather the step's numbers into `detail` and the
    order's `ticket_key` out of the recipe; both columns are gone, so
    what is left is the drink, the step and the sentence.

    `ticket_serial` comes out of the recipe document, where
    order/qr_to_recipe.py put it when the ticket was claimed. Every fault
    this function records happened while a drink was being made, so all
    of them can name their ticket -- unless the order was run with
    --no-ticket, and then there is no ticket to name.
    """
    return log_error(
        message,
        severity=severity,
        drink_id=document.get("drink_id"),
        drink_name=document.get("drink_name"),
        step_label=str(step.get("step")) if step.get("step") is not None else None,
        step_type=step.get("type"),
        ticket_serial=document.get("ticket_serial"),
    )


def recent(limit: int = 20) -> list[dict[str, Any]]:
    """Return the newest entries. [] if unreadable.

    No narrowing left: category was the last thing to narrow by and it
    was dropped on 2026-09-07. The fault screen filters by date and
    severity; this is the quick look from a terminal.
    """
    conn = None
    cursor = None

    try:
        conn = connect_database()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM error_log ORDER BY error_id DESC LIMIT %s",
            (int(limit),),
        )
        return list(cursor.fetchall())
    except Exception as error:      # noqa: BLE001 - a reader, not a gate
        print(f"[error_log] could not read: {error}", file=sys.stderr)
        return []
    finally:
        close_database_resources(cursor, conn)


def get(error_id: int) -> dict[str, Any] | None:
    """Return one entry by id, or None."""
    conn = None
    cursor = None

    try:
        conn = connect_database()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM error_log WHERE error_id = %s",
                       (int(error_id),))
        return cursor.fetchone()
    except Exception as error:      # noqa: BLE001
        print(f"[error_log] could not read: {error}", file=sys.stderr)
        return None
    finally:
        close_database_resources(cursor, conn)


def summary(days: int = 7) -> list[dict[str, Any]]:
    """Count faults by step and drink over the last N days.

    It grouped by category first until that column was dropped; severity
    is what is left to tell one kind of fault from another.
    """
    conn = None
    cursor = None

    try:
        conn = connect_database()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT severity, step_label, drink_name, COUNT(*) AS n,"
            "       MAX(created_at) AS last_seen "
            "FROM error_log "
            "WHERE created_at >= NOW() - INTERVAL %s DAY "
            "GROUP BY severity, step_label, drink_name "
            "ORDER BY n DESC, last_seen DESC",
            (int(days),),
        )
        return list(cursor.fetchall())
    except Exception as error:      # noqa: BLE001
        print(f"[error_log] could not read: {error}", file=sys.stderr)
        return []
    finally:
        close_database_resources(cursor, conn)


def _print_rows(rows: list[dict[str, Any]]) -> None:
    """One line per entry, newest first."""
    if not rows:
        print("Không có lỗi nào được ghi.")
        return

    print(f"{'ID':>6}  {'WHEN':<23} {'SEV':<8} {'STEP':<5} "
          f"{'DRINK':<14} MESSAGE")

    for row in rows:
        when = str(row.get("created_at") or "")[:23]
        message = " ".join(str(row.get("message") or "").split())
        print(
            f"{row['error_id']:>6}  {when:<23} "
            f"{str(row.get('severity') or ''):<8} "
            f"{str(row.get('step_label') or '-'):<5} "
            f"{str(row.get('drink_name') or '-')[:14]:<14} "
            f"{message[:70]}"
        )


def main(argv: list[str] | None = None) -> int:
    """Entry point for reading the log."""
    parser = argparse.ArgumentParser(
        description="Xem nhật ký lỗi của máy (bảng error_log).",
    )
    parser.add_argument("--recent", type=int, nargs="?", const=20,
                        metavar="N", help="N lỗi gần nhất (mặc định 20).")
    parser.add_argument("--show", type=int, metavar="ID",
                        help="Xem chi tiết một lỗi.")
    parser.add_argument("--summary", type=int, nargs="?", const=7,
                        metavar="DAYS",
                        help="Thống kê lỗi N ngày qua (mặc định 7).")
    args = parser.parse_args(argv)

    if args.show is not None:
        row = get(args.show)

        if row is None:
            print(f"Không có lỗi id {args.show}.")
            return 1

        for key, value in row.items():
            print(f"{key:<14} {value}")
        return 0

    if args.summary is not None:
        rows = summary(args.summary)

        if not rows:
            print(f"Không có lỗi nào trong {args.summary} ngày qua.")
            return 0

        print(f"{'COUNT':>6}  {'SEVERITY':<10} {'STEP':<5} "
              f"{'DRINK':<16} LAST")
        for row in rows:
            print(f"{row['n']:>6}  {str(row['severity']):<10} "
                  f"{str(row.get('step_label') or '-'):<5} "
                  f"{str(row.get('drink_name') or '-')[:16]:<16} "
                  f"{row['last_seen']}")
        return 0

    _print_rows(recent(
        limit=args.recent if args.recent is not None else 20,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
