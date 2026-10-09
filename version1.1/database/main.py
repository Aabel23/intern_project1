# ============================================================
# UNIFIED DATABASE COMMAND LINE
# ============================================================

import argparse
import json
from pathlib import Path

from mysql.connector import Error

try:
    from .db_core import apply_database_sql, recalculate_thresholds_in_database
    from .inventory_service import (
        add_inventory,
        check_inventory,
        consume_drink,
        set_inventory,
        subtract_inventory,
        update_drinks_inventory,
        update_inventory_batch,
    )
except ImportError:
    from db_core import apply_database_sql, recalculate_thresholds_in_database
    from inventory_service import (
        add_inventory,
        check_inventory,
        consume_drink,
        set_inventory,
        subtract_inventory,
        update_drinks_inventory,
        update_inventory_batch,
    )


# ============================================================
# ARGUMENTS
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="BeveragePOS database manager",
    )

    commands = parser.add_subparsers(
        dest="command",
        required=True,
    )

    commands.add_parser(
        "update",
        help="Read database.sql and safely update database",
    )

    commands.add_parser(
        "reset",
        help="Drop database and recreate it from database.sql",
    )

    commands.add_parser(
        "check-inventory",
        help="Recalculate thresholds and drink.in_stock from ingredients",
    )

    commands.add_parser(
        "update-drinks",
        help="Update drink.in_stock from ingredient stock",
    )

    commands.add_parser(
        "recalculate-thresholds",
        help="Recalculate all threshold_gram values",
    )

    for command_name, help_text in (
        ("set-stock", "Set exact inventory for one ingredient"),
        ("add-stock", "Add inventory for one ingredient"),
        ("subtract-stock", "Subtract inventory for one ingredient"),
    ):
        command = commands.add_parser(command_name, help=help_text)
        command.add_argument("--ingredient-id", type=int, required=True)
        command.add_argument("--gram", required=True)

    consume = commands.add_parser(
        "consume-drink",
        help="Subtract stock according to a drink recipe",
    )
    consume.add_argument("--drink-id", type=int, required=True)
    consume.add_argument("--quantity", type=int, default=1)

    batch = commands.add_parser(
        "machine-update",
        help="Update stock from a machine readings JSON file",
    )
    batch.add_argument("--file", type=Path, required=True)
    batch.add_argument(
        "--mode",
        choices=("set", "add", "subtract"),
        default="set",
    )

    return parser


# ============================================================
# MACHINE JSON
# ============================================================

def read_machine_file(path: Path) -> dict[int, float]:
    if not path.exists():
        raise FileNotFoundError(f"Machine file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    raw_readings = data.get("ingredients", data)

    if isinstance(raw_readings, list):
        readings = {
            int(item["ingredient_id"]): item["amount"]
            for item in raw_readings
        }
    elif isinstance(raw_readings, dict):
        readings = {
            int(ingredient_id): gram
            for ingredient_id, gram in raw_readings.items()
        }
    else:
        raise ValueError(
            "Machine JSON must contain a dictionary or ingredients list"
        )

    return readings


# ============================================================
# COMMAND HANDLER
# ============================================================

def run_command(args) -> None:
    if args.command == "update":
        count = apply_database_sql(reset=False)
        updated = check_inventory()
        print(f"[DATABASE] Updated from database.sql: {count} statements")
        print(f"[INVENTORY] Recalculated, {updated} drink rows refreshed")

    elif args.command == "reset":
        count = apply_database_sql(reset=True)
        updated = check_inventory()
        print(f"[DATABASE] Reset from database.sql: {count} statements")
        print(f"[INVENTORY] Recalculated, {updated} drink rows refreshed")

    elif args.command == "check-inventory":
        updated = check_inventory()
        print(f"[INVENTORY] Recalculated, {updated} drink rows refreshed")

    elif args.command == "update-drinks":
        updated_count = update_drinks_inventory()
        print(f"[INVENTORY] Updated {updated_count} drink rows")

    elif args.command == "recalculate-thresholds":
        recalculate_thresholds_in_database()
        updated = check_inventory()
        print("[THRESHOLD] Recalculated")
        print(f"[INVENTORY] Recalculated, {updated} drink rows refreshed")

    elif args.command == "set-stock":
        remaining = set_inventory(args.ingredient_id, args.gram)
        print(f"[INVENTORY] ingredient_id={args.ingredient_id}: {remaining}g")

    elif args.command == "add-stock":
        remaining = add_inventory(args.ingredient_id, args.gram)
        print(f"[INVENTORY] ingredient_id={args.ingredient_id}: {remaining}g")

    elif args.command == "subtract-stock":
        remaining = subtract_inventory(args.ingredient_id, args.gram)
        print(f"[INVENTORY] ingredient_id={args.ingredient_id}: {remaining}g")

    elif args.command == "consume-drink":
        consume_drink(args.drink_id, args.quantity)
        print(
            f"[CONSUME] drink_id={args.drink_id}, "
            f"quantity={args.quantity}"
        )

    elif args.command == "machine-update":
        readings = read_machine_file(args.file)
        update_inventory_batch(readings, mode=args.mode)
        print(
            f"[MACHINE] {len(readings)} ingredients updated "
            f"with mode={args.mode}"
        )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        run_command(args)
    except (Error, ValueError, FileNotFoundError, json.JSONDecodeError) as error:
        print(f"[ERROR] {error}")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
