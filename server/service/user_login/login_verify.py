"""Đọc tài khoản trong database và xác minh mật khẩu đăng nhập."""

import hashlib
import hmac

from server.database.user.user_read import get_credentials
from .session import create_session


INVALID_LOGIN = "Tên đăng nhập hoặc mật khẩu không đúng"
DUMMY_PASSWORD = f"pbkdf2_sha256$200000${'00' * 16}${'00' * 32}"


def _matches_password(password, stored_password):
    """So sánh mật khẩu với chuỗi PBKDF2 do user_password.hash_password tạo."""
    try:
        algorithm, iterations, salt, expected = stored_password.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations)
        if not 1 <= iterations <= 1_000_000:
            return False
        salt = bytes.fromhex(salt)
        expected = bytes.fromhex(expected)
    except (AttributeError, TypeError, ValueError):
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(actual, expected)


def verify_login(data):
    """Trả về kết quả tối giản; tuyệt đối không trả password hash cho app."""
    if not isinstance(data, dict):
        return {"valid": False, "message": "Dữ liệu phải là JSON object"}

    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str) or not username.strip():
        return {"valid": False, "message": "Thiếu tên đăng nhập"}
    if not isinstance(password, str) or not password:
        return {"valid": False, "message": "Thiếu mật khẩu"}
    if len(username) > 150 or len(password) > 1024:
        return {"valid": False, "message": "Thông tin đăng nhập không hợp lệ"}

    credentials = get_credentials(username.strip())
    stored_password = credentials["password"] if credentials else DUMMY_PASSWORD
    if not _matches_password(password, stored_password) or credentials is None:
        return {"valid": False, "message": INVALID_LOGIN}

    return {
        "valid": True,
        "verified": True,
        "token": create_session(credentials["id"]),
        "message": "Đăng nhập thành công",
    }
