from server.database.connection import get_connection
from server.database.machine import machine_read
from server.lib.http.http_json import invalid
from server.lib.security.user_session import check_login
from server.lib.validation.identifier_validate import is_machine_id
from server.database.machine import machine_write


def is_staff_id(value):
    return isinstance(value, int) and not isinstance(value, bool)


def revoke_staff(data):
    """Chủ máy thu hồi quyền của một nhân viên; không xóa được quyền chủ."""
    # 1. Kiểm phiên và dữ liệu thu hồi.
    user_id, error = check_login(data)
    if error:
        return error
    machine_id, staff_id = data.get("machine_id"), data.get("user_id")
    if not is_machine_id(machine_id) or not is_staff_id(staff_id):
        return invalid("Thiếu mã máy hoặc nhân viên")
    # 2. Kiểm quyền chủ và chỉ xóa quyền manager.
    with get_connection() as conn:
        if not machine_read.is_owner(machine_id, user_id, conn):
            return invalid("Chỉ chủ máy mới thu hồi được quyền")
        machine_write.remove_manager(conn, machine_id, staff_id)
    return {"valid": True, "message": "Đã thu hồi quyền nhân viên"}
