"""Issue and redeem the tickets behind single-use QR labels.

WHAT A TICKET IS
    A row in order_ticket, keyed by the SHA-256 hash of the exact outer
    QR payload it was issued for. The digits on the label are only a
    pointer; this table is what says whether they are still worth a
    drink.

    Paper cannot record that it was scanned. So "single use" cannot live
    in the payload -- any check the label carries about itself is a
    check a photocopy carries too. It lives here, where a scan can
    change it.

    WHY payload_hash, NOT A PRINTED SERIAL
    qrproto (protocol v1.4) payloads carry no serial: they are SKU +
    instructions + timestamp + machine ID, encrypted, with no room left
    for a value this table would hand out. But every AES-GCM encryption
    draws a fresh random nonce, so two identical orders still produce
    two different payload strings -- the payload is already unique on
    its own, and its hash makes a perfectly good claim key.

    `serial` (AUTO_INCREMENT) stays as the table's own primary key and
    the short handle used by lookup() and in error_log -- it is simply
    never printed on a label or embedded in a payload.

THE LIFECYCLE
    issue()        -> unused        the store screen prints a label
    claim()        -> in_progress   the scanner accepts it, exactly once
    complete()     -> used          the drink was poured; done for good
    release()      -> unused        it failed, and a label exists to retry
    mark_failed()  -> noqr_err      it failed, and no label exists

    Which of the last two applies is decided by ONE thing: whether there
    is a piece of paper in the customer's hand. See below.

    Only claim() is a race. Two scans of the same label -- a double
    trigger on the scanner, or a photograph held up beside the original
    -- can arrive at once, and both must not win. It is written as a
    single UPDATE ... WHERE status = 'unused', so MySQL's row lock
    decides: one statement reports one row changed, the other reports
    none and is refused. Nothing here reads-then-writes, because between
    the read and the write is exactly where the second scan gets in.

WHAT A FAILED DRINK GOES BACK TO, AND WHY IT DEPENDS
    A pump that fails mid-pour is the machine's fault, not the customer's.
    What can be done about it depends entirely on whether they are holding
    a label.

    SCANNED ORDER -> release() -> 'unused'
        They printed a QR and scanned it. That paper still works, so the
        ticket is handed back and they simply scan it again. Anything else
        takes a paid-for drink and the means of proving it in one go.

    STARTED FROM THE STORE SCREEN -> mark_failed() -> 'noqr_err'
        The "chạy máy ngay (không cần quét)" button, for a dead scanner or
        a printer out of paper. Nothing was printed, so there is no label
        to hand back. 'unused' would describe a code that exists nowhere
        and can never be presented -- a row that reads as redeemable and
        is not. 'noqr_err' says what actually happened, and staff issue a
        fresh code, which puts a person in front of the failure.

    A poured drink is 'used' either way: that outcome does not depend on
    how the order was started.

WHY EXPIRY IS CHECKED HERE AND NOT BY A CLOCK
    The amounts on a label were computed from the recipe as it stood when
    it was printed. Change the recipe and an old label pours the old drink.
    So labels go stale, and TICKET_LIFETIME_HOURS is how stale is too
    stale. It is evaluated at claim time rather than by a sweep, because a
    machine that was switched off overnight never runs the sweep but is
    certainly still holding yesterday's labels.

    This is independent of qrproto's own TS + max_age_seconds freshness
    check (default 600s) -- that one guards against a label being
    presented long after it was printed at all; this one guards against
    a label pouring a recipe that has since changed.

"""

from __future__ import annotations

import hashlib

from configuration import machine
from database.core.connection import close_database_resources, connect_database

from flexmix_debug import trace          # noqa: E402


# How long a printed label stays good. A customer who pays and walks to the
# machine takes minutes; anything measured in days is a label that outlived
# the recipe it was priced and portioned against.
TICKET_LIFETIME_HOURS = machine.TICKET_LIFETIME_HOURS

STATUS_UNUSED = "unused"
STATUS_IN_PROGRESS = "in_progress"
STATUS_USED = "used"
STATUS_EXPIRED = "expired"
# An order started WITHOUT a scan that did not end in a drink. Terminal by
# necessity rather than by policy: there is no QR in anybody's hand that
# could bring it back. A failed order that WAS scanned goes to 'unused'
# instead -- see the note above.
STATUS_NOQR_ERR = "noqr_err"

# Kept in step with schema/schema.sql's ck_order_ticket_status. A value that is
# not in this set is rejected by the database anyway -- this is so it is
# rejected with a sentence rather than a constraint-violation traceback.
VALID_STATUSES = (
    STATUS_UNUSED, STATUS_IN_PROGRESS, STATUS_USED, STATUS_EXPIRED,
    STATUS_NOQR_ERR,
)


class TicketError(Exception):
    """A ticket could not be issued or redeemed.

    Carries `reason`, a short machine-readable tag, so callers can tell a
    label that was already drunk from one that never existed without
    matching on message text. The message itself is Vietnamese, because it
    is shown on the machine.
    """

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message


@trace
def hash_payload(payload: str) -> str:
    """SHA-256 hex digest of an outer QR payload -- the claim key.

    Exposed rather than kept private: a caller that only has a payload
    string sometimes needs the same hash this module computes
    internally -- order/run_flow.py logs which ticket a refused scan
    belonged to without a database round trip, for instance.
    """
    return hashlib.sha256(str(payload).encode("ascii")).hexdigest()


@trace
def issue(drink_id: int, payload: str, note: str = "") -> dict:
    """Mint a ticket for one already-built payload.

    Returns {'serial', 'payload_hash', 'payload'}.

    `payload` must already be the finished, printable payload string --
    unlike protocol v1.3's serial, nothing about a qrproto payload comes
    from this table, so there is no builder callback here: the caller
    (store_gui/serve.py) calls qrproto.create() first and hands the
    result straight in.

    `note` is the customer's free text. Stored beside the ticket rather
    than encoded into the payload, because the payload is numeric and
    always will be -- payload_hash is the handle that fetches everything
    a QR code cannot itself carry.
    """
    conn = None
    cursor = None
    payload = str(payload)
    payload_hash = hash_payload(payload)

    try:
        conn = connect_database()
        conn.start_transaction()
        cursor = conn.cursor()

        # The price AND the name are read and stored HERE, inside the same
        # transaction, rather than looked up when a report runs. A ticket
        # records a sale at the moment it was made; what the drink costs
        # next week, or whether it is still on the menu at all, are
        # different facts about a different day. Storing the name is also
        # what allows a drink to be deleted without erasing its history.
        # NULL rather than '' when there is nothing to say, so "has a
        # note" is one test everywhere instead of two.
        text = str(note or "").strip()[:200] or None

        cursor.execute(
            "INSERT INTO order_ticket (drink_id, price, drink_name, "
            "payload, payload_hash, note, status) "
            "SELECT %s, price, drink_name, %s, %s, %s, %s "
            "FROM drink WHERE drink_id = %s",
            (int(drink_id), payload, payload_hash, text, STATUS_UNUSED,
             int(drink_id)),
        )

        if cursor.rowcount == 0:
            raise TicketError(
                "unknown_drink", f"Không có món id {drink_id}.",
            )

        serial = int(cursor.lastrowid)
        conn.commit()

        return {"serial": serial, "payload_hash": payload_hash, "payload": payload}
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:      # noqa: BLE001 - the original error wins
                pass
        raise
    finally:
        close_database_resources(cursor, conn)


@trace
def claim(payload: str) -> dict:
    """Take a ticket for use. Raises TicketError if it cannot be taken.

    Returns the row's serial and drink_id on success, so the caller can
    check that the label is asking for the drink the ticket was sold for.

    payload_hash IS the lookup key, so unlike protocol v1.3's
    serial-then-payload double check, there is nothing to verify
    afterwards: the hash of a different payload is simply a different
    hash and will not match any row on its own.

    The checks happen in two passes on purpose. The UPDATE is attempted
    first and unconditionally -- that is the atomic part, and it must not
    be preceded by a decision made from a stale read. Only when it changes
    nothing do we go and look at why, and that lookup is allowed to be
    leisurely because by then the answer is an error message, not a gate.
    """
    conn = None
    cursor = None
    payload = str(payload)
    payload_hash = hash_payload(payload)

    try:
        conn = connect_database()
        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)

        # Expire in the same transaction as the claim, so a label cannot
        # slip through in the gap between being aged out and being taken.
        cursor.execute(
            "UPDATE order_ticket SET status = %s "
            "WHERE payload_hash = %s AND status = %s "
            "AND created_at < NOW() - INTERVAL %s HOUR",
            (STATUS_EXPIRED, payload_hash, STATUS_UNUSED,
             TICKET_LIFETIME_HOURS),
        )

        cursor.execute(
            "UPDATE order_ticket "
            "SET status = %s, scanned_at = NOW() "
            "WHERE payload_hash = %s AND status = %s",
            (STATUS_IN_PROGRESS, payload_hash, STATUS_UNUSED),
        )

        if cursor.rowcount == 1:
            cursor.execute(
                "SELECT serial, drink_id, note FROM order_ticket "
                "WHERE payload_hash = %s",
                (payload_hash,),
            )
            row = cursor.fetchone() or {}
            conn.commit()
            return {
                "serial": row.get("serial"),
                "payload_hash": payload_hash,
                "drink_id": row.get("drink_id"),
                # Read here rather than by a second lookup later: this is
                # the moment the ticket is known to be genuine and taken.
                "note": row.get("note") or "",
            }

        # Nothing was claimed. Find out what this payload actually is.
        cursor.execute(
            "SELECT status, serial, drink_id, created_at, scanned_at "
            "FROM order_ticket WHERE payload_hash = %s",
            (payload_hash,),
        )
        row = cursor.fetchone()
        conn.commit()

        raise _refusal(payload_hash, row)
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:      # noqa: BLE001 - the original error wins
                pass
        raise
    finally:
        close_database_resources(cursor, conn)


def _refusal(payload_hash: str, row: dict | None) -> TicketError:
    """Turn a failed claim into the most specific message available.

    Worth the effort: "QR này đã dùng rồi" sends the customer to the till,
    while "không nhận dạng được" sends staff to the log. Collapsing both
    into one error wastes everybody's time.

    Messages show the first 8 hex characters of the hash, not the full
    64 -- enough for staff to match a log line to a report row, short
    enough to read on the machine's screen. The old "payload_mismatch"
    reason no longer exists: a serial used to be looked up and then
    checked against its stored payload separately, but payload_hash IS
    the lookup, so a mismatched payload simply finds no row at all and
    falls into the `row is None` branch below.
    """
    short = payload_hash[:8]

    if row is None:
        return TicketError(
            "unknown",
            f"QR không hợp lệ trên máy này (mã vé {short}...).",
        )

    status = row.get("status")

    if status == STATUS_IN_PROGRESS:
        return TicketError(
            "in_progress",
            f"QR này đang được pha (mã vé {short}...).",
        )

    if status == STATUS_USED:
        when = row.get("scanned_at")
        return TicketError(
            "used",
            f"QR này đã được dùng rồi (mã vé {short}..."
            + (f", lúc {when}" if when else "") + ").",
        )

    if status == STATUS_NOQR_ERR:
        # Only reachable if a label was printed as well as started from
        # the screen -- the paper exists, the order behind it does not.
        return TicketError(
            "noqr_err",
            f"Đơn của mã này đã chạy không quét và bị lỗi "
            f"(mã vé {short}...). Vui lòng báo nhân viên để đặt lại.",
        )

    if status == STATUS_EXPIRED:
        return TicketError(
            "expired",
            f"QR đã quá hạn {TICKET_LIFETIME_HOURS} giờ "
            f"(mã vé {short}...). Vui lòng đặt lại.",
        )

    return TicketError(
        "unavailable",
        f"QR không dùng được (mã vé {short}..., trạng thái {status}).",
    )


@trace
def complete(payload_hash: str) -> bool:
    """Mark a claimed ticket as spent. True if this call did it."""
    return _finish(payload_hash, STATUS_USED, "completed_at = NOW()")


@trace
def release(payload_hash: str) -> bool:
    """Hand a claimed ticket back so the same label works again.

    For an order that came from a scan: the paper is still in the
    customer's hand and still worth a drink.

    scanned_at is cleared, so the row does not claim to have been scanned
    for an order that never happened.
    """
    return _finish(payload_hash, STATUS_UNUSED, "scanned_at = NULL")


@trace
def mark_failed(payload_hash: str) -> bool:
    """Close out a claimed ticket whose drink never happened.

    Only for orders started from the store screen with nothing printed.
    A scanned order uses release() -- see the note at the top.

    scanned_at is deliberately KEPT. This row is the only record that the
    order existed at all, and a row that says it was never scanned is not
    a record of an order that ran and failed.

    It used to keep an order_id beside it, to tie the failure back to its
    order in error_log. Both columns are gone now -- error_log.order_id on
    2026-09-07 and this table's on the same day (see
    database/migrate_drop_ticket_order_id.sql) -- and a fault names its
    ticket directly instead, by the "[Vé #123]" tag at the head of
    error_log.message.

    completed_at is stamped even though nothing was completed: it is when
    this ticket stopped being live, and a row with no end time reads as one
    still in progress.
    """
    return _finish(payload_hash, STATUS_NOQR_ERR, "completed_at = NOW()")


def _finish(payload_hash: str, status: str, extra: str) -> bool:
    """Move a ticket out of in_progress. Shared by every ending.

    Guarded on status = 'in_progress' rather than applied blindly, so a
    late completion cannot overwrite a ticket already settled, or re-open
    one that was used hours ago.
    """
    conn = None
    cursor = None

    try:
        conn = connect_database()
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE order_ticket SET status = %s, {extra} "
            f"WHERE payload_hash = %s AND status = %s",
            (status, str(payload_hash), STATUS_IN_PROGRESS),
        )
        changed = cursor.rowcount == 1
        conn.commit()
        return changed
    finally:
        close_database_resources(cursor, conn)


@trace
def release_stranded() -> list[str]:
    """Hand back every ticket stuck mid-order. Returns the payload_hash
    values freed.

    WHAT STRANDS A TICKET
        claim() marks a ticket in_progress and run_flow settles it when the
        drink ends. That settling runs in a `finally`, which covers an
        exception or a Ctrl+C but cannot survive a kill -9, a power cut, or
        the flow dying with the I2C bus. The row is then in_progress for
        ever, and the customer's code is refused with "đang được pha" for a
        drink nobody is making.

    WHY THEY GO BACK TO 'unused' AND NOT 'noqr_err'
        This cannot tell how the order was started -- that fact lived in
        the flow that died. So it takes the choice that is wrong in the
        cheaper direction: handing back a code for an order that had no
        label leaves an 'unused' row nobody can present, which expires on
        its own in TICKET_LIFETIME_HOURS and costs nothing. The opposite
        mistake takes a real label out of a real customer's hand after a
        power cut. One is untidy, the other is a drink they paid for.

    WHY IT IS SAFE TO FREE THEM ALL
        Only run_flow claims tickets, and it holds a single-instance lock,
        so no second flow can be part-way through one. The caller checks
        that nothing is listening on the runner's port before calling this,
        which is what proves no drink is actually being poured. A ticket the
        store screen has only ISSUED is 'unused', never in_progress, so a
        customer walking over with a fresh label is untouched.

    Called at startup rather than on a timer: that is the moment the two
    facts needed to make the judgement -- the lock is held and the port is
    free -- are both known to be true.
    """
    conn = None
    cursor = None

    try:
        conn = connect_database()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT payload_hash FROM order_ticket WHERE status = %s",
            (STATUS_IN_PROGRESS,),
        )
        hashes = [str(row["payload_hash"]) for row in cursor.fetchall()]

        if hashes:
            cursor.execute(
                "UPDATE order_ticket "
                "SET status = %s, scanned_at = NULL "
                "WHERE status = %s",
                (STATUS_UNUSED, STATUS_IN_PROGRESS),
            )

        conn.commit()
        return hashes
    finally:
        close_database_resources(cursor, conn)


@trace
def lookup(serial: int) -> dict | None:
    """Return one ticket row by its internal serial, or None.

    For inspection (management tooling), never for a gate -- claim()
    and its siblings look a ticket up by payload_hash, not serial.
    """
    conn = None
    cursor = None

    try:
        conn = connect_database()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT t.*, d.drink_name FROM order_ticket t "
            "LEFT JOIN drink d ON d.drink_id = t.drink_id "
            "WHERE t.serial = %s",
            (int(serial),),
        )
        return cursor.fetchone()
    finally:
        close_database_resources(cursor, conn)


def recent(limit: int = 20) -> list[dict]:
    """Return the most recently issued tickets, newest first."""
    conn = None
    cursor = None

    try:
        conn = connect_database()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT t.serial, t.payload_hash, t.drink_id, d.drink_name, "
            "t.status, t.created_at, t.scanned_at, t.completed_at "
            "FROM order_ticket t "
            "LEFT JOIN drink d ON d.drink_id = t.drink_id "
            "ORDER BY t.serial DESC LIMIT %s",
            (int(limit),),
        )
        return list(cursor.fetchall())
    finally:
        close_database_resources(cursor, conn)


def recent_page(before_serial: int | None, limit: int) -> list[dict]:
    """Read at most limit + 1 ticket snapshots in descending serial order.

    The extra row lets the caller form a next-page cursor. Never fetch the
    QR payload, hash, customer note, or current drink row for this view.
    """
    conn = None
    cursor = None
    try:
        conn = connect_database()
        cursor = conn.cursor(dictionary=True)
        columns = (
            "serial, drink_name, price, status, created_at, "
            "scanned_at, completed_at"
        )
        if before_serial is None:
            cursor.execute(
                f"SELECT {columns} FROM order_ticket "
                "ORDER BY serial DESC LIMIT %s",
                (limit + 1,),
            )
        else:
            cursor.execute(
                f"SELECT {columns} FROM order_ticket "
                "WHERE serial < %s ORDER BY serial DESC LIMIT %s",
                (before_serial, limit + 1),
            )
        return list(cursor.fetchall())
    finally:
        close_database_resources(cursor, conn)
