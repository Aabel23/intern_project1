"""Đăng nhập một bước: app gửi username/password, server kiểm rồi trả token ngay.

    receive_login: username + password → so với database → đúng thì tạo phiên, trả token

Hàm nhận body JSON đã parse, trả thân {"valid", "message", ...}; api gắn status theo valid.
"""

# Tài khoản/phiên dùng chung; nghiệp vụ đăng nhập nằm trong file này.
from server.database.user.user_read import get_credentials
from server.lib.http.http_json import invalid
from server.lib.security.user_password import matches_password
from server.lib.security.user_session import create_session


INVALID_LOGIN = "Tên đăng nhập hoặc mật khẩu không đúng"
# Băm cả khi không có tài khoản, để thời gian trả lời không lộ tên nào tồn tại.
DUMMY_PASSWORD = f"pbkdf2_sha256$200000${'00' * 16}${'00' * 32}"


def receive_login(data):
    """Đúng tài khoản và mật khẩu thì trả token phiên mới, sai thì trả lỗi."""
    if not isinstance(data, dict):
        return invalid("Dữ liệu phải là JSON object")
    user_id, error = verify_login(data)
    if error:
        return error
    return {"valid": True, "token": create_session(user_id), "message": "Đăng nhập thành công"}


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
