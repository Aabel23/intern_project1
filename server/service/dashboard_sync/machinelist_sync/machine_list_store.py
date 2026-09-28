"""Truy vấn riêng của danh sách, đổi tên và gỡ máy."""

from server.database.connection import get_connection


def list_by_user(user_id):
    """Các máy tài khoản đang là owner hoặc manager."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT m.machine_id, m.name, mm.role FROM machine_managers mm"
            " JOIN machines m ON m.machine_id = mm.machine_id"
            " WHERE mm.user_id=? ORDER BY mm.created_at, m.name",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def rename_machine(conn, machine_id, name):
    conn.execute("UPDATE machines SET name=? WHERE machine_id=?", (name, machine_id))


def delete_machine(conn, machine_id):
    # Quyền quản lý và mã mời của máy bị xóa theo (ON DELETE CASCADE).
    conn.execute("DELETE FROM machines WHERE machine_id=?", (machine_id,))
