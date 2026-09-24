"""Kiểm tra dữ liệu đăng ký trước khi xử lý."""

import re
from server.database.user.user_read import get_by_username, get_by_email


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

    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", data["email"].strip()):
        return "Email không hợp lệ"

    return check_duplicate(data["username"].strip(), data["email"].strip())
