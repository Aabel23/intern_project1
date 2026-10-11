# ============================================================
# INVENTORY CHECK AND UPDATE SERVICE
# ============================================================

from decimal import Decimal, InvalidOperation
from typing import Literal, Mapping

from mysql.connector import Error

from configuration.machine import PIN_TO_PUMP

from database.core.connection import close_database_resources, connect_database
from database.core.helpers import gpio_number, mysql_number
from database.schema.apply import recalculate_thresholds


UpdateMode = Literal["set", "add", "subtract"]

DRINK_INSTOCK_UPDATE = """
    UPDATE drink AS drink

    LEFT JOIN (
        SELECT
            recipe.drink_id,
            COUNT(recipe.ingredient_id) AS ingredient_count,
            MIN(
                CASE
                    WHEN ingredient.in_stock = TRUE THEN 1
                    ELSE 0
                END
            ) AS every_ingredient_instock

        FROM recipe AS recipe

        LEFT JOIN ingredient AS ingredient
            ON ingredient.ingredient_id = recipe.ingredient_id

        GROUP BY recipe.drink_id
    ) AS stock
        ON stock.drink_id = drink.drink_id

    SET drink.in_stock = IF(
        COALESCE(stock.ingredient_count, 0) > 0
        AND COALESCE(stock.every_ingredient_instock, 0) = 1,
        TRUE,
        FALSE
    )
"""

DRINK_REQUIREMENTS_QUERY = """
    SELECT
        drink.drink_name,
        ingredient.ingredient_id,
        ingredient.ingredient_name,
        SUM(recipe.target_gram) * %s AS required_gram

    FROM drink AS drink

    JOIN recipe AS recipe
        ON recipe.drink_id = drink.drink_id

    JOIN ingredient AS ingredient
        ON ingredient.ingredient_id = recipe.ingredient_id

    WHERE drink.drink_id = %s

    GROUP BY
        drink.drink_name,
        ingredient.ingredient_id,
        ingredient.ingredient_name

    ORDER BY ingredient.ingredient_id
"""


# ============================================================
# DRINK AVAILABILITY
# ============================================================

def refresh_drink_instock(cursor) -> int:
    """Update drink.in_stock inside the caller's transaction."""

    cursor.execute(DRINK_INSTOCK_UPDATE)
    return max(int(cursor.rowcount or 0), 0)


def update_drinks_inventory() -> int:
    """Recalculate drink.in_stock from the ingredient levels.

    The store screen reads store_gui/menu-data.js, not this table; see
    publish_store_menu().
    """

    conn = connect_database()
    cursor = conn.cursor(dictionary=True)

    try:
        conn.start_transaction()
        updated_count = refresh_drink_instock(cursor)
        conn.commit()
    except Error:
        conn.rollback()
        raise
    finally:
        close_database_resources(cursor, conn)

    return updated_count


# ============================================================
# VALIDATION
# ============================================================

def to_decimal(value, field_name: str) -> Decimal:
    try:
        result = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"{field_name} must be a valid number") from error

    return result


def require_non_negative(value, field_name: str) -> Decimal:
    result = to_decimal(value, field_name)

    if result < 0:
        raise ValueError(f"{field_name} cannot be negative")

    return result


def require_positive(value, field_name: str) -> Decimal:
    result = to_decimal(value, field_name)

    if result <= 0:
        raise ValueError(f"{field_name} must be greater than 0")

    return result


# ============================================================
# INTERNAL HELPERS
# ============================================================

def lock_ingredient(cursor, ingredient_id: int) -> dict:
    cursor.execute(
        """
        SELECT
            ingredient_id,
            ingredient_name,
            amount,
            threshold_gram,
            in_stock

        FROM ingredient

        WHERE ingredient_id = %s

        FOR UPDATE
        """,
        (ingredient_id,),
    )

    ingredient = cursor.fetchone()

    if ingredient is None:
        raise ValueError(
            f"Ingredient not found: ingredient_id={ingredient_id}"
        )

    return ingredient


def publish_store_menu() -> str:
    """Rebuild store_gui/menu-data.js so the customer screen agrees.

    WHY THIS IS HERE
        The customer screen has no server and cannot query MySQL. It reads
        a snapshot file, and that file IS the menu as far as any customer
        is concerned. drink.in_stock going false changes nothing they can
        see until the snapshot is rewritten.

        A stock level falling below its threshold is not an edit by a
        person -- it happens while the machine pours -- so it must be
        rebuilt here, or the screen keeps selling a drink the machine can
        no longer make.

    Returns a sentence if it could not be written, "" if it worked. It
    never raises: the stock change is already committed, and failing to
    repaint a screen must not look like a failure to record the pour.
    """
    try:
        from store_gui.sync_menu import publish_menu
    except ImportError as error:      # a database-only install
        return f"store menu not rebuilt (store_gui unavailable): {error}"

    try:
        publish_menu()
        return ""
    except Exception as error:        # noqa: BLE001 - reported, never raised
        return f"store menu not rebuilt: {error}"


def sync_inventory_outputs() -> None:
    """Bring everything downstream of a stock change back in line.

    Two things go stale when stock moves: drink.in_stock in the database,
    and the snapshot the customer screen reads. Both are refreshed here,
    which is the one place every stock change already passes through.
    """
    update_drinks_inventory()

    problem = publish_store_menu()

    if problem:
        print(f"[database] {problem}")


# ============================================================
# CHECK INVENTORY
# ============================================================

def check_inventory() -> int:
    """Recalculate thresholds and drink stock. Returns rows updated."""
    conn = connect_database()
    cursor = conn.cursor(dictionary=True)

    try:
        recalculate_thresholds(cursor)
        updated = refresh_drink_instock(cursor)
        conn.commit()
        return updated

    except Error:
        conn.rollback()
        raise

    finally:
        close_database_resources(cursor, conn)


# ============================================================
# SINGLE INGREDIENT UPDATE
# ============================================================

def update_ingredient_inventory(
    ingredient_id: int,
    gram,
    mode: UpdateMode = "set",
    refresh_stock: bool = True,
) -> Decimal:
    if mode == "set":
        amount = require_non_negative(gram, "gram")
    elif mode in {"add", "subtract"}:
        amount = require_positive(gram, "gram")
    else:
        raise ValueError(f"Unsupported update mode: {mode}")

    conn = connect_database()
    cursor = conn.cursor(dictionary=True)

    try:
        conn.start_transaction()
        ingredient = lock_ingredient(cursor, ingredient_id)
        current = ingredient["amount"]

        if mode == "set":
            new_inventory = amount
        elif mode == "add":
            new_inventory = current + amount
        else:
            if current < amount:
                raise ValueError(
                    f"Not enough {ingredient['ingredient_name']}: "
                    f"required={amount}g, available={current}g"
                )
            new_inventory = current - amount

        cursor.execute(
            """
            UPDATE ingredient
            SET amount = %s
            WHERE ingredient_id = %s
            """,
            (new_inventory, ingredient_id),
        )

        conn.commit()

    except (Error, ValueError):
        conn.rollback()
        raise

    finally:
        close_database_resources(cursor, conn)

    if refresh_stock:
        sync_inventory_outputs()

    return new_inventory


def set_inventory(ingredient_id: int, gram) -> Decimal:
    return update_ingredient_inventory(
        ingredient_id,
        gram,
        mode="set",
    )


def add_inventory(ingredient_id: int, gram) -> Decimal:
    return update_ingredient_inventory(
        ingredient_id,
        gram,
        mode="add",
    )


def subtract_inventory(ingredient_id: int, gram) -> Decimal:
    return update_ingredient_inventory(
        ingredient_id,
        gram,
        mode="subtract",
    )


# ============================================================
# BATCH UPDATE FOR FUTURE MACHINE CHECKER
# ============================================================

def update_inventory_batch(
    readings: Mapping[int, int | float | Decimal],
    mode: UpdateMode = "set",
    refresh_stock: bool = True,
) -> None:
    """
    Hook dành cho file kiểm tra kho từ máy pha.

    readings ví dụ:
        {1: 7500, 2: 4200} với mode="set"
        {1: 120, 2: 80} với mode="subtract"
    """

    if not readings:
        raise ValueError("readings cannot be empty")

    conn = connect_database()
    cursor = conn.cursor(dictionary=True)

    try:
        conn.start_transaction()

        for ingredient_id in sorted(readings):
            amount = readings[ingredient_id]

            if mode == "set":
                amount = require_non_negative(amount, "gram")
            elif mode in {"add", "subtract"}:
                amount = require_positive(amount, "gram")
            else:
                raise ValueError(f"Unsupported update mode: {mode}")

            ingredient = lock_ingredient(cursor, ingredient_id)
            current = ingredient["amount"]

            if mode == "set":
                new_inventory = amount
            elif mode == "add":
                new_inventory = current + amount
            else:
                if current < amount:
                    raise ValueError(
                        f"Not enough {ingredient['ingredient_name']}: "
                        f"required={amount}g, available={current}g"
                    )
                new_inventory = current - amount

            cursor.execute(
                """
                UPDATE ingredient
                SET amount = %s
                WHERE ingredient_id = %s
                """,
                (new_inventory, ingredient_id),
            )

        conn.commit()

    except (Error, ValueError):
        conn.rollback()
        raise

    finally:
        close_database_resources(cursor, conn)

    if refresh_stock:
        sync_inventory_outputs()


# ============================================================
# CONSUME STOCK BY DRINK RECIPE
# ============================================================

def consume_drink(
    drink_id: int,
    quantity: int = 1,
    refresh_stock: bool = True,
) -> None:
    try:
        normalized_drink_id = int(drink_id)
    except (TypeError, ValueError) as error:
        raise ValueError("drink_id must be an integer") from error

    if normalized_drink_id <= 0:
        raise ValueError("drink_id must be greater than 0")

    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    conn = connect_database()
    cursor = conn.cursor(dictionary=True)

    try:
        conn.start_transaction()

        cursor.execute(
            DRINK_REQUIREMENTS_QUERY,
            (quantity, normalized_drink_id),
        )

        requirements = cursor.fetchall()

        if not requirements:
            raise ValueError(
                f"Drink or recipe not found: drink_id={normalized_drink_id}"
            )

        ingredient_ids = [
            row["ingredient_id"]
            for row in requirements
        ]
        placeholders = ", ".join(["%s"] * len(ingredient_ids))

        cursor.execute(
            f"""
            SELECT
                ingredient_id,
                ingredient_name,
                amount,
                threshold_gram,
                in_stock

            FROM ingredient

            WHERE ingredient_id IN ({placeholders})

            ORDER BY ingredient_id

            FOR UPDATE
            """,
            tuple(ingredient_ids),
        )

        stock_by_id = {
            row["ingredient_id"]: row
            for row in cursor.fetchall()
        }

        shortages: list[str] = []

        for requirement in requirements:
            stock = stock_by_id[requirement["ingredient_id"]]

            if not bool(stock["in_stock"]):
                shortages.append(
                    f"{stock['ingredient_name']} is below threshold"
                )
            elif stock["amount"] < requirement["required_gram"]:
                shortages.append(
                    f"{stock['ingredient_name']}: "
                    f"required={requirement['required_gram']}g, "
                    f"available={stock['amount']}g"
                )

        if shortages:
            raise ValueError(
                "Drink cannot be produced: " + "; ".join(shortages)
            )

        for requirement in requirements:
            cursor.execute(
                """
                UPDATE ingredient
                SET amount = amount - %s
                WHERE ingredient_id = %s
                """,
                (
                    requirement["required_gram"],
                    requirement["ingredient_id"],
                ),
            )

        conn.commit()

    except (Error, ValueError):
        conn.rollback()
        raise

    finally:
        close_database_resources(cursor, conn)

    if refresh_stock:
        sync_inventory_outputs()



# ============================================================
# CONSUMPTION FROM A COMPLETED MACHINE ORDER
# ============================================================

def consume_recipe_usage(
    usage: Mapping[int, int | float | Decimal],
    refresh_stock: bool = True,
) -> None:
    """Subtract actual pump usage in one database transaction."""
    normalized_usage: dict[int, Decimal] = {}

    for raw_ingredient_id, raw_gram in usage.items():
        try:
            ingredient_id = int(raw_ingredient_id)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Invalid ingredient_id: {raw_ingredient_id!r}"
            ) from error

        if ingredient_id <= 0:
            raise ValueError(
                f"ingredient_id must be greater than 0: {ingredient_id}"
            )

        amount = require_positive(
            raw_gram,
            f"ingredient {ingredient_id} gram",
        )
        normalized_usage[ingredient_id] = (
            normalized_usage.get(ingredient_id, Decimal("0.00"))
            + amount
        )

    conn = connect_database()
    cursor = conn.cursor(dictionary=True)

    try:
        conn.start_transaction()

        for ingredient_id, amount in sorted(normalized_usage.items()):
            ingredient = lock_ingredient(
                cursor,
                ingredient_id,
            )
            current = to_decimal(
                ingredient["amount"],
                "amount",
            )

            if current < amount:
                raise ValueError(
                    f"Not enough {ingredient['ingredient_name']}: "
                    f"required={amount}g, available={current}g"
                )

            cursor.execute(
                """
                UPDATE ingredient
                SET amount = amount - %s
                WHERE ingredient_id = %s
                """,
                (
                    amount,
                    ingredient_id,
                ),
            )

        conn.commit()

    except (Error, TypeError, ValueError):
        conn.rollback()
        raise

    finally:
        close_database_resources(cursor, conn)

    if refresh_stock:
        sync_inventory_outputs()


# ============================================================
# STOCK TAB OF THE MACHINE (machine/ingredient_sync)
# ============================================================

# What a container holds when nobody has declared ingredient.max_gram.
DEFAULT_MAX_GRAM = Decimal("10000")


def max_gram_or_default(raw) -> Decimal:
    return DEFAULT_MAX_GRAM if raw is None else Decimal(raw)


def stock_order(row: dict) -> tuple:
    """Pumps first in pump order, then the manual panel, then the rest."""
    if row["type"] == "PUMP":
        return (0, row["pump_no"] if row["pump_no"] is not None else 900,
                row["ingredient_id"])

    slot = gpio_number(row["gpio"])
    return (1, slot if slot is not None else 900, row["ingredient_id"])


def list_ingredients() -> list[dict]:
    """Every ingredient, ordered the way the machine is laid out."""
    conn = connect_database()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                ingredient.ingredient_id,
                ingredient.ingredient_name,
                ingredient.type,
                ingredient.data_type,
                ingredient.amount,
                ingredient.threshold_gram,
                ingredient.max_gram,
                ingredient.gpio,
                ingredient.in_stock,
                COUNT(DISTINCT recipe.drink_id) AS used_in

            FROM ingredient

            LEFT JOIN recipe
                ON recipe.ingredient_id = ingredient.ingredient_id

            GROUP BY ingredient.ingredient_id
            """
        )
        rows = cursor.fetchall()
    finally:
        close_database_resources(cursor, conn)

    ingredients = [
        {
            "ingredient_id": int(row["ingredient_id"]),
            "name": row["ingredient_name"],
            "type": row["type"],
            "data_type": row["data_type"],
            "amount": mysql_number(row["amount"]),
            "threshold_gram": mysql_number(row["threshold_gram"]),
            "max_gram": mysql_number(max_gram_or_default(row["max_gram"])),
            # False when max_gram above is DEFAULT_MAX_GRAM, a guess.
            "max_set": row["max_gram"] is not None,
            "gpio": row["gpio"],
            "pump_no": (
                PIN_TO_PUMP.get(gpio_number(row["gpio"]))
                if row["type"] == "PUMP"
                else None
            ),
            "in_stock": bool(row["in_stock"]),
            "used_in": int(row["used_in"]),
        }
        for row in rows
    ]

    return sorted(ingredients, key=stock_order)


def refill(target, value) -> dict:
    """Put stock back: target is an ingredient id or "all", value is
    "full" (fill to max_gram) or the grams now in the container.

    One transaction, so a refill of "all" either happens or does not.
    in_stock is set by the ingredient triggers, so it is read back after
    the commit rather than assumed. The caller rebuilds the store menu.
    """
    if target == "all" and value != "full":
        raise ValueError("Nạp tất cả chỉ nhận value = \"full\"")

    if value != "full":
        value = require_non_negative(value, "gram")

    conn = connect_database()
    cursor = conn.cursor(dictionary=True)

    try:
        conn.start_transaction()

        query = "SELECT ingredient_id, ingredient_name, max_gram FROM ingredient"
        params: tuple = ()

        if target != "all":
            query += " WHERE ingredient_id = %s"
            params = (int(target),)

        cursor.execute(query + " ORDER BY ingredient_id FOR UPDATE", params)
        rows = cursor.fetchall()

        if not rows:
            raise ValueError(f"Ingredient not found: ingredient_id={target}")

        filled = []

        for row in rows:
            amount = (max_gram_or_default(row["max_gram"])
                      if value == "full" else value)
            cursor.execute(
                "UPDATE ingredient SET amount = %s WHERE ingredient_id = %s",
                (amount, row["ingredient_id"]),
            )
            filled.append({
                "ingredient_id": int(row["ingredient_id"]),
                "name": row["ingredient_name"],
                "max_set": row["max_gram"] is not None,
            })

        conn.commit()

        cursor.execute(
            "SELECT ingredient_id, amount, in_stock FROM ingredient"
        )
        saved = {int(r["ingredient_id"]): r for r in cursor.fetchall()}

    except (Error, ValueError):
        conn.rollback()
        raise

    finally:
        close_database_resources(cursor, conn)

    for row in filled:
        row["amount"] = mysql_number(saved[row["ingredient_id"]]["amount"])
        row["in_stock"] = bool(saved[row["ingredient_id"]]["in_stock"])

    return {"filled": filled, "count": len(filled)}
