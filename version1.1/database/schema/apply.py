"""Build the database from schema.sql and seed.sql.

THE SCHEMA IS TWO FILES
    schema.sql is the shape (tables, triggers), seed.sql the default data.
    Both are re-runnable: CREATE TABLE IF NOT EXISTS, INSERT ... ON
    DUPLICATE KEY UPDATE, DROP/CREATE TRIGGER. There are no migrations:
    to change the schema, edit schema.sql and rebuild with reset=True.
"""

from pathlib import Path

from mysql.connector import Error

from database.core.config import DB_NAME
from database.core.connection import connect_database, connect_server


SCHEMA_DIR = Path(__file__).resolve().parent

# Run in this order: the data needs the tables.
SQL_FILES = (SCHEMA_DIR / "schema.sql", SCHEMA_DIR / "seed.sql")


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


def read_sql_file(sql_file: Path) -> list[str]:
    """Read one .sql file and split it into executable statements."""
    if not sql_file.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_file}")

    sql_text = sql_file.read_text(encoding="utf-8")
    return split_sql_statements(sql_text)


# ============================================================
# CREATE / UPDATE DATABASE
# ============================================================

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
    statements = [
        statement
        for sql_file in SQL_FILES
        for statement in read_sql_file(sql_file)
    ]

    conn = connect_database()
    cursor = conn.cursor()
    executed_count = 0

    try:
        for statement in statements:
            cursor.execute(statement)
            executed_count += 1

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
