"""Chủ xóa máy; nhân viên bỏ quyền của mình → {valid, deleted, message}."""

from server.database.connection import get_connection
from server.database.machine.machine_read import can_manage, is_owner
from server.database.machine.machine_write import remove_manager
from server.lib.http.http_json import invalid
from server.lib.security.user_session import check_login
from server.lib.validation.identifier_validate import is_machine_id


def remove_machine(data):
    # Bước 1: kiểm phiên rồi kiểm mã máy.
    user_id, error = check_login(data)
    if error:
        return error
    machine_id = data.get("machine_id")
    if not is_machine_id(machine_id):
        return invalid("Thiếu mã máy hợp lệ")

    with get_connection() as conn:
        # Bước 2: khóa ghi trước khi kiểm quyền, giữ vai trò ổn định đến lúc xóa.
        conn.execute("BEGIN IMMEDIATE")
        if is_owner(machine_id, user_id, conn):
            # Bước 3a: xóa máy; quyền và mã mời bị xóa theo ON DELETE CASCADE.
            conn.execute("DELETE FROM machines WHERE machine_id=?", (machine_id,))
            return {"valid": True, "deleted": True, "message": "Đã gỡ máy khỏi quán"}
        if not can_manage(machine_id, user_id, conn):
            return invalid("Bạn không quản lý máy này")

        # Bước 3b: nhân viên chỉ bỏ quyền quản lý của chính mình.
        remove_manager(conn, machine_id, user_id)
    return {"valid": True, "deleted": False, "message": "Đã bỏ quản lý máy"}
