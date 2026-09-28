"""Các hàm đọc/ghi bảng machine_invites (mã mời chia sẻ máy, lưu dạng hash)."""

from pathlib import Path
from server.database.connection import get_connection


def setup():
    with get_connection() as conn:
        conn.executescript(Path(__file__).with_name("machine_share_schema.sql").read_text(encoding="utf-8"))


def replace_invite(conn, code_hash, machine_id, created_by, expires_at, now):
    """Xóa mã hết hạn và mã cũ chưa dùng của máy, rồi lưu mã mới."""
    conn.execute("DELETE FROM machine_invites WHERE expires_at <= ?", (now,))
    conn.execute(
        "DELETE FROM machine_invites WHERE machine_id=? AND used_at IS NULL", (machine_id,)
    )
    conn.execute(
        "INSERT INTO machine_invites (code_hash, machine_id, created_by, expires_at)"
        " VALUES (?, ?, ?, ?)",
        (code_hash, machine_id, created_by, expires_at),
    )


def find_valid_invite(conn, code_hash, now):
    """Mã chưa dùng, chưa hết hạn: trả machine_id và tên máy, None nếu không có."""
    row = conn.execute(
        "SELECT i.machine_id, m.name FROM machine_invites i"
        " JOIN machines m ON m.machine_id = i.machine_id"
        " WHERE i.code_hash=? AND i.used_at IS NULL AND i.expires_at > ?",
        (code_hash, now),
    ).fetchone()
    return dict(row) if row else None


def mark_used(conn, code_hash, user_id):
    conn.execute(
        "UPDATE machine_invites SET used_by=?, used_at=datetime('now') WHERE code_hash=?",
        (user_id, code_hash),
    )


def list_staff(machine_id, conn):
    """Danh sách nhân viên đọc trong transaction đã kiểm quyền của chủ máy."""
    rows = conn.execute(
        "SELECT u.id AS user_id, u.username, u.full_name FROM machine_managers mm"
        " JOIN users u ON u.id = mm.user_id"
        " WHERE mm.machine_id=? AND mm.role='manager' ORDER BY mm.created_at, u.username",
        (machine_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def add_manager(conn, machine_id, user_id):
    # Đã là chủ thì giữ nguyên quyền owner.
    conn.execute(
        "INSERT OR IGNORE INTO machine_managers (machine_id, user_id, role) VALUES (?, ?, 'manager')",
        (machine_id, user_id),
    )
