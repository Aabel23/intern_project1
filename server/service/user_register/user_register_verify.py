"""Kiểm tra dữ liệu đăng ký; chỉ đọc database (trùng tên/email), không ghi, không đọc/ghi HTTP.

Trả câu lỗi cho người dùng, hoặc None nếu hợp lệ.
"""

# Thư viện chuẩn
import re

# Server chung: database tài khoản
from server.database.user.user_read import get_by_email, get_by_username


def check_duplicate(username, email):
    if get_by_username(username):
        return "Tên đăng nhập đã tồn tại"
    if get_by_email(email):
        return "Email đã tồn tại"
    return None


def verify_user(data):
    if not isinstance(data, dict):
        return "Dữ liệu phải là JSON object"

    for field in ("full_name", "username", "password", "email"):
        if not isinstance(data.get(field), str):
            return f"Trường {field} phải là chuỗi"
        if not data[field].strip():
            return f"Trường {field} không được để trống"

    if len(data["password"]) < 8:
        return "Mật khẩu cần ít nhất 8 ký tự"
    # Cùng giới hạn với login_verify, nếu không sẽ tạo được tài khoản không đăng nhập được.
    if len(data["password"]) > 1024:
        return "Mật khẩu tối đa 1024 ký tự"
    if len(data["username"].strip()) > 150:
        return "Tên đăng nhập tối đa 150 ký tự"
    if len(data["full_name"].strip()) > 150:
        return "Họ tên tối đa 150 ký tự"
    if len(data["email"].strip()) > 254:
        return "Email không hợp lệ"

    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", data["email"].strip()):
        return "Email không hợp lệ"

    # Email lưu dạng chữ thường nên so trùng cũng bằng chữ thường.
    return check_duplicate(data["username"].strip(), data["email"].strip().lower())
