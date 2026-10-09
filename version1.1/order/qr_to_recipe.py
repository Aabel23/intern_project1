"""Turn a scanned QR code into the recipe the machine will run.

WHAT THIS FILE IS
    The join between the scanner and the runner. Something upstream puts a
    scanned code in scan/raw_qr.json; order/process_runner.py runs whatever
    is in order/current_recipe.json. This file reads the first and writes
    the second.

    It does one pass and exits. It does not watch for new scans -- it is a
    step inside a larger order flow, and that flow decides when an order
    has arrived and calls this.

THE FLOW OF ONE ORDER
    1.  Read the payload out of scan/raw_qr.json.
    2.  Verify it with qrproto.verify() -- protocol v1.4: decrypt
        (AES-256-GCM), check both CRCs, confirm the embedded MID matches
        this machine, confirm TS is still fresh, then check the
        instruction semantics. Any failure at any stage stops here --
        nothing is written. See choices_from_payload() for how each
        failure is classified.
    3.  Look the SKU up in the database. The SKU is the drink_id, and the
        recipe behind it is the base drink: every pumped ingredient, its
        grams, and its step.
    4.  Apply the customer's choices from the payload (see below).
    5.  Hand the adjusted rows to database/export_data.py, which is what
        already knows how to turn recipe rows into pump, manual and detect
        steps with pump numbers and pour durations.
    6.  Stamp a fresh order_id and created_at.
    7.  CLAIM THE TICKET -- see below -- and only then write
        order/current_recipe.json.

WHY THE TICKET IS CLAIMED SECOND-TO-LAST
    order_ticket rows are keyed by the SHA-256 hash of the exact payload
    string (see database/order_ticket.py) -- protocol v1.4 payloads carry
    no serial of their own, so the payload itself, hashed, is the handle.
    Claiming a ticket is what spends the code. It happens after the
    recipe is built and immediately before the file is written, which is
    the only ordering that is safe in both directions:

        later than the build, so a code that names a drink with no recipe
        is refused without being spent -- the customer keeps their label;

        earlier than the write, so the machine never starts pouring for a
        code somebody else is already using. If the write then fails, the
        ticket is released again before the error is raised.

    A label that is already in progress, already drunk, older than
    database/order_ticket.TICKET_LIFETIME_HOURS, or was never issued by
    this machine is refused here with a sentence saying which. The
    payload hash ends up in the recipe as "ticket_key", so
    order/run_flow.py can mark it used when the drink is poured or hand
    it back if the machine fails.

    This is separate from, and in addition to, qrproto's own TS-based
    freshness check in step 2: that one guards a payload that is simply
    too old to trust at all; this one guards a payload whose ticket was
    already spent, or that names a recipe that has since changed.

    --dry-run does not claim, and neither does --no-ticket. See RUNNING IT.

WHAT THE QR CHANGES, AND WHAT IT DOES NOT
    The payload carries the customer's choices, not the whole recipe.
    Pumped ingredients are not in it at all -- their grams come from the
    database, found through the SKU. What the payload can say is:

        type 02 BOOLEAN     0001 keep this ingredient, 0000 leave it out
        type 01 WEIGHT      pour exactly this many grams of it, replacing
                            the recipe's figure. The POS has already done
                            the arithmetic -- 50 g of sugar at 25% arrives
                            here as 13, not as a percentage to work out.

    There is no percentage type in protocol v1.4 -- see qrproto/constants.py
    for why, and note that TYPE_WEIGHT is "01" here, not "03": the two
    types this deployment uses were renumbered when percentage was
    dropped, they do not match protocol v1.3's numbering.

    An ingredient the payload says nothing about keeps whatever the recipe
    specifies. Silence is not a request to remove something: a payload that
    mentions no toppings is an order for the drink as designed, which is
    also the only thing an empty count-00 payload could sensibly mean.

    Dropping the last ingredient of a step drops the step with it, and the
    steps are renumbered so the runner sees 1, 2, 3 with no gaps.

WHY IT REFUSES TO OVERWRITE A RUNNING ORDER
    order/current_recipe.json is live state, not just a file: the runner
    reads it as it pours and the GUI polls it. Replacing it mid-drink
    would leave the machine executing one recipe while the screen shows
    another. If any step is 'running' or 'waiting', this refuses and says
    so. --force overrides it, for when a run has been killed and the file
    is stale.

RUNNING IT
    python3 -m order.qr_to_recipe              # newest scan -> recipe
    python3 -m order.qr_to_recipe --dry-run    # show it, write nothing
    python3 -m order.qr_to_recipe --payload 14059752786395867314497880745833621620228526260560581548525514765337709381573254518555442869756414206534259874317965167434156089

    A hand-typed --payload has to be a real qrproto payload -- encrypted,
    signed, bound to this machine's MACHINE_ID -- since verification
    happens before anything else. Build one with qrproto.create() rather
    than typing digits by hand.

    --no-ticket skips the claim, so a payload built this way can be
    run without the store screen having issued one. It exists for bench
    testing and says so loudly every time; it is reachable only from this
    command line, never from a scan.

    Then run the machine as usual:
        python3 -m order.process_runner
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path


if __package__ in {None, ""}:
    project_dir = str(Path(__file__).resolve().parent.parent)

    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

from database.db_core import connect_database
from database.export_data import (
    attach_actions,
    build_drinks,
    build_process_document,
    get_action_rows,
    get_recipe_rows,
    load_pump_calibration,
)
from database import order_ticket
import qrproto
from qrproto.errors import (
    ClockSkewError,
    ExpiredError,
    MachineMismatchError,
    ProtocolError,
)
from configuration.qrproto_config import MACHINE_ID, get_key

from flexmix_debug import trace          # noqa: E402


ORDER_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ORDER_DIR.parent

RAW_QR_FILE = PROJECT_DIR / "scan" / "raw_qr.json"
CURRENT_RECIPE_FILE = ORDER_DIR / "current_recipe.json"

# Statuses that mean the runner is part-way through this document.
BUSY_STATUSES = {"running", "waiting"}

TYPE_BOOLEAN_NAME = "boolean"
TYPE_WEIGHT_NAME = "weight"


class OrderError(Exception):
    """Raised when a scan cannot be turned into a runnable recipe."""


class ScanError(OrderError):
    """The digits themselves are wrong: bad CRC, corrupt envelope, wrong
    length, not digits -- qrproto stages 1-5 and 8 (FormatError,
    ChecksumError, CryptoError, and stage-8 semantic failures).

    Separate from its parent because the two mean opposite things to the
    person standing at the machine.

        OrderError  the code was READ correctly and refused -- already
                    used, expired, wrong machine, not from this machine.
                    Scanning it again will be refused again; they need
                    staff or a new order. Worth recording as a fault.

        ScanError   the code was not read correctly, or decrypted into
                    something that cannot be a genuine payload. The label
                    is probably fine: the scanner caught it at an angle,
                    the paper was creased, a digit was misread. The fix
                    is to scan it again, and there is nothing wrong with
                    the machine to record.

    Both CRCs and the AES-GCM tag exist precisely to make this
    distinction possible -- a misread is caught as a misread instead of
    being executed as some other drink, or silently accepted as a
    different one. Logging every one of them as a machine fault would
    bury the real faults in noise from creased paper. A stage-8 semantic
    failure (e.g. a duplicate ingredient) is grouped here too: with
    authentication this strong, a payload reaching stage 8 with bad
    content did not survive the scan intact, the same conclusion a bad
    CRC would reach.
    """


def now_text() -> str:
    """Local time as ISO 8601 with an offset, matching process_runner.py."""
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


@trace
def read_scanned_payload(path: Path) -> str:
    """Return the payload to build from raw_qr.json.

    The file holds one code -- the most recent scan, overwritten each time:

        {"qr_code": "0006...", "timestamp": "2026-08-07T14:13:47.534+07:00"}

    'payload' is accepted in place of 'qr_code', since that is the key the
    order flow writes by hand. A list is also accepted and its last entry
    used, which is what scan/scanner.py wrote before it was reduced to a
    single code; a file left over from then still works.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            content = json.load(handle)
    except FileNotFoundError as error:
        raise OrderError(
            f"Chưa có {path}. Cần một mã QR đã quét trước."
        ) from error
    except ValueError as error:
        raise OrderError(f"{path} không phải JSON hợp lệ: {error}") from error

    if isinstance(content, dict):
        payload = content.get("payload") or content.get("qr_code")

        if not payload:
            raise OrderError(
                f"{path} không có khóa 'payload' (hoặc 'qr_code')."
            )

        return str(payload)

    if isinstance(content, list):
        if not content:
            raise OrderError(f"{path} chưa có mã nào được quét.")

        latest = content[-1]

        if not isinstance(latest, dict):
            raise OrderError(f"Bản ghi cuối trong {path} không phải object.")

        payload = latest.get("qr_code") or latest.get("payload")

        if not payload:
            raise OrderError(
                f"Bản ghi cuối trong {path} không có 'qr_code'."
            )

        return str(payload)

    raise OrderError(
        f"{path} phải là object có 'payload', hoặc mảng bản ghi quét."
    )


def load_current_recipe(path: Path) -> dict | None:
    """Read the recipe currently on disk, or None if there isn't one."""
    try:
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
    except (FileNotFoundError, ValueError):
        return None

    return document if isinstance(document, dict) else None


def busy_steps(document: dict | None) -> list[str]:
    """Return the labels of any steps the runner is part-way through."""
    if not document:
        return []

    return [
        str(step.get("step"))
        for step in document.get("steps", [])
        if str(step.get("status")) in BUSY_STATUSES
    ]


@trace
def choices_from_payload(payload: str) -> tuple[int, dict[int, dict]]:
    """Verify a payload and return its SKU and the choices it carries.

    Returns (sku, {ingredient_id: {"kind": ..., "value": ...}}).

    A weight pair is the customer's chosen amount, worked out by whatever
    built the payload from the recipe's own 100% figure. It replaces the
    recipe's amount rather than scaling it. Only two kinds exist -- no
    percentage pair can arrive here, see qrproto/constants.py.

    Runs the full 8-stage check (qrproto.verify): decrypts, checks both
    CRCs, confirms MID matches MACHINE_ID, confirms TS is still fresh,
    then checks instruction semantics. Any stage failing raises one of
    qrproto's error subclasses, which process_payload() below sorts into
    ScanError or OrderError.
    """
    parsed = qrproto.verify(payload, key=get_key(), machine_id=MACHINE_ID)
    choices: dict[int, dict] = {}

    for item in parsed["instructions"]:
        if isinstance(item.value, bool):
            choices[item.ingredient] = {
                "kind": TYPE_BOOLEAN_NAME,
                "value": bool(item.value),
            }
        else:
            # An amount the customer chose. The recipe's own figure is the
            # 100% default, and the POS has already worked out the share, so
            # this replaces it outright rather than scaling it.
            choices[item.ingredient] = {
                "kind": TYPE_WEIGHT_NAME,
                "value": int(item.value),
            }

    return int(parsed["sku"]), choices


@trace
def apply_choices(
    rows: list[dict],
    choices: dict[int, dict],
) -> tuple[list[dict], list[str]]:
    """Adjust the recipe rows to match what the customer chose.

    Returns the kept rows and a human-readable note for each adjustment.
    A row is dropped when a boolean says no, and its gram figure is
    replaced when a weight choice says so (split across that
    ingredient's steps in the recipe's own proportions). Everything else
    is passed through, so an ingredient the payload never mentions is
    made exactly as the recipe specifies.
    """
    kept: list[dict] = []
    notes: list[str] = []
    seen_ingredients = {int(row["ingredient_id"]) for row in rows}

    # How much of each ingredient the recipe pours in total, used to share a
    # chosen weight out across the steps that pour it.
    weight_totals: dict[int, float] = {}

    for row in rows:
        key = int(row["ingredient_id"])
        weight_totals[key] = weight_totals.get(key, 0.0) + float(
            row["target_gram"]
        )

    for ingredient_id, choice in sorted(choices.items()):
        if ingredient_id not in seen_ingredients:
            notes.append(
                f"nguyên liệu {ingredient_id:02d} có trong mã QR nhưng "
                "không có trong công thức -- bỏ qua"
            )

    for row in rows:
        ingredient_id = int(row["ingredient_id"])
        choice = choices.get(ingredient_id)
        name = row["ingredient_name"]

        if choice is None:
            kept.append(row)
            continue

        if choice["kind"] == TYPE_BOOLEAN_NAME:
            if choice["value"]:
                kept.append(row)
            else:
                notes.append(
                    f"bỏ {name} (nguyên liệu {ingredient_id:02d}, "
                    f"bước {row['step_no']}) theo lựa chọn của khách"
                )
            continue

        if choice["kind"] == TYPE_WEIGHT_NAME:
            original = float(row["target_gram"])
            requested = float(choice["value"])

            # Split across the ingredient's steps in the recipe's own
            # proportions, so a two-step pour keeps its shape and the
            # totals still add up to what the customer asked for.
            total = weight_totals.get(ingredient_id, original)
            portion = (
                requested * (original / total) if total > 0 else requested
            )
            portion = round(portion, 2)

            if portion <= 0:
                notes.append(
                    f"bỏ {name} (nguyên liệu {ingredient_id:02d}) vì "
                    f"khách chọn {requested:g} g"
                )
                continue

            adjusted = dict(row)
            adjusted["target_gram"] = portion
            kept.append(adjusted)
            notes.append(
                f"{name}: {original:g} g -> {portion:g} g (khách chọn "
                f"{requested:g} g)"
            )
            continue

        # choices_from_payload() only ever produces TYPE_BOOLEAN_NAME or
        # TYPE_WEIGHT_NAME (qrproto has no percentage type) -- reaching
        # here means a caller built a choices dict by hand with a kind
        # this function does not know. Fail loudly rather than silently
        # keep the row unmodified.
        raise OrderError(
            f"nguyên liệu {ingredient_id:02d}: loại lựa chọn "
            f"{choice['kind']!r} không được hỗ trợ"
        )

    return kept, notes


@trace
def renumber_steps(
    rows: list[dict],
    actions: list[dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Close gaps left by dropped ingredients so steps run 1, 2, 3...

    Dropping the only ingredient of a step removes the step entirely. The
    runner labels its steps from these numbers, so leaving a hole would
    show the customer a jump from step 2 to step 4.

    Action steps are renumbered on the SAME mapping, never a second one of
    their own. An action pours nothing, so it owns a step number that no
    ingredient row carries; numbering the two lists apart would slide an
    action away from the pour it was written to follow -- a shake landing
    before the spirit it is meant to shake.
    """
    actions = list(actions or [])

    numbers = {int(row["step_no"]) for row in rows}
    numbers |= {int(action["step_no"]) for action in actions}

    remaining = sorted(numbers)
    renumbered = {old: new for new, old in enumerate(remaining, start=1)}

    def moved(source: list[dict]) -> list[dict]:
        result = []

        for row in source:
            copy = dict(row)
            copy["step_no"] = renumbered[int(row["step_no"])]
            result.append(copy)

        return result

    return moved(rows), moved(actions)


@trace
def build_recipe_for_sku(
    sku: int,
    choices: dict[int, dict],
) -> tuple[dict, list[str]]:
    """Build the process document for one SKU with the choices applied."""
    connection = connect_database()

    try:
        cursor = connection.cursor(dictionary=True)
        rows = get_recipe_rows(cursor)
        action_rows = get_action_rows(cursor)
        cursor.close()
    finally:
        connection.close()

    drink_rows = [row for row in rows if int(row["drink_id"]) == sku]

    if not drink_rows:
        raise OrderError(
            f"SKU {sku:04d} không có công thức nào trong database."
        )

    kept, notes = apply_choices(drink_rows, choices)

    if not kept:
        raise OrderError(
            f"SKU {sku:04d}: mọi nguyên liệu đều bị loại, không còn gì để pha."
        )

    drink_actions = [
        action
        for action in action_rows
        if int(action["drink_id"]) == sku
    ]

    kept, drink_actions = renumber_steps(kept, drink_actions)

    drinks = attach_actions(
        build_drinks(kept),
        drink_actions,
    )
    document = build_process_document(
        drinks[sku],
        drinks[sku].get("image"),
        load_pump_calibration(),
    )

    document["order_id"] = uuid.uuid4().hex
    document["created_at"] = now_text()
    document["updated_at"] = document["created_at"]

    return document, notes


def describe(document: dict, notes: list[str]) -> None:
    """Print what the machine is about to be asked to make."""
    print(f"\nSKU {document['drink_id']:04d}  {document['drink_name']}")
    print(f"  order_id  {document['order_id']}")
    print(f"  {len(document['steps'])} bước:")

    for step in document["steps"]:
        label = str(step.get("step"))
        kind = str(step.get("type"))

        if kind == "pump":
            detail = ", ".join(
                f"{pump['ingredient_name']['en']} {pump['gram']:g} g "
                f"({pump['duration_sec']:g}s)"
                for pump in step.get("pumps", [])
            )
        elif kind == "manual":
            # A manual step names its ingredient in 'label'; only a pump
            # step carries 'ingredient_name'.
            detail = ", ".join(
                f"{button['label']['en']} (panel {button['panel']})"
                for button in step.get("buttons", [])
            ) or "cổng bắt đầu"
        else:
            detail = "kiểm tra ly"

        print(f"    {label:<4} {kind:<7} {detail}")

    if notes:
        print("  thay đổi theo mã QR:")
        for note in notes:
            print(f"    - {note}")


@trace
def write_recipe(document: dict, path: Path) -> None:
    """Write current_recipe.json atomically.

    The GUI polls this file every second or so. Renaming a finished
    temporary file over it means a poll sees the old recipe or the new
    one, never a half-written document.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")

    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()

    temporary.replace(path)


@trace
def claim_ticket(payload: str) -> dict:
    """Spend the ticket this payload names. Returns what it is worth knowing.

    {'note': str, 'serial': int | None}. Raises OrderError if the ticket
    cannot be spent.

    WHY THE SERIAL COMES BACK
        It used to return the note alone. The serial is the number the
        ticket is KNOWN BY -- printed on the label, shown on the Vé QR
        screen -- and it is what tags this order's faults in error_log so
        the two screens can link to each other. It costs nothing to carry:
        order_ticket.claim() has always read it in the same transaction
        that claims the row, and this threw it away.

    It took the order's uuid as a second argument until 2026-09-07 and
    handed it to order_ticket.claim() to be written into the ticket row.
    Nothing ever looked a ticket up by it, so the column went; see
    database/migrate_drop_ticket_order_id.sql.

    order_ticket.claim() looks the ticket up by the payload's own hash --
    the hash is the lookup key, not the serial (see
    database/order_ticket.py). A preview payload (one the store screen
    only showed, never issued) was never given a row, so it lands in the
    same "unknown" refusal a label from another machine would -- no
    special-casing needed here.

    order_ticket.TicketError already carries a sentence saying exactly why
    a label was refused -- used, expired, in progress, unknown -- so it is
    passed straight through rather than flattened into a generic message.
    That sentence is what the customer is shown, and "this code has
    already been used" sends them somewhere useful while "invalid QR"
    does not.
    """
    try:
        claimed = order_ticket.claim(payload)
    except order_ticket.TicketError as error:
        raise OrderError(error.message) from error

    return {
        "note": str(claimed.get("note") or ""),
        "serial": claimed.get("serial"),
    }


@trace
def process_payload(
    payload: str,
    *,
    output_path: Path,
    dry_run: bool,
    force: bool,
    use_ticket: bool = True,
) -> dict:
    """Turn one payload into a written recipe. Raises OrderError."""
    try:
        sku, choices = choices_from_payload(payload)
    except (MachineMismatchError, ExpiredError, ClockSkewError) as error:
        # Caught BEFORE the plain ProtocolError below on purpose: all
        # three are ProtocolError subclasses, and except clauses test in
        # order, so this branch would never be reached if the generic
        # one came first. The payload decrypted and checked out
        # structurally here -- it is being refused on policy (wrong
        # machine, too old), not because it was misread. Scanning it
        # again will be refused again.
        raise OrderError(str(error)) from error
    except ProtocolError as error:
        # Everything else qrproto.verify() can raise: FormatError,
        # ChecksumError, CryptoError (stages 1-5) or a plain ProtocolError
        # from a stage-8 semantic failure. Either way the digits that
        # arrived, or what they decrypted to, are not what was printed --
        # with authentication this strong, a stage-8 failure is just as
        # much a sign of a bad scan as a bad CRC is.
        raise ScanError(f"Mã QR không hợp lệ: {error}") from error

    busy = busy_steps(load_current_recipe(output_path))

    if busy and not force:
        raise OrderError(
            f"{output_path.name} đang chạy dở (bước {', '.join(busy)}). "
            "Đợi máy pha xong, hoặc dùng --force để ghi đè."
        )

    document, notes = build_recipe_for_sku(sku, choices)

    # Carried into the recipe so run_flow.py can settle the ticket when the
    # drink finishes: used if it poured, and either handed back or marked
    # noqr_err if it did not, depending on whether a label exists. The file
    # is the only thing that survives between the two processes.
    ticket_key = order_ticket.hash_payload(payload)
    document["ticket_key"] = ticket_key

    describe(document, notes)

    if dry_run:
        print(f"\n--dry-run: chưa ghi {output_path}, chưa dùng vé QR.")
        return document

    if busy:
        print(f"\n  CẢNH BÁO: ghi đè lên đơn đang chạy dở "
              f"(bước {', '.join(busy)}) vì --force.")

    if use_ticket:
        claimed = claim_ticket(payload)
        note = claimed["note"]

        # Into the recipe, which is the only thing that reaches the
        # bartender screen. The screen shows it as a notice bar, because a
        # request nobody notices is the same as one nobody was told.
        if note:
            document["note"] = note
            print(f"\n  GHI CHÚ CỦA KHÁCH: {note}")

        # Also into the recipe, and for the same reason the ticket_key
        # above is: the file is the only thing that reaches the process
        # that pours the drink. process_runner.py reads it back out and
        # tags every fault it records with it, which is the whole link
        # from a fault to the ticket that caused it -- and it needed no
        # column, because the tag rides in error_log.message. See HOW A
        # FAULT STILL NAMES ITS TICKET in database/error_log.py.
        if claimed["serial"] is not None:
            document["ticket_serial"] = int(claimed["serial"])

        print(f"\nĐã nhận vé QR (mã {ticket_key[:8]}...).")
    else:
        print("\n  CẢNH BÁO: --no-ticket, mã QR này KHÔNG bị đánh dấu đã "
              "dùng và có thể quét lại.")

    try:
        write_recipe(document, output_path)
    except OSError as error:
        # The ticket is claimed but no recipe exists, so nothing will ever
        # finish this order and settle it. Closed out here, or the row sits
        # 'in_progress' until release_stranded() finds it hours later and
        # the customer's code is refused with "đang được pha" in the
        # meantime -- for an order that got no further than a failed write.
        if use_ticket:
            # release(), not mark_failed(): this is before anything was
            # poured, and if the code came off a label that label is
            # untouched and still worth a drink.
            order_ticket.release(ticket_key)
            print(f"Đã trả lại vé QR (mã {ticket_key[:8]}...).")
        raise OrderError(f"Không ghi được {output_path}: {error}") from error

    print(f"\nĐã ghi {output_path}")
    return document


@trace
def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a shell-friendly exit code."""
    parser = argparse.ArgumentParser(
        description="Đọc mã QR đã quét và cập nhật current_recipe.json.",
    )
    parser.add_argument(
        "--raw-qr", type=Path, default=RAW_QR_FILE,
        help=f"File mã đã quét (mặc định {RAW_QR_FILE}).",
    )
    parser.add_argument(
        "--output", type=Path, default=CURRENT_RECIPE_FILE,
        help=f"File công thức (mặc định {CURRENT_RECIPE_FILE}).",
    )
    parser.add_argument(
        "--payload",
        help="Dùng chuỗi này thay vì đọc file mã đã quét.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Hiển thị công thức nhưng không ghi file.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Ghi đè kể cả khi đơn hiện tại đang chạy dở.",
    )
    parser.add_argument(
        "--no-ticket", action="store_true",
        help="Bỏ qua kiểm tra vé QR dùng một lần. Chỉ dùng để thử máy.",
    )
    args = parser.parse_args(argv)

    try:
        if args.payload:
            payload = args.payload
        else:
            payload = read_scanned_payload(args.raw_qr)
            print(f"Mã QR: {payload}")

        process_payload(
            payload,
            output_path=args.output,
            dry_run=args.dry_run,
            force=args.force,
            use_ticket=not args.no_ticket,
        )
    except OrderError as error:
        print(f"LỖI: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
