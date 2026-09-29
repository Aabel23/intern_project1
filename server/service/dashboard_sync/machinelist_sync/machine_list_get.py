"""Đọc danh sách máy từ SQLite và trạng thái từ heartbeat trong RAM."""

from server.database.connection import get_connection
from server.lib.machine.machine_transport import is_online, last_seen_of
from server.lib.security.user_session import check_login


def list_my_machines(data):
    """JSON app → {valid, machines}; chỉ lấy máy tài khoản có quyền quản lý."""
    # Bước 1: kiểm phiên đăng nhập.
    user_id, error = check_login(data)
    if error:
        return error

    # Bước 2: đọc máy và vai trò, giữ thứ tự được cấp quyền rồi đến tên máy.
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT m.machine_id, m.name, mm.role FROM machine_managers mm"
            " JOIN machines m ON m.machine_id = mm.machine_id"
            " WHERE mm.user_id=? ORDER BY mm.created_at, m.name",
            (user_id,),
        ).fetchall()
    return {"valid": True, "machines": [dict(row) for row in rows]}


def machine_status(machine_id):
    """Không cần token: trả trạng thái heartbeat, không gửi lệnh xuống máy."""
    return {"machine_id": machine_id, "online": is_online(machine_id), "last_seen": last_seen_of(machine_id)}
