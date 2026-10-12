"""Đọc/ghi bảng drink trong MySQL của máy pha (database/core/connection.py) cho tab Menu.

Cần thư mục gốc version1.1 trên PYTHONPATH (xem machine/README.md).
"""

# Thư viện chuẩn
from contextlib import contextmanager
from decimal import Decimal

# Tầng database của máy pha
from database.core.connection import close_database_resources, connect_database
from database.core.helpers import mysql_number

# Cột đi trong gói menu, theo đúng thứ tự này.
FIELDS = (
    "drink_id", "drink_name", "image", "price", "available", "in_stock",
    "glass_id", "drink_type_id", "garnish", "featured",
)


@contextmanager
def connect():
    """Commit khi xong, rollback khi lỗi, luôn đóng kết nối."""
    conn = connect_database()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        close_database_resources(conn=conn)


def read_drinks(conn):
    """Các món chưa xóa mềm, mỗi món là một list theo FIELDS."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"SELECT {', '.join(FIELDS)} FROM drink WHERE deleted_at IS NULL ORDER BY drink_id"
        )
        rows = cursor.fetchall()
    finally:
        cursor.close()
    # DECIMAL (giá) thành int/float để JSON và CRC không phụ thuộc kiểu Decimal.
    return [[mysql_number(v) if isinstance(v, Decimal) else v for v in row] for row in rows]


def update_drink(conn, drink_id, fields):
    """Ghi các cột đã kiểm tra (tên cột lấy từ machine_menu_validate.EDITABLE)."""
    assignments = ", ".join(f"{key} = %s" for key in fields)
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"UPDATE drink SET {assignments} WHERE drink_id = %s", (*fields.values(), drink_id)
        )
    finally:
        cursor.close()
