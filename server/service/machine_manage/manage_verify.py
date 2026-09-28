"""Hàm kiểm tra của quản lý máy; chỉ đọc, không ghi database, không đọc/ghi HTTP.

Mỗi hàm kiểm tra trả lỗi là thân JSON gửi app ({"valid": false, "message"}),
flow tự gắn status.
"""

# Server chung: database máy, hàm kiểm tra
from server.database.machine import machine_read
from server.lib.checks import is_machine_id

# Module khác: phiên đăng nhập
from server.service.user_login.session import NOT_LOGGED_IN, user_from_request

NAME_MAX_LENGTH = 150


def invalid(message):
    return {"valid": False, "message": message}


def check_request(data):
    """Trả (user_id, machine_id, None) nếu đã đăng nhập và mã máy đúng dạng, sai thì (None, None, lỗi)."""
    user_id = user_from_request(data)
    if user_id is None:
        return None, None, NOT_LOGGED_IN
    machine_id = data.get("machine_id")
    if not is_machine_id(machine_id):
        return None, None, invalid("Thiếu mã máy hợp lệ")
    return user_id, machine_id, None


def clean_name(name):
    """Tên đã bỏ khoảng trắng hai đầu; None nếu rỗng hoặc dài quá NAME_MAX_LENGTH."""
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > NAME_MAX_LENGTH:
        return None
    return name.strip()


def role_of(conn, machine_id, user_id):
    """"owner", "manager" hoặc None; đọc trong conn của flow để cùng transaction với lệnh ghi."""
    if machine_read.is_owner(machine_id, user_id, conn):
        return "owner"
    if machine_read.can_manage(machine_id, user_id, conn):
        return "manager"
    return None
