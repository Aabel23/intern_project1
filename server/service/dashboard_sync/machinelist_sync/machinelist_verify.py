"""Hàm kiểm tra của tab Máy; chỉ đọc, không ghi database, không đọc/ghi HTTP.

Lỗi trả về là thân JSON gửi app ({"valid": false, "message"}).
"""

# Server chung: database máy, hàm kiểm tra, phiên đăng nhập, dạng lỗi
from server.database.machine import machine_read
from server.lib.checks import is_machine_id
from server.lib.http_json import invalid
from server.lib.session import check_login

NAME_MAX_LENGTH = 150


def check_request(data):
    """Trả (user_id, machine_id, None) nếu đã đăng nhập và mã máy đúng dạng, sai thì (None, None, lỗi)."""
    user_id, error = check_login(data)
    if error:
        return None, None, error
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
