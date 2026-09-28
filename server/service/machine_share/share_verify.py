"""Kiểm tra gói chia sẻ máy app gửi; chỉ đọc, không ghi database, không đọc/ghi HTTP.

Lỗi trả về là thân JSON gửi app ({"valid": false, "message"}).
"""

# Server chung: cấu hình mã mời, hàm kiểm tra, dạng lỗi, phiên đăng nhập
from server.config.config import INVITE_CODE_MAX_LENGTH, INVITE_CODE_MIN_LENGTH
from server.lib.checks import is_machine_id
from server.lib.http_json import invalid
from server.lib.session import check_login


def check_request(data):
    """Trả (user_id, machine_id, None) nếu đã đăng nhập và mã máy đúng dạng, sai thì (None, None, lỗi)."""
    user_id, error = check_login(data)
    if error:
        return None, None, error
    machine_id = data.get("machine_id")
    if not is_machine_id(machine_id):
        return None, None, invalid("Thiếu mã máy hợp lệ")
    return user_id, machine_id, None


def is_code(code):
    return isinstance(code, str) and INVITE_CODE_MIN_LENGTH <= len(code) <= INVITE_CODE_MAX_LENGTH


def is_staff_id(value):
    return isinstance(value, int) and not isinstance(value, bool)
