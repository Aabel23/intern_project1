from server.database.connection import get_connection
from server.database.machine import machine_read
from server.lib.http.http_json import invalid
from server.lib.security.user_session import check_login
from server.lib.validation.identifier_validate import is_machine_id
from server.database.machine import machine_share_store as store


def list_staff(data):
    """Chủ máy xem nhân viên đang được giao máy để thu hồi khi cần."""
    # 1. Kiểm phiên đăng nhập và mã máy.
    user_id, error = check_login(data)
    if error:
        return error
    machine_id = data.get("machine_id")
    if not is_machine_id(machine_id):
        return invalid("Thiếu mã máy hợp lệ")
    # 2. Kiểm quyền chủ trước khi đọc danh sách nhân viên.
    with get_connection() as conn:
        if not machine_read.is_owner(machine_id, user_id, conn):
            return invalid("Chỉ chủ máy mới xem được nhân viên")
        staff = store.list_staff(machine_id, conn)
    return {"valid": True, "staff": staff}
