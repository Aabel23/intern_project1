"""Turn every drink in the database into a QR payload file.

WHAT THIS FILE IS
    The bridge from the beveragepos database to the QR Code Payload
    Protocol v1.3. It reads the drink and recipe tables, converts each
    recipe into one numeric payload, and writes those payloads into
    scan/qr_codes/ ready to be printed. scan/qr_payload.py owns the
    protocol itself; this file owns only the mapping from database rows
    onto protocol fields.

THE FLOW OF ONE RUN
    1.  Read every drink, every ingredient, and every recipe row.
    2.  For each drink, collapse its recipe rows into one instruction per
        ingredient (see WHY ROWS ARE COLLAPSED).
    3.  Decide each ingredient's protocol type from ingredient.data_type,
        and work out its data value (see HOW A ROW BECOMES AN INSTRUCTION).
    4.  Build the payload with qr_payload.encode(), which appends the CRC.
    5.  Decode it straight back with the ingredient registry enforced. A
        payload that will not survive its own decoder never reaches a file.
    6.  Write scan/qr_codes/drink_<id>_<name>.txt holding the raw digits,
        plus index.json holding the decoded breakdown of all of them.

WHAT GOES IN THE PAYLOAD, AND WHAT DOES NOT
    The payload carries what the customer chose, not the whole recipe:

        data_type 'percentage' -> type 01, a share of this ingredient's own
                                  recipe amount
        data_type 'boolean'    -> type 02, 0001 because the recipe lists it
        data_type 'weight'     -> OMITTED, the pumps handle it

    A weight-typed ingredient is poured automatically. Its gram figure is
    fixed by the recipe, the machine already has it in the database, and
    the SKU at the front of the payload is what finds it. Putting it in
    the QR code as well would print a number that can only ever agree with
    the database or be wrong -- so it is left out.

    That is also what ingredient.data_type has always meant: the schema
    describes it as "cách khách chọn nguyên liệu này khi đặt món", how the
    customer picks this ingredient when ordering. A percentage is a dial
    the customer turns and a boolean is a box they tick; a weight is
    neither, because nobody is asked about it.

    The consequence is that most drinks encode to an empty payload. A
    recipe of nothing but pumped liquids has no customer choices in it, so
    it is 17 digits of SKU, serial and checksum. Section 2.3 is explicit
    that this is valid and not an error: it identifies a SKU with no
    instructions.

THESE LABELS CANNOT BUY A DRINK
    Every payload here carries SERIAL_NONE. Real orders carry a serial
    naming a row in the order_ticket table, and that row is what makes a
    code redeemable exactly once; these files have no order behind them, so
    they get the serial that no ticket will ever match.

    Scan one and order/qr_to_recipe.py refuses it by name, saying it is a
    sample label. That is deliberate: without it, printing this directory
    would produce a sheet of free drinks. What the files remain good for is
    checking the encoder, sizing a symbol before ordering sticker stock,
    and reading a drink's options off the digits by eye.

    Type 03 still exists in scan/qr_payload.py and still round-trips. It
    is simply not reachable from this generator while every weight-typed
    ingredient is pump-driven.

    A percentage is a share of that one ingredient's own recipe amount,
    not of the whole drink. recipe.target_gram IS the 100% figure, so a
    payload carrying 100.0 pours it exactly as written and 50.0 pours half
    -- which is how order/qr_to_recipe.py reads it at the other end.

    What this file emits for a dial is DIAL_DEFAULT_PERCENT of the recipe
    amount: these are label payloads, printed once per drink, so they carry
    the drink as it is normally made. A customer's own choice comes from
    the POS instead.

WHY ROWS ARE COLLAPSED
    A recipe may pour the same ingredient at more than one step -- SO1
    pours Water at step 1 and again at step 4. The protocol forbids an
    ingredient appearing in two pairs (section 7.4) because two pairs
    naming one ingredient are contradictory by construction.

    So the rows are summed into a single instruction per ingredient. This
    is lossless for the ratio and lossy for the ordering: a payload says
    what is in the drink, never in what order or across how many steps.
    Anything rebuilding a runnable recipe from a scan has to get the step
    structure from the database, which is what the SKU is for.

WHAT THIS CANNOT CATCH
    The protocol caps ingredients at 24 and pairs at 12. Both hold for the
    current catalogue with room to spare, and a drink that broke either
    limit would be reported rather than silently truncated.

RUNNING IT
    python3 -m scan.generate_drink_qr              # write the files
    python3 -m scan.generate_drink_qr --dry-run    # show them, write nothing
    python3 -m scan.generate_drink_qr --drink 6    # just one drink
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path


if __package__ in {None, ""}:
    project_dir = str(Path(__file__).resolve().parent.parent)

    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

from database.db_core import connect_database
from scan.qr_payload import (
    Grams,
    Instruction,
    MAX_PAIRS,
    Percent,
    ProtocolError,
    SERIAL_NONE,
    WEIGHT_MAX_RAW,
    decode,
    encode,
    minimum_version,
    symbol_dimensions,
)


SCAN_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SCAN_DIR / "qr_codes"

# ingredient.data_type -> protocol type. 'number' is the pre-rename name
# for 'weight' and is still accepted so an un-migrated database reports a
# clear result rather than an unhandled data_type.
WEIGHT_DATA_TYPES = {"weight", "number"}
PERCENTAGE_DATA_TYPES = {"percentage"}
BOOLEAN_DATA_TYPES = {"boolean"}

# A label carries the drink as it is normally made: every topping in, and a
# dial at the amount the recipe already pours.
DIAL_DEFAULT_PERCENT = 100.0

DRINK_QUERY = """
    SELECT drink_id, drink_name, available
    FROM drink
    ORDER BY drink_id
"""

INGREDIENT_QUERY = """
    SELECT ingredient_id, ingredient_name, type, data_type
    FROM ingredient
    ORDER BY ingredient_id
"""

RECIPE_QUERY = """
    SELECT drink_id, ingredient_id, step_no, target_gram
    FROM recipe
    ORDER BY drink_id, step_no, ingredient_id
"""


def slugify(name: str) -> str:
    """Turn a drink name into a lowercase filename fragment."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return slug or "drink"


def read_catalogue() -> tuple[list[dict], dict[int, dict], list[dict]]:
    """Read drinks, ingredients and recipe rows from the database."""
    connection = connect_database()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(DRINK_QUERY)
        drinks = cursor.fetchall()

        cursor.execute(INGREDIENT_QUERY)
        ingredients = {row["ingredient_id"]: row for row in cursor.fetchall()}

        cursor.execute(RECIPE_QUERY)
        recipe_rows = cursor.fetchall()

        cursor.close()
    finally:
        connection.close()

    return drinks, ingredients, recipe_rows


def collapse_rows(rows: list[dict]) -> dict[int, dict]:
    """Sum one drink's recipe rows into a single entry per ingredient.

    Returns ingredient_id -> {"gram": total, "steps": [step numbers]}.

    Only used for ingredients that become payload pairs. Section 7.4
    forbids an ingredient appearing in two pairs, so one that is poured at
    more than one step has to be merged before it can be encoded. Anything
    not encoded is left alone -- see build_instructions().
    """
    totals: dict[int, dict] = {}

    for row in rows:
        entry = totals.setdefault(
            row["ingredient_id"], {"gram": 0.0, "steps": []},
        )
        entry["gram"] += float(row["target_gram"])
        entry["steps"].append(int(row["step_no"]))

    return totals


def build_instructions(
    rows: list[dict],
    ingredients: dict[int, dict],
) -> tuple[list[Instruction], list[dict]]:
    """Convert one drink's recipe rows into protocol instructions.

    Returns the instructions and a breakdown describing how the payload
    was arrived at, for the index file and the console report. The two are
    not parallel: the breakdown also lists the pumped ingredients, which
    never become instructions.

    Pumped ingredients are reported one line per recipe row, exactly as
    the database stores them. They are never merged: merging exists only
    to satisfy the one-pair-per-ingredient rule, and a pumped ingredient
    never becomes a pair. Summing them would print a gram figure that
    appears nowhere in the recipe table -- SO1's Water is 55 g at step 1
    and 60 g at step 4, not a single 115 g pour.
    """
    encoded_rows = [
        row for row in rows
        if ingredients[row["ingredient_id"]]["data_type"]
        not in WEIGHT_DATA_TYPES
    ]
    pumped_rows = [
        row for row in rows
        if ingredients[row["ingredient_id"]]["data_type"] in WEIGHT_DATA_TYPES
    ]

    instructions: list[Instruction] = []
    breakdown: list[dict] = []

    # Pumped automatically from the recipe the SKU points at. Listed per
    # row, in step order, so the report mirrors the recipe table.
    for row in sorted(pumped_rows, key=lambda r: (r["step_no"],
                                                  r["ingredient_id"])):
        ingredient = ingredients[row["ingredient_id"]]
        breakdown.append({
            "ingredient_id": row["ingredient_id"],
            "ingredient_name": ingredient["ingredient_name"],
            "ingredient_type": ingredient["type"],
            "data_type": ingredient["data_type"],
            "gram": round(float(row["target_gram"]), 2),
            "steps": [int(row["step_no"])],
            "percent": None,
            "encoded_value": None,
            "in_payload": False,
        })

    totals = collapse_rows(encoded_rows)

    for ingredient_id in sorted(totals):
        ingredient = ingredients[ingredient_id]
        data_type = ingredient["data_type"]
        name = ingredient["ingredient_name"]
        gram = totals[ingredient_id]["gram"]

        share = None

        if data_type in BOOLEAN_DATA_TYPES:
            value: float | bool | Grams = True

        elif data_type in PERCENTAGE_DATA_TYPES:
            # A dial carries the resulting WEIGHT, not the percentage: the
            # arithmetic is done here so the machine reads grams outright.
            # store_gui/drinks-pos.js does exactly the same with whatever
            # the customer picked, so both producers agree.
            share = DIAL_DEFAULT_PERCENT
            grams = int(math.floor(gram * share / 100.0 + 0.5))

            if grams <= 0:
                # 0% means leave it out; a weight of zero cannot say that.
                value = False
            else:
                value = Grams(grams)

        else:
            raise ProtocolError(
                f"ingredient {ingredient_id} ({name}) has data_type "
                f"'{data_type}', which this generator does not handle"
            )

        instructions.append(
            Instruction(ingredient=ingredient_id, value=value),
        )
        breakdown.append({
            "ingredient_id": ingredient_id,
            "ingredient_name": name,
            "ingredient_type": ingredient["type"],
            "data_type": data_type,
            "gram": round(gram, 2),
            "steps": sorted(totals[ingredient_id]["steps"]),
            "percent": share,
            "encoded_value": (
                bool(value) if isinstance(value, bool) else float(value)
            ),
            "in_payload": True,
        })

    # Report in pour order so the listing reads like the recipe table. A
    # merged entry sorts by its first step. This only reorders the
    # breakdown; `instructions` keeps the order the payload was built in.
    breakdown.sort(key=lambda item: (item["steps"][0], item["ingredient_id"]))

    return instructions, breakdown


def build_drink_payload(
    drink: dict,
    rows: list[dict],
    ingredients: dict[int, dict],
) -> dict:
    """Build and verify one drink's payload. Raises ProtocolError if invalid."""
    instructions, breakdown = build_instructions(rows, ingredients)

    # Counted after the weight-typed ingredients are dropped, since only
    # what is encoded takes up a pair.
    if len(instructions) > MAX_PAIRS:
        raise ProtocolError(
            f"{len(instructions)} encoded ingredients exceeds the protocol "
            f"maximum of {MAX_PAIRS} pairs"
        )
    # SERIAL_NONE, not a real serial. These files are reference labels --
    # one per drink on the menu, regenerated whenever the recipes change --
    # and a ticket belongs to one customer's order, so there is nothing
    # here to give them. Scanning one is refused by name in
    # order/qr_to_recipe.py rather than by accident, which is what makes a
    # printed menu sheet useless as a stack of free drinks.
    #
    # These payloads stay useful for what they are for: checking the
    # encoder, sizing a symbol, and reading a drink's options off the label
    # by eye.
    payload = encode(int(drink["drink_id"]), SERIAL_NONE, instructions)

    # Decode it back with the registry enforced. Nothing reaches a file
    # that its own decoder would refuse.
    decode(payload, registry=set(ingredients))

    version = minimum_version(payload)

    return {
        "sku": int(drink["drink_id"]),
        "drink_name": drink["drink_name"],
        "available": bool(drink["available"]),
        "serial": SERIAL_NONE,
        "single_use": False,
        "payload": payload,
        "digits": len(payload),
        "count": len(instructions),
        "qr_version": version,
        "footprint_mm": symbol_dimensions(version)["footprint_mm"],
        "weighed_gram": round(
            sum(
                item["gram"] for item in breakdown
                if item["data_type"] in WEIGHT_DATA_TYPES
            ),
            2,
        ),
        "merged_steps": sorted(
            item["ingredient_id"]
            for item in breakdown
            if len(item["steps"]) > 1
        ),
        "instructions": breakdown,
    }


def write_outputs(results: list[dict], output_dir: Path) -> list[Path]:
    """Write one payload file per drink, plus a combined index.

    Each drink file holds nothing but the raw code:

        {"payload": "00010301010522020103480401013032301"}

    Deliberately just the one key. Whatever scans a label needs the digits
    and nothing else, and every other fact about the drink -- its name,
    its grams, its steps -- is in the database behind the SKU. index.json
    carries the derivation for people, not for the machine.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for result in results:
        name = f"drink_{result['sku']:04d}_{slugify(result['drink_name'])}.json"
        path = output_dir / name
        path.write_text(
            json.dumps({"payload": result["payload"]}, indent=2) + "\n",
            encoding="utf-8",
        )
        written.append(path)

    index_path = output_dir / "index.json"
    index_path.write_text(
        json.dumps(
            {"protocol": "flexmix.qr/1.3", "drinks": results},
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    written.append(index_path)

    return written


def report(result: dict) -> None:
    """Print one drink's payload and how each field was derived."""
    print(f"\nSKU {result['sku']:04d}  {result['drink_name']}"
          f"   ({result['weighed_gram']:g} g weighed)")
    print(f"  payload  {result['payload']}")
    print(f"  {result['digits']} digits, count {result['count']:02d}, "
          f"QR version {result['qr_version']} at level H "
          f"({result['footprint_mm']:g} mm square at 0.5 mm modules)")

    for item in result["instructions"]:
        if not item["in_payload"]:
            shown = "--       pumped, not encoded"
        elif item["data_type"] in BOOLEAN_DATA_TYPES:
            shown = "type 02  boolean  yes"
        else:
            # A dial is encoded as a WEIGHT, so report the grams that
            # actually reach the payload, not the percentage they came from.
            grams = item["encoded_value"]
            if grams is False or grams is None:
                shown = "type 02  boolean  no   (0% -- left out)"
            else:
                shown = (f"type 03  weight   {int(grams)} g"
                         f"  ({item['percent']:.0f}% of {item['gram']:g} g)")

        steps = item["steps"]
        where = (
            f"step {steps[0]}" if len(steps) == 1
            else f"steps {'+'.join(str(s) for s in steps)} merged"
        )
        print(f"    {item['ingredient_id']:02d} {item['ingredient_name']:<18}"
              f" {item['gram']:>7.2f} g  {where:<16}  {shown}")

    if result["count"] == 0:
        print("    (no customer choices -- empty payload, valid per "
              "section 2.3)")


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a shell-friendly exit code."""
    parser = argparse.ArgumentParser(
        description="Generate QR payload files for every drink.",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT_DIR,
        help=f"Where to write (default {DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--drink", type=int, action="append",
        help="Only this drink_id. May be repeated.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show the payloads without writing any file.",
    )
    args = parser.parse_args(argv)

    try:
        drinks, ingredients, recipe_rows = read_catalogue()
    except Exception as error:
        print(f"Không đọc được database: {error}", file=sys.stderr)
        return 1

    out_of_range = [
        ingredient_id for ingredient_id in ingredients if ingredient_id > 24
    ]
    if out_of_range:
        print(
            "Ingredient id vượt quá giới hạn 24 của giao thức: "
            + ", ".join(str(i) for i in out_of_range),
            file=sys.stderr,
        )
        return 1

    wanted = set(args.drink) if args.drink else None
    rows_by_drink: dict[int, list[dict]] = {}

    for row in recipe_rows:
        rows_by_drink.setdefault(row["drink_id"], []).append(row)

    results: list[dict] = []
    failures = 0

    for drink in drinks:
        drink_id = int(drink["drink_id"])

        if wanted is not None and drink_id not in wanted:
            continue

        rows = rows_by_drink.get(drink_id, [])

        try:
            result = build_drink_payload(drink, rows, ingredients)
        except ProtocolError as error:
            print(f"\nSKU {drink_id:04d}  {drink['drink_name']}",
                  file=sys.stderr)
            print(f"  BỎ QUA: {error}", file=sys.stderr)
            failures += 1
            continue

        results.append(result)
        report(result)

    if not results:
        print("\nKhông tạo được payload nào.", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"\n--dry-run: {len(results)} payload, chưa ghi file nào.")
        return 1 if failures else 0

    written = write_outputs(results, args.output)
    print(f"\nĐã ghi {len(written)} file vào {args.output}:")
    for path in written:
        print(f"  {path.name}")

    if failures:
        print(f"\n{failures} món bị bỏ qua.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
