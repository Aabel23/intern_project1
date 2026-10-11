"""Small helpers shared by the services: hardware slot names, numbers and
JSON out of MySQL rows.
"""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# HARDWARE SLOTS
#
# ingredient.gpio names where an ingredient physically lives, and it names
# two different things depending on the ingredient's type:
#
#     PUMP    a BCM pin driving a pump          -> "G26", "G15"
#     MANUAL  a position on the button panel    -> "P01", "P06"
#
# It used to be a bare INT, which meant a 1 in that column could be pin 1 or
# panel position 1 and nothing in the value said which. The prefix is what
# makes a slot readable on its own -- in a log, in a query, on a
# screen -- without having to fetch the row's type first to interpret it.
#
# Two digits, zero padded, so a column of them lines up.
# ---------------------------------------------------------------------------

GPIO_PREFIX_PUMP = "G"      # a BCM pin
GPIO_PREFIX_MANUAL = "P"    # a panel position


def gpio_slot(number, ingredient_type: str) -> str | None:
    """Format a raw number as a slot: (26, 'PUMP') -> 'G26'."""
    if number is None or str(number).strip() == "":
        return None

    prefix = (GPIO_PREFIX_PUMP
              if str(ingredient_type).upper() == "PUMP"
              else GPIO_PREFIX_MANUAL)

    return f"{prefix}{int(number):02d}"


def gpio_number(slot) -> int | None:
    """The number inside a slot: 'G26' -> 26, 'P01' -> 1, None -> None.

    Accepts a bare number too, so code that has not been migrated yet -- or
    a database that has not -- keeps working instead of failing on a value
    that is perfectly readable.
    """
    if slot is None:
        return None

    text = str(slot).strip()

    if not text:
        return None

    if text[0].upper() in (GPIO_PREFIX_PUMP, GPIO_PREFIX_MANUAL):
        text = text[1:]

    try:
        return int(text)
    except ValueError:
        return None


def mysql_number(value: Any) -> int | float:
    """Turn a MySQL Decimal into a plain int or float for JSON."""
    if value is None:
        return 0.0

    if isinstance(value, Decimal):
        value = float(value)

    if isinstance(value, float) and value.is_integer():
        return int(value)

    return value


def normalize_mysql_row(row: dict[str, Any]) -> dict[str, Any]:
    """Apply mysql_number to every value in one row."""
    return {
        key: mysql_number(value)
        for key, value in row.items()
    }


def write_json_atomic(path: Path, data: Any) -> None:
    """Write JSON through a temporary file so readers never see half."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    temporary_path.replace(path)
