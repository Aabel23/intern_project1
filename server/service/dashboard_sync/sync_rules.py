"""Quyền của các tab dashboard đọc/ghi dữ liệu máy (menu, kho).

Bảng vai trò được làm từng việc, và check_access() dùng chung cho mọi module
trong dashboard_sync: token → người dùng → có quản lý máy này → vai trò đủ quyền.
Lỗi trả dạng {"loi": ...} như các tab dữ liệu máy đang trả.
"""

# Server chung: database máy, hàm kiểm tra, phiên đăng nhập
from server.database.machine.machine_read import can_manage, is_owner
from server.lib.checks import is_machine_id
from server.lib.session import NOT_LOGGED_IN, user_from_request

# Tab Menu: nhận gói menu, gửi thay đổi món.
QUYEN_MENU = {"owner", "manager"}
# Tab Kho: xem tồn kho.
QUYEN_KHO = {"owner", "manager"}
# Tab Kho: nạp kho.
QUYEN_NAP_KHO = {"owner", "manager"}


def check_access(data, roles):
    """Trả (machine_id, None) nếu được làm việc này với máy, sai thì (None, (lỗi, status))."""
    user_id = user_from_request(data)
    if user_id is None:
        return None, ({"loi": NOT_LOGGED_IN["message"], "login_required": True}, 401)
    machine_id = data.get("machine_id")
    if not is_machine_id(machine_id) or not can_manage(machine_id, user_id):
        return None, ({"loi": "Bạn không quản lý máy này"}, 403)
    vai_tro = "owner" if is_owner(machine_id, user_id) else "manager"
    if vai_tro not in roles:
        return None, ({"loi": "Không đủ quyền"}, 403)
    return machine_id, None
