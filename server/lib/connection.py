"""Quản lý kết nối tới SQLite.

Mọi module repository đều lấy connection qua đây để đường dẫn DB và
các PRAGMA chỉ được khai báo ở một chỗ duy nhất.
"""

import sqlite3
from contextlib import contextmanager
from server.config.path import DATABASE_PATH

DB_PATH = DATABASE_PATH


def connect() -> sqlite3.Connection:
    """Mở một connection mới, trả về row dạng dict-like."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_connection():
    """Dùng với `with`: tự commit khi thành công, rollback khi có lỗi."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
