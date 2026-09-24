"""Đổi tên máy và gỡ máy khỏi tài khoản."""

from server.database.connection import get_connection
from server.database.machine import machine_read, machine_write
from server.lib.checks import is_machine_id
from server.service.user_login.session import NOT_LOGGED_IN, user_from_request


def rename_machine(data):
    """Chủ máy đổi tên hiển thị; tên do người dùng nhập trên app."""
    user_id = user_from_request(data)
    if user_id is None:
        return NOT_LOGGED_IN
    machine_id = data.get("machine_id")
    name = data.get("name")
    if not is_machine_id(machine_id):
        return {"valid": False, "message": "Thiếu mã máy hợp lệ"}
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 150:
        return {"valid": False, "message": "Tên máy phải có 1-150 ký tự"}
    with get_connection() as conn:
        if not machine_read.is_owner(machine_id, user_id, conn):
            return {"valid": False, "message": "Chỉ chủ máy mới đổi tên được"}
        machine_write.rename_machine(conn, machine_id, name.strip())
    return {"valid": True, "name": name.strip(), "message": "Đã đổi tên máy"}


def remove_machine(data):
    """Chủ gỡ máy: xóa máy cùng quyền của mọi nhân viên, tem QR đăng ký lại được.
    Nhân viên gỡ máy: chỉ bỏ quyền quản lý của chính mình."""
    user_id = user_from_request(data)
    if user_id is None:
        return NOT_LOGGED_IN
    machine_id = data.get("machine_id")
    if not is_machine_id(machine_id):
        return {"valid": False, "message": "Thiếu mã máy hợp lệ"}
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        if machine_read.is_owner(machine_id, user_id, conn):
            machine_write.delete_machine(conn, machine_id)
            return {"valid": True, "deleted": True, "message": "Đã gỡ máy khỏi quán"}
        if not machine_read.can_manage(machine_id, user_id, conn):
            return {"valid": False, "message": "Bạn không quản lý máy này"}
        machine_write.remove_manager(conn, machine_id, user_id)
    return {"valid": True, "deleted": False, "message": "Đã bỏ quản lý máy"}
