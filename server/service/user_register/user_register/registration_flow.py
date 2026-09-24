"""Điều phối đăng ký: kiểm tra dữ liệu -> OTP -> ghi tài khoản."""
import secrets
import threading
import time

from server.lib.checks import is_request_id, remove_expired
from server.lib.hashing import request_fingerprint
from server.database.user.user_add import hash_password
from ..otp import otp_flow
from .user_verify import verify_user
from .user_register import register_user

REGISTRATIONS = {}
FLOW_LOCK = threading.Lock()


def cleanup_locked():
    remove_expired(REGISTRATIONS)


def cleanup():
    with FLOW_LOCK:
        cleanup_locked()
    otp_flow.cleanup()


def find_registration(request_id):
    """Tìm phiên cũ; gọi khi đang giữ FLOW_LOCK."""
    for key, state in REGISTRATIONS.items():
        if state["request_id"] == request_id:
            return key
    return None


def prepare_registration(data, fingerprint):
    """Kiểm tra dữ liệu và bật cờ đầu tiên; gọi khi đang giữ FLOW_LOCK."""
    if len(REGISTRATIONS) >= otp_flow.MAX_SESSIONS:
        return {"valid": False, "message": "Server đang bận", "retry_after": 60}
    error = verify_user(data)
    if error:
        return {"valid": False, "message": error}

    user_data = {
        "full_name": data["full_name"].strip(),
        "username": data["username"].strip(),
        "email": data["email"].strip().lower(),
        "password_hash": hash_password(data["password"]),
    }
    registration_id = secrets.token_urlsafe(32)
    result = otp_flow.create_session(registration_id, user_data["email"])
    if not result["valid"]:
        return result
    REGISTRATIONS[registration_id] = {
        "request_id": data["request_id"], "fingerprint": fingerprint,
        "user_data": user_data,
        "data_valid": True, "otp_verified": False, "account_created": False,
        "expires_at": time.monotonic() + otp_flow.SESSION_SECONDS,
    }
    print("VALID: Registration data; waiting for OTP", flush=True)
    return {"valid": True, "registration_id": registration_id}


def resume_registration(registration_id, fingerprint):
    """Đối chiếu lần thử lại; gọi khi đang giữ FLOW_LOCK."""
    state = REGISTRATIONS[registration_id]
    if state["fingerprint"] != fingerprint:
        return {"valid": False, "message": "Dữ liệu đã thay đổi; hãy tạo yêu cầu mới"}
    return {"valid": True, "registration_id": registration_id,
            "account_created": state["account_created"],
            "verified": state["account_created"], "message": "Tài khoản đã được tạo"}


def receive_register(data):
    # Nhận mã yêu cầu để tránh tạo phiên trùng khi app thử lại.
    if not isinstance(data, dict):
        return {"valid": False, "message": "Dữ liệu phải là JSON object"}
    request_id = data.get("request_id")
    if not is_request_id(request_id):
        return {"valid": False, "message": "Thiếu mã yêu cầu đăng ký hợp lệ"}
    fingerprint = request_fingerprint(data)

    # Chuẩn bị phiên trong khóa; gửi email sau khi đã thả khóa.
    with FLOW_LOCK:
        cleanup_locked()
        registration_id = find_registration(request_id)
        if registration_id is None:
            result = prepare_registration(data, fingerprint)
        else:
            result = resume_registration(registration_id, fingerprint)

    if not result["valid"] or result.get("account_created"):
        return result
    return otp_flow.start_otp(result["registration_id"])


def resend_otp(data):
    return otp_flow.resend_otp(data)


def finish_registration(registration_id):
    """Đủ hai cờ mới ghi DB; gọi khi đang giữ FLOW_LOCK."""
    state = REGISTRATIONS.get(registration_id)
    if state is None:
        return {"valid": False, "message": "Phiên đăng ký đã hết hạn"}
    state["otp_verified"] = True
    if not state["data_valid"] or not state["otp_verified"]:
        return {"valid": False, "message": "Chưa đủ điều kiện tạo tài khoản"}
    if state["account_created"]:
        return {"valid": True, "verified": True, "account_created": True,
                "message": "Tài khoản đã được tạo"}
    try:
        register_user(state["user_data"])
    except ValueError as error:
        return {"valid": False, "message": str(error)}
    state["account_created"] = True
    print("VALID: User created", flush=True)
    return {"valid": True, "verified": True, "account_created": True,
            "message": "Tạo tài khoản thành công"}


def confirm_otp(data):
    result = otp_flow.confirm_otp(data)
    if not result["valid"]:
        return result
    with FLOW_LOCK:
        cleanup_locked()
        return finish_registration(data["registration_id"])
