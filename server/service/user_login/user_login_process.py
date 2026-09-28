"""Luồng đăng nhập hai bước: nhận yêu cầu, xác minh ngay, giữ kết quả ngắn hạn cho app hỏi lại.

    receive_login:     request_id → (gửi lại cùng request_id thì trả login_id cũ) → xác minh
                       → tạo phiên nếu đúng → giữ kết quả 60 giây → trả login_id
    send_verification: request_id + login_id → kết quả đã giữ (token nếu đúng mật khẩu)

Mỗi hàm nhận body JSON đã parse, trả thân {"valid", "message", ...}; api gắn status theo valid.
"""

# Thư viện chuẩn
import hmac
import secrets
import threading
import time

# Tài khoản/phiên dùng chung; nghiệp vụ đăng nhập nằm trong file này.
from server.config.routing import APP_VERIFY_LOGIN
from server.database.user.user_read import get_credentials
from server.lib.checks import is_request_id, remove_expired
from server.lib.hashing import request_fingerprint
from server.lib.http_json import invalid
from server.lib.passwords import matches_password
from server.lib.session import create_session


INVALID_LOGIN = "Tên đăng nhập hoặc mật khẩu không đúng"
# Băm cả khi không có tài khoản, để thời gian trả lời không lộ tên nào tồn tại.
DUMMY_PASSWORD = f"pbkdf2_sha256$200000${'00' * 16}${'00' * 32}"

LOGIN_TTL_SECONDS = 60
MAX_LOGIN_STATES = 1000
LOGIN_STATES = {}
FLOW_LOCK = threading.Lock()


def cleanup_locked():
    remove_expired(LOGIN_STATES)


def cleanup():
    with FLOW_LOCK:
        cleanup_locked()


def login_result(data):
    """Kết quả gửi app: đúng mật khẩu thì kèm token phiên mới."""
    user_id, error = verify_login(data)
    if error:
        return error
    return {"valid": True, "verified": True, "token": create_session(user_id), "message": "Đăng nhập thành công"}


def find_login(request_id):
    """Tìm login_id theo request_id; chỉ gọi khi đang giữ FLOW_LOCK."""
    for login_id, state in LOGIN_STATES.items():
        if state["request_id"] == request_id:
            return login_id
    return None


def receive_login(data):
    """Nhận username/password, xác minh ngay và chỉ lưu kết quả, không lưu mật khẩu."""
    if not isinstance(data, dict):
        return {"valid": False, "message": "Dữ liệu phải là JSON object"}
    request_id = data.get("request_id")
    if not is_request_id(request_id):
        return {"valid": False, "message": "Thiếu mã yêu cầu đăng nhập hợp lệ"}
    fingerprint = request_fingerprint(data)

    with FLOW_LOCK:
        cleanup_locked()
        old_login_id = find_login(request_id)
        if old_login_id is not None:
            state = LOGIN_STATES[old_login_id]
            if state["fingerprint"] != fingerprint:
                return {
                    "valid": False,
                    "message": "Dữ liệu đã thay đổi; hãy tạo yêu cầu đăng nhập mới",
                }
            return {
                "valid": True,
                "login_id": old_login_id,
                "verify_route": APP_VERIFY_LOGIN,
                "message": "Yêu cầu đăng nhập đã được tiếp nhận",
            }
        if len(LOGIN_STATES) >= MAX_LOGIN_STATES:
            return {"valid": False, "message": "Server đang bận", "retry_after": 60}
        login_id = secrets.token_urlsafe(32)
        LOGIN_STATES[login_id] = {
            "request_id": request_id,
            "fingerprint": fingerprint,
            "status": "received",
            "expires_at": time.monotonic() + LOGIN_TTL_SECONDS,
        }

    try:
        result = login_result(data)
    except Exception:
        with FLOW_LOCK:
            LOGIN_STATES.pop(login_id, None)
        raise

    with FLOW_LOCK:
        state = LOGIN_STATES.get(login_id)
        if state is None:
            return {"valid": False, "message": "Yêu cầu đăng nhập đã hết hạn"}
        state["status"] = "verified"
        state["result"] = result

    return {
        "valid": True,
        "login_id": login_id,
        "verify_route": APP_VERIFY_LOGIN,
        "message": "Đã nhận yêu cầu đăng nhập",
    }


def send_verification(data):
    """App gọi bằng cùng request_id và login_id để nhận kết quả xác minh."""
    if not isinstance(data, dict):
        return {"valid": False, "message": "Dữ liệu phải là JSON object"}
    request_id = data.get("request_id")
    login_id = data.get("login_id")
    if not is_request_id(request_id):
        return {"valid": False, "message": "Thiếu mã yêu cầu đăng nhập hợp lệ"}
    if not isinstance(login_id, str) or not login_id:
        return {"valid": False, "message": "Thiếu ID đăng nhập"}

    with FLOW_LOCK:
        cleanup_locked()
        state = LOGIN_STATES.get(login_id)
        if state is None:
            return {"valid": False, "message": "Yêu cầu đăng nhập đã hết hạn"}
        if not hmac.compare_digest(state["request_id"], request_id):
            return {"valid": False, "message": "Mã yêu cầu đăng nhập không khớp"}
        if state["status"] != "verified":
            return {"valid": False, "message": "Đang xác minh đăng nhập", "retry_after": 1}
        return dict(state["result"])


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
