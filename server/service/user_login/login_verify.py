"""Kiểm tra tài khoản và mật khẩu đăng nhập; chỉ đọc database, không tạo phiên.

Lỗi trả về là thân JSON gửi app ({"valid": false, "message"}).
"""

# Thư viện chuẩn
import hashlib
import hmac

# Server chung: database tài khoản, dạng lỗi
from server.database.user.user_read import get_credentials
from server.lib.http_json import invalid

INVALID_LOGIN = "Tên đăng nhập hoặc mật khẩu không đúng"
# Băm cả khi không có tài khoản, để thời gian trả lời không lộ tên nào tồn tại.
DUMMY_PASSWORD = f"pbkdf2_sha256$200000${'00' * 16}${'00' * 32}"


def parse_stored(stored_password):
    """(thuật toán, số vòng, salt, digest) từ chuỗi do user_add.hash_password tạo; None nếu sai dạng."""
    try:
        algorithm, iterations, salt, expected = stored_password.split("$", 3)
        return algorithm, int(iterations), bytes.fromhex(salt), bytes.fromhex(expected)
    except (AttributeError, TypeError, ValueError):
        return None


def matches_password(password, stored_password):
    parsed = parse_stored(stored_password)
    if parsed is None or parsed[0] != "pbkdf2_sha256" or not 1 <= parsed[1] <= 1_000_000:
        return False
    _, iterations, salt, expected = parsed
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def verify_login(data):
    """(user_id, None) nếu đúng tài khoản và mật khẩu, sai thì (None, lỗi)."""
    username, password = data.get("username"), data.get("password")
    if not isinstance(username, str) or not username.strip():
        return None, invalid("Thiếu tên đăng nhập")
    if not isinstance(password, str) or not password:
        return None, invalid("Thiếu mật khẩu")
    if len(username) > 150 or len(password) > 1024:
        return None, invalid("Thông tin đăng nhập không hợp lệ")
    credentials = get_credentials(username.strip())
    stored_password = credentials["password"] if credentials else DUMMY_PASSWORD
    if not matches_password(password, stored_password) or credentials is None:
        return None, invalid(INVALID_LOGIN)
    return credentials["id"], None
