"""Open the database, bring its schema up to date, and share helpers.

WHAT THIS FILE IS
    The only place that connects to MySQL and the only place that changes
    its shape. Every other module in database/ receives a cursor from
    here and assumes the schema is already current.

THE SCHEMA IS DESCRIBED BY A FILE, NOT BY CODE
    database/database.sql is the source of truth for the structure and
    the default data. It is written to be re-runnable: CREATE TABLE IF
    NOT EXISTS, INSERT ... ON DUPLICATE KEY UPDATE, and ALTER statements
    whose "already applied" errors are ignored (IGNORED_SCHEMA_ERROR_CODES).

THE FLOW OF apply_database_sql()
    1.  Create the database if it does not exist. With reset=True the old
        one is dropped first and step 2 is skipped.
    2.  Run the migrations, oldest first, each a no-op once applied:
            migrate_monitoring_schema()   instock -> in_stock, and the
                                          old ingredient_pump_mapping
            migrate_legacy_recipe_schema() merge the old recipe header
                                          and detail tables into one
            migrate_v2_schema()           all_drink/all_recipe/
                                          all_ingredient -> drink/recipe/
                                          ingredient, inventory_gram ->
                                          amount, and fold the GPIO
                                          mapping table into ingredient
    3.  Execute every statement in database.sql in order.
    4.  Apply any numbered migration in database/migrations/ this
        database has not recorded yet -- see database/migrate.py.
    5.  Commit, or roll back the whole thing on any error.

    The step-2 migrations deliberately speak the OLD table names: they run
    before the rename and would find nothing afterwards, which is exactly
    what makes them safe to run again.

WHERE A NEW SCHEMA CHANGE GOES -- THE ONE RULE
    In database/migrations/, as a numbered file. NOT in database.sql.

    That is a change of habit, so it is worth saying why. Adding a column
    used to mean editing database.sql *and* writing an ALTER beside it:
    CREATE TABLE IF NOT EXISTS does nothing to a table that already
    exists, so the edit alone reached new machines and never reached the
    ones already running. That is precisely why thirteen migrate_*.sql
    files accumulated in database/ -- each one is the second half of an
    edit whose first half is in database.sql.

    A numbered migration is both halves at once. It runs on a fresh
    machine and on a five-month-old one, exactly once each, and the row it
    leaves behind says so.

    database.sql is therefore now a BASELINE: the schema as of 0001, not
    the schema as of today. To read the current shape of a table, read
    database.sql and then the migrations after it. When that becomes more
    reading than it is worth, the fix is to squash -- regenerate
    database.sql from a fully migrated database and move the baseline
    forward -- not to start editing both places again.

TWO KINDS OF MIGRATION NOW, AND THE DIFFERENCE MATTERS
    Step 2 is the old kind: a Python function that inspects the database,
    decides whether its change is already in place, and does nothing if it
    is. Safe to run forever, and it leaves no trace -- which is exactly the
    problem. Nothing can answer "what shape is this machine in?".

    Step 4 is the new kind: a numbered file, applied once, recorded in
    schema_migration. Ask that table and it tells you. That is what the
    fleet agent reads before it trusts anything else it reads.

    The step-2 functions are not being converted. They rename tables that
    have not existed since before this project had a second machine, and
    replaying that history under new numbers would put false dates in a
    logbook on its very first page. They stay as they are, inside the
    baseline. database/MIGRATIONS.md has the same reasoning for the
    thirteen hand-run .sql files.

WHY migrate_v2_schema DOES MORE THAN RENAME
    MySQL refuses to rename a column a CHECK constraint reads, and the
    old triggers read all_ingredient.inventory_gram, so both are dropped
    before the rename and rebuilt afterwards -- the triggers by
    database.sql, the constraints by the migration itself, because
    CREATE TABLE IF NOT EXISTS cannot add them to a table that exists.
    DDL is not transactional in MySQL, so the migration is written to
    finish correctly from a half-applied state.

ALSO HERE
    Number and JSON helpers every exporter shares: mysql_number() turns
    Decimal into int or float, write_json_atomic() writes through a
    temporary file so no reader ever sees half a document.
"""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

import mysql.connector
from mysql.connector import Error

try:
    from .config import DB_CONFIG, DB_NAME, SERVER_CONFIG, SQL_FILE
except ImportError:
    from config import DB_CONFIG, DB_NAME, SERVER_CONFIG, SQL_FILE


IGNORED_SCHEMA_ERROR_CODES = {
    1060,  # Duplicate column name on repeated migration.
    1061,  # Duplicate key name on repeated migration.
    1091,  # Column/index already absent during SKU removal.
    3821,  # CHECK constraint already absent when dropping option_*.
    # Duplicate FOREIGN KEY name -- what "ADD CONSTRAINT fk_drink_glass"
    # raises the second time the file runs. 1061 is the same statement
    # about an index and was already here; a named FK reports itself
    # under its own code instead, and without it every re-run of
    # database.sql stopped at the glass constraint and never reached the
    # ALTERs below it.
    1826,
}


# ============================================================
# CONNECTIONS
# ============================================================

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
# makes a slot readable on its own -- in a log, in a query, on the admin
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


def connect_server():
    """Connect to the MySQL server without selecting a database."""
    return mysql.connector.connect(**SERVER_CONFIG)


def connect_database():
    """Connect to the configured beverage database."""
    return mysql.connector.connect(**DB_CONFIG)


# ============================================================
# SQL FILE PARSER
# ============================================================

def split_sql_statements(sql_text: str) -> list[str]:
    """Tách câu lệnh SQL, không cắt dấu ; nằm trong chuỗi."""

    statements: list[str] = []
    buffer: list[str] = []

    in_single_quote = False
    in_double_quote = False
    in_backtick = False
    in_line_comment = False
    in_block_comment = False

    index = 0
    length = len(sql_text)

    while index < length:
        char = sql_text[index]
        next_char = sql_text[index + 1] if index + 1 < length else ""

        if in_line_comment:
            if char == "\n":
                in_line_comment = False
                buffer.append(char)
            index += 1
            continue

        if in_block_comment:
            if char == "*" and next_char == "/":
                in_block_comment = False
                index += 2
            else:
                index += 1
            continue

        if not (in_single_quote or in_double_quote or in_backtick):
            if char == "#":
                in_line_comment = True
                index += 1
                continue

            if char == "-" and next_char == "-":
                following = sql_text[index + 2] if index + 2 < length else " "
                if following.isspace():
                    in_line_comment = True
                    index += 2
                    continue

            if char == "/" and next_char == "*":
                in_block_comment = True
                index += 2
                continue

        if char == "'" and not (in_double_quote or in_backtick):
            escaped = index > 0 and sql_text[index - 1] == "\\"
            if not escaped:
                in_single_quote = not in_single_quote

        elif char == '"' and not (in_single_quote or in_backtick):
            escaped = index > 0 and sql_text[index - 1] == "\\"
            if not escaped:
                in_double_quote = not in_double_quote

        elif char == "`" and not (in_single_quote or in_double_quote):
            in_backtick = not in_backtick

        if (
            char == ";"
            and not in_single_quote
            and not in_double_quote
            and not in_backtick
        ):
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer.clear()
        else:
            buffer.append(char)

        index += 1

    remaining = "".join(buffer).strip()
    if remaining:
        statements.append(remaining)

    return statements


def read_sql_file(sql_file: Path = SQL_FILE) -> list[str]:
    """Read database.sql and split it into executable statements."""
    if not sql_file.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_file}")

    sql_text = sql_file.read_text(encoding="utf-8")
    return split_sql_statements(sql_text)


# ============================================================
# CREATE / UPDATE DATABASE FROM database.sql
# ============================================================

def _get_table_columns(cursor, table_name: str) -> set[str]:
    """Return the column names of one table, empty if it is absent."""
    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = %s
        """,
        (DB_NAME, table_name),
    )
    return {
        row[0] if not isinstance(row, dict) else row["COLUMN_NAME"]
        for row in cursor.fetchall()
    }


def migrate_monitoring_schema(cursor) -> bool:
    """Rename legacy monitoring columns without losing stored values."""
    changed = False
    drink_columns = _get_table_columns(cursor, "all_drink")

    if "instock" in drink_columns and "in_stock" not in drink_columns:
        cursor.execute(
            """
            ALTER TABLE all_drink
            CHANGE COLUMN instock in_stock
                BOOLEAN NOT NULL DEFAULT TRUE
            """
        )
        changed = True
    elif "instock" in drink_columns and "in_stock" in drink_columns:
        cursor.execute("UPDATE all_drink SET in_stock = instock")
        cursor.execute("ALTER TABLE all_drink DROP COLUMN instock")
        changed = True

    legacy_mapping_columns = _get_table_columns(
        cursor,
        "ingredient_pump_mapping",
    )
    gpio_mapping_columns = _get_table_columns(
        cursor,
        "ingredient_gpio_mapping",
    )

    if "source" in legacy_mapping_columns and "gpio" not in legacy_mapping_columns:
        cursor.execute(
            """
            ALTER TABLE ingredient_pump_mapping
            CHANGE COLUMN `source` gpio INT NOT NULL
            """
        )
        changed = True
    elif "source" in legacy_mapping_columns and "gpio" in legacy_mapping_columns:
        cursor.execute(
            "UPDATE ingredient_pump_mapping SET gpio = `source`"
        )
        cursor.execute(
            "ALTER TABLE ingredient_pump_mapping DROP COLUMN `source`"
        )
        changed = True

    if "pump_no" in legacy_mapping_columns:
        cursor.execute(
            "ALTER TABLE ingredient_pump_mapping DROP COLUMN pump_no"
        )
        changed = True

    if legacy_mapping_columns and not gpio_mapping_columns:
        cursor.execute(
            "RENAME TABLE ingredient_pump_mapping TO ingredient_gpio_mapping"
        )
        gpio_mapping_columns = legacy_mapping_columns
        changed = True
    elif legacy_mapping_columns and gpio_mapping_columns:
        cursor.execute(
            """
            INSERT IGNORE INTO ingredient_gpio_mapping (ingredient_id, gpio)
            SELECT ingredient_id, gpio
            FROM ingredient_pump_mapping
            """
        )
        cursor.execute("DROP TABLE ingredient_pump_mapping")
        changed = True

    if "ingredient_name" in gpio_mapping_columns:
        cursor.execute(
            "ALTER TABLE ingredient_gpio_mapping DROP COLUMN ingredient_name"
        )
        changed = True

    return changed


def _table_exists(cursor, table_name: str) -> bool:
    """Return whether one table exists in the configured database."""
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = %s
        """,
        (DB_NAME, table_name),
    )
    row = cursor.fetchone()
    value = row["COUNT(*)"] if isinstance(row, dict) else row[0]
    return int(value) > 0


V2_TABLE_RENAMES = (
    ("all_drink", "drink"),
    ("all_recipe", "recipe"),
    ("all_ingredient", "ingredient"),
)

# Named so a migrated database ends up identical to a fresh install.
# (constraint name, clause, the columns the clause reads).
#
# The third element is not decoration. These are installed on a table that
# already exists, and some of the columns they read are themselves added by
# an ALTER in database.sql -- which runs *after* the migrations. Adding a
# constraint over a column that is not there yet fails with error 1054, so
# each one waits until its columns exist. See ensure_ingredient_checks().
V2_INGREDIENT_CHECKS = (
    ("ck_ingredient_amount", "amount >= 0", ("amount",)),
    ("ck_ingredient_threshold", "threshold_gram >= 0", ("threshold_gram",)),
    # NULL is "nobody has declared how big this container is" and is
    # allowed; 0 is not, because a zero-sized container divides by zero on
    # the stock screen and turns "fill it" into "empty it".
    ("ck_ingredient_max_gram",
     "max_gram IS NULL OR max_gram > 0", ("max_gram",)),
    # A slot is a letter and digits now, not a number -- "gpio >= 0" would
    # refuse every value. See gpio_slot() at the top of this file.
    ("ck_ingredient_gpio",
     "gpio IS NULL OR gpio REGEXP '^[GP][0-9]+$'", ("gpio",)),
    ("ck_ingredient_type", "type IN ('PUMP', 'MANUAL')", ("type",)),
    (
        "ck_ingredient_data_type",
        "data_type IN ('boolean', 'percentage', 'weight')",
        ("data_type",),
    ),
)

# data_type 'number' was renamed to 'weight' when the QR payload protocol
# gained a weight type (scan/qr_payload.py). Both the constraint and the
# rows that use it have to move together.
LEGACY_DATA_TYPE = "number"
RENAMED_DATA_TYPE = "weight"


def _table_indexes(cursor, table_name: str) -> set[str]:
    """Return the index names defined on one table."""
    cursor.execute(
        """
        SELECT DISTINCT INDEX_NAME
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = %s
        """,
        (DB_NAME, table_name),
    )
    return {
        (row["INDEX_NAME"] if isinstance(row, dict) else row[0])
        for row in cursor.fetchall()
    }


def _check_constraints(cursor, table_name: str) -> dict[str, str]:
    """Return the CHECK constraints of one table, by name."""
    cursor.execute(
        """
        SELECT
            checks.CONSTRAINT_NAME AS name,
            checks.CHECK_CLAUSE AS clause
        FROM information_schema.CHECK_CONSTRAINTS AS checks
        JOIN information_schema.TABLE_CONSTRAINTS AS constraints
            ON constraints.CONSTRAINT_SCHEMA = checks.CONSTRAINT_SCHEMA
           AND constraints.CONSTRAINT_NAME = checks.CONSTRAINT_NAME
        WHERE checks.CONSTRAINT_SCHEMA = %s
          AND constraints.TABLE_NAME = %s
        """,
        (DB_NAME, table_name),
    )
    return {
        (row["name"] if isinstance(row, dict) else row[0]): (
            row["clause"] if isinstance(row, dict) else row[1]
        )
        for row in cursor.fetchall()
    }


def ensure_ingredient_checks(cursor) -> bool:
    """Install the named CHECK constraints on ingredient. Returns True if any
    were added.

    CREATE TABLE IF NOT EXISTS cannot add a constraint to a table that is
    already there, so they are installed by name here instead.

    A constraint whose columns do not exist yet is skipped rather than
    attempted: the option_* columns arrive via an ALTER in database.sql,
    which runs after the migrations, so on the very first upgrade the
    columns appear only later in the same run. apply_database_sql() calls
    this again once the statements have executed, and that second call
    installs them.
    """
    if not _table_exists(cursor, "ingredient"):
        return False

    columns = _get_table_columns(cursor, "ingredient")
    existing_checks = _check_constraints(cursor, "ingredient")
    changed = False

    for constraint_name, clause, required_columns in V2_INGREDIENT_CHECKS:
        if constraint_name in existing_checks:
            continue

        if not set(required_columns) <= set(columns):
            continue

        cursor.execute(
            f"ALTER TABLE ingredient ADD CONSTRAINT {constraint_name} "
            f"CHECK ({clause})"
        )
        changed = True

    return changed


def migrate_v2_schema(cursor) -> bool:
    """Rename the all_* tables and fold the GPIO mapping into ingredient.

    The old triggers read all_ingredient.inventory_gram, so they are
    dropped before that column is renamed. database.sql recreates them
    against the new column straight after this migration.
    """
    changed = False

    for trigger_name in (
        "trg_all_ingredient_before_insert",
        "trg_all_ingredient_before_update",
    ):
        cursor.execute(
            f"DROP TRIGGER IF EXISTS {trigger_name}"
        )

    for old_name, new_name in V2_TABLE_RENAMES:
        if _table_exists(cursor, old_name) and not _table_exists(
            cursor,
            new_name,
        ):
            cursor.execute(
                f"RENAME TABLE {old_name} TO {new_name}"
            )
            changed = True

    if not _table_exists(cursor, "ingredient"):
        return changed

    ingredient_columns = _get_table_columns(cursor, "ingredient")

    if (
        "inventory_gram" in ingredient_columns
        and "amount" not in ingredient_columns
    ):
        # MySQL refuses to rename a column a CHECK constraint reads, so
        # every constraint over inventory_gram goes first.
        for constraint_name, clause in _check_constraints(
            cursor,
            "ingredient",
        ).items():
            if "inventory_gram" in clause:
                cursor.execute(
                    "ALTER TABLE ingredient "
                    f"DROP CHECK {constraint_name}"
                )

        cursor.execute(
            """
            ALTER TABLE ingredient
            CHANGE COLUMN inventory_gram
                amount DECIMAL(10,2) NOT NULL DEFAULT 0
            """
        )
        ingredient_columns.add("amount")
        changed = True

    for column_name, definition in (
        ("type", "VARCHAR(16) NOT NULL DEFAULT 'PUMP'"),
        ("data_type", "VARCHAR(16) NOT NULL DEFAULT 'number'"),
        ("gpio", "INT NULL"),
    ):
        if column_name not in ingredient_columns:
            cursor.execute(
                f"ALTER TABLE ingredient ADD COLUMN {column_name} {definition}"
            )
            changed = True

    if _table_exists(cursor, "ingredient_gpio_mapping"):
        # Carry every wired pump across before the mapping table goes.
        cursor.execute(
            """
            UPDATE ingredient AS target
            JOIN ingredient_gpio_mapping AS mapping
                ON mapping.ingredient_id = target.ingredient_id
            SET target.gpio = mapping.gpio
            """
        )

        # An ingredient with no pump was, and stays, added by hand.
        cursor.execute(
            """
            UPDATE ingredient
            SET type = IF(gpio IS NULL, 'MANUAL', 'PUMP')
            """
        )

        cursor.execute("DROP TABLE ingredient_gpio_mapping")
        changed = True

    # Rename the data_type value 'number' to 'weight'. The old CHECK
    # constraint forbids 'weight', and MySQL enforces it during the UPDATE,
    # so the constraint has to be dropped before the rows can move. The
    # loop below then reinstalls it from V2_INGREDIENT_CHECKS with the new
    # clause -- which is also why this has to run before that loop reads
    # the existing constraint names.
    # MySQL stores a CHECK clause with its quotes backslash-escaped and a
    # charset prefix on every literal -- 'number' is held as
    # _utf8mb4\'number\' -- so the bare word is what can be matched.
    for constraint_name, clause in _check_constraints(
        cursor,
        "ingredient",
    ).items():
        if (
            constraint_name == "ck_ingredient_data_type"
            and LEGACY_DATA_TYPE in clause
        ):
            cursor.execute(
                f"ALTER TABLE ingredient DROP CHECK {constraint_name}"
            )
            changed = True

    cursor.execute(
        "UPDATE ingredient SET data_type = %s WHERE data_type = %s",
        (RENAMED_DATA_TYPE, LEGACY_DATA_TYPE),
    )

    if cursor.rowcount > 0:
        changed = True

    changed = ensure_ingredient_checks(cursor) or changed

    if "gpio" not in _get_table_columns(cursor, "ingredient"):
        return changed

    indexes = _table_indexes(cursor, "ingredient")

    # A PUMP gpio is a Raspberry Pi pin and a MANUAL gpio is a panel
    # position, so the same number can legitimately appear twice. Only
    # the pair (type, gpio) has to stay unique.
    if "gpio" in indexes:
        cursor.execute(
            "ALTER TABLE ingredient DROP INDEX gpio"
        )
        changed = True

    if "uq_ingredient_type_gpio" not in indexes:
        cursor.execute(
            "ALTER TABLE ingredient "
            "ADD UNIQUE KEY uq_ingredient_type_gpio (type, gpio)"
        )
        changed = True

    return changed


def legacy_recipe_schema_exists(cursor) -> bool:
    """Return whether both tables from the legacy recipe schema exist."""

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = 'all_recipe'
          AND COLUMN_NAME = 'recipe_id'
        """,
        (DB_NAME,),
    )
    has_legacy_recipe_id = int(cursor.fetchone()[0]) > 0

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = 'recipe_ingredient_mapping'
        """,
        (DB_NAME,),
    )
    has_legacy_mapping = int(cursor.fetchone()[0]) > 0

    return has_legacy_recipe_id and has_legacy_mapping


def migrate_legacy_recipe_schema(cursor) -> bool:
    """Merge the legacy recipe header/detail tables without losing rows."""

    if not legacy_recipe_schema_exists(cursor):
        return False

    cursor.execute("DROP TABLE IF EXISTS all_recipe_v2")

    cursor.execute(
        """
        CREATE TABLE all_recipe_v2 (
            drink_id INT NOT NULL,
            ingredient_id INT NOT NULL,
            step_no INT NOT NULL,
            target_gram DECIMAL(10,2) NOT NULL,

            PRIMARY KEY (
                drink_id,
                step_no,
                ingredient_id
            ),

            CHECK (step_no > 0),
            CHECK (target_gram > 0),

            CONSTRAINT fk_recipe_v2_drink
                FOREIGN KEY (drink_id)
                REFERENCES all_drink(drink_id)
                ON DELETE CASCADE,

            CONSTRAINT fk_recipe_v2_ingredient
                FOREIGN KEY (ingredient_id)
                REFERENCES all_ingredient(ingredient_id)
                ON DELETE RESTRICT
        ) ENGINE=InnoDB
        """
    )

    cursor.execute(
        """
        INSERT INTO all_recipe_v2 (
            drink_id,
            ingredient_id,
            step_no,
            target_gram
        )
        SELECT
            recipe.drink_id,
            mapping.ingredient_id,
            mapping.step_no,
            mapping.target_gram
        FROM all_recipe AS recipe
        JOIN recipe_ingredient_mapping AS mapping
            ON mapping.recipe_id = recipe.recipe_id
        """
    )

    cursor.execute(
        """
        RENAME TABLE
            all_recipe TO all_recipe_legacy,
            recipe_ingredient_mapping
                TO recipe_ingredient_mapping_legacy,
            all_recipe_v2 TO all_recipe
        """
    )
    cursor.execute("DROP TABLE recipe_ingredient_mapping_legacy")
    cursor.execute("DROP TABLE all_recipe_legacy")
    return True


def ensure_database_exists(reset: bool = False) -> None:
    """Create the database, dropping it first when reset is asked for."""
    conn = connect_server()
    cursor = conn.cursor()

    try:
        if reset:
            cursor.execute(f"DROP DATABASE IF EXISTS `{DB_NAME}`")

        cursor.execute(
            f"""
            CREATE DATABASE IF NOT EXISTS `{DB_NAME}`
            CHARACTER SET utf8mb4
            COLLATE utf8mb4_unicode_ci
            """
        )
    finally:
        cursor.close()
        conn.close()


def apply_database_sql(reset: bool = False) -> int:
    """
    reset=False: cập nhật schema/data mặc định, không xóa inventory hiện tại.
    reset=True: xóa database cũ rồi tạo lại toàn bộ.
    """

    ensure_database_exists(reset=reset)
    statements = read_sql_file()

    conn = connect_database()
    cursor = conn.cursor()
    executed_count = 0

    try:
        if not reset:
            migrate_monitoring_schema(cursor)
            migrate_legacy_recipe_schema(cursor)
            migrate_v2_schema(cursor)

        for statement in statements:
            try:
                cursor.execute(statement)
                executed_count += 1
            except Error as error:
                if error.errno in IGNORED_SCHEMA_ERROR_CODES:
                    continue
                raise

        # Again, now that every ALTER in the file has run: a constraint over
        # a column the file only just added was skipped the first time round.
        ensure_ingredient_checks(cursor)

        # Numbered migrations, on top of everything above. Imported here
        # rather than at module scope because migrate.py imports
        # split_sql_statements back out of this file; by the time this line
        # runs, this module is fully loaded and the cycle cannot bite.
        from database import migrate

        migrate.run(cursor)

        conn.commit()
        return executed_count

    except Error:
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()


# ============================================================
# THRESHOLD
# ============================================================

THRESHOLD_UPDATE_QUERY = """
    UPDATE ingredient AS ingredient

    LEFT JOIN (
        SELECT
            ingredient_id,
            ROUND(MAX(recipe_total_gram) * 1.10, 2)
                AS threshold_gram

        FROM (
            SELECT
                drink_id,
                ingredient_id,
                SUM(target_gram) AS recipe_total_gram

            FROM recipe

            GROUP BY
                drink_id,
                ingredient_id
        ) AS recipe_usage

        GROUP BY ingredient_id
    ) AS calculated
        ON calculated.ingredient_id = ingredient.ingredient_id

    SET ingredient.threshold_gram = COALESCE(
        calculated.threshold_gram,
        0
    )
"""


def recalculate_thresholds(cursor) -> None:
    """Set each ingredient threshold to 110% of its largest recipe use."""
    cursor.execute(THRESHOLD_UPDATE_QUERY)


def recalculate_thresholds_in_database() -> None:
    """Recalculate every threshold on a connection of its own."""
    conn = connect_database()
    cursor = conn.cursor()

    try:
        recalculate_thresholds(cursor)
        conn.commit()
    except Error:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


# ============================================================
# JSON HELPERS
# ============================================================

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


def close_database_resources(cursor=None, conn=None) -> None:
    """Close a cursor and a connection, ignoring the ones not given."""
    if cursor is not None:
        cursor.close()

    if conn is not None and conn.is_connected():
        conn.close()
