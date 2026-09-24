"""Các hàm đọc dữ liệu từ bảng machines và machine_managers.

Hàm nào nhận conn thì chạy trong giao dịch của nơi gọi (ví dụ đang BEGIN IMMEDIATE);
bỏ trống conn thì tự mở kết nối riêng.
"""

from contextlib import contextmanager

from ..connection import get_connection


@contextmanager
def use_connection(conn=None):
    if conn is not None:
        yield conn
    else:
        with get_connection() as own:
            yield own


def find_id_by_key_hash(key_hash, conn=None):
    """machine_id của máy có product key này, None nếu chưa đăng ký."""
    with use_connection(conn) as conn:
        row = conn.execute(
            "SELECT machine_id FROM machines WHERE product_key_hash=?", (key_hash,)
        ).fetchone()
    return row["machine_id"] if row else None


def matches_key(machine_id, key_hash):
    """ID máy và product key có khớp bản ghi đã đăng ký không."""
    with use_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM machines WHERE machine_id=? AND product_key_hash=?",
            (machine_id, key_hash),
        ).fetchone()
    return row is not None


def get_owner_id(machine_id, conn=None):
    with use_connection(conn) as conn:
        row = conn.execute(
            "SELECT user_id FROM machine_managers WHERE machine_id=? AND role='owner'",
            (machine_id,),
        ).fetchone()
    return row["user_id"] if row else None


def is_owner(machine_id, user_id, conn=None):
    with use_connection(conn) as conn:
        row = conn.execute(
            "SELECT 1 FROM machine_managers WHERE machine_id=? AND user_id=? AND role='owner'",
            (machine_id, user_id),
        ).fetchone()
    return row is not None


def can_manage(machine_id, user_id, conn=None):
    """Chủ máy hoặc nhân viên được giao."""
    with use_connection(conn) as conn:
        row = conn.execute(
            "SELECT 1 FROM machine_managers WHERE machine_id=? AND user_id=?",
            (machine_id, user_id),
        ).fetchone()
    return row is not None


def list_by_user(user_id):
    """Các máy tài khoản đang là owner hoặc manager."""
    with use_connection() as conn:
        rows = conn.execute(
            "SELECT m.machine_id, m.name, mm.role FROM machine_managers mm"
            " JOIN machines m ON m.machine_id = mm.machine_id"
            " WHERE mm.user_id=? ORDER BY mm.created_at, m.name",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_staff(machine_id, conn=None):
    """Nhân viên (manager) của máy, không gồm chủ."""
    with use_connection(conn) as conn:
        rows = conn.execute(
            "SELECT u.id AS user_id, u.username, u.full_name FROM machine_managers mm"
            " JOIN users u ON u.id = mm.user_id"
            " WHERE mm.machine_id=? AND mm.role='manager' ORDER BY mm.created_at, u.username",
            (machine_id,),
        ).fetchall()
    return [dict(row) for row in rows]
