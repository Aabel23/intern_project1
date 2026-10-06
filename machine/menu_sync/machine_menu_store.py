"""Đọc/ghi bảng drink trong machine/database/database.db cho tab Menu."""

# Thư viện chuẩn
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "database" / "database.db"

# Cột đi trong gói menu, theo đúng thứ tự này.
FIELDS = (
    "drink_id", "drink_name", "image", "price", "available", "in_stock",
    "glass_id", "drink_type_id", "garnish", "featured",
)


@contextmanager
def connect():
    """Commit khi xong, rollback khi lỗi, luôn đóng kết nối."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        with conn:
            yield conn
    finally:
        conn.close()


def read_drinks(conn):
    """Các món chưa xóa mềm, mỗi món là một list theo FIELDS."""
    rows = conn.execute(
        f"SELECT {', '.join(FIELDS)} FROM drink WHERE deleted_at IS NULL ORDER BY drink_id"
    )
    return [list(row) for row in rows]


def update_drink(conn, drink_id, fields):
    """Ghi các cột đã kiểm tra (tên cột lấy từ machine_menu_validate.EDITABLE)."""
    assignments = ", ".join(f"{key} = ?" for key in fields)
    conn.execute(f"UPDATE drink SET {assignments} WHERE drink_id = ?", (*fields.values(), drink_id))
