"""Luồng OTP trong một tiến trình. Không tạo tài khoản trong database."""
import math
import threading
import time

from .user_otp_send import send_otp
from .user_otp_generate import generate_code, hash_code, OTP_TTL_SECONDS, OTP_MAX_ATTEMPTS
from .user_otp_validate import check_request, matches_code

SESSION_SECONDS = 900
MAX_SESSIONS = 1000
SESSIONS = {}
EMAIL_LIMITS = {}
# Khóa dùng chung cho mọi thao tác thay đổi trạng thái; không giữ khi gửi SMTP.
# ponytail: một tiến trình; dùng kho trạng thái chung khi chạy nhiều worker.
LOCK = threading.Lock()


def failure(message, retry_after=None):
    result = {"valid": False, "message": message}
    if retry_after is not None:
        result["retry_after"] = retry_after
    return result


def cleanup_locked():
    """Chỉ gọi khi đã giữ LOCK."""
    now = time.monotonic()
    for key, session in list(SESSIONS.items()):
        if now >= session["expires_at"] and not session["sending"]:
            del SESSIONS[key]
    for email, limit in list(EMAIL_LIMITS.items()):
        if now >= limit["window_end"] and now >= limit["next_send_at"]:
            del EMAIL_LIMITS[email]


def cleanup():
    with LOCK:
        cleanup_locked()


def create_session(registration_id, email):
    """Main gọi sau khi dữ liệu hợp lệ. OTP chỉ cần ID phiên và email."""
    with LOCK:
        cleanup_locked()
        if len(SESSIONS) >= MAX_SESSIONS:
            return failure("Server đang bận, hãy thử lại sau", 60)
        SESSIONS[registration_id] = {
            "email": email,
            "expires_at": time.monotonic() + SESSION_SECONDS,
            "otp_hash": None, "otp_expires_at": 0,
            "attempts": 0, "sending": False, "verified": False,
        }
    return {"valid": True}


def start_otp(registration_id):
    """Thử lại cùng phiên không gửi thêm email nếu đã có mã."""
    with LOCK:
        session = SESSIONS.get(registration_id)
        if session and time.monotonic() < session["expires_at"]:
            if session["sending"]:
                return failure("Đang gửi email, hãy thử lại", 3)
            if session["otp_hash"] or session["verified"]:
                return {"valid": True, "registration_id": registration_id,
                        "message": "Yêu cầu đã được tiếp nhận"}
    return resend_otp({"registration_id": registration_id})


def resend_otp(data):
    if not isinstance(data, dict) or not isinstance(data.get("registration_id"), str):
        return failure("Thiếu ID phiên đăng ký")
    registration_id = data["registration_id"]
    with LOCK:
        cleanup_locked()
        session = SESSIONS.get(registration_id)
        now = time.monotonic()
        if session is None or now >= session["expires_at"]:
            return failure("Phiên đăng ký đã hết hạn")
        if session["verified"]:
            return failure("Email đã được xác minh")
        if session["sending"]:
            return failure("Đang gửi email, hãy thử lại", 3)
        email = session["email"]
        limit = EMAIL_LIMITS.get(email)
        if limit and now < limit["next_send_at"]:
            return failure("Vui lòng chờ trước khi gửi lại", math.ceil(limit["next_send_at"] - now))
        if not limit or now >= limit["window_end"]:
            if email not in EMAIL_LIMITS and len(EMAIL_LIMITS) >= MAX_SESSIONS:
                return failure("Server đang bận", 60)
            limit = {"window_end": now + 3600, "count": 0, "next_send_at": 0}
            EMAIL_LIMITS[email] = limit
        if limit["count"] >= 5:
            return failure("Đã đạt giới hạn gửi email trong một giờ", math.ceil(limit["window_end"] - now))
        # Giữ lượt trước khi gửi; lỗi SMTP cũng không được bỏ giới hạn này.
        limit["count"] += 1
        limit["next_send_at"] = now + 60
        session["sending"] = True
        code = generate_code()

    # SMTP chạy ngoài khóa để những phiên khác vẫn hoạt động.
    try:
        error = send_otp(email, code)
    except Exception:
        # Luôn mở trạng thái sending nếu nhà cung cấp email gặp lỗi bất ngờ.
        with LOCK:
            session["sending"] = False
        raise
    with LOCK:
        session["sending"] = False
        if error:
            return failure(error, max(1, math.ceil(limit["next_send_at"] - time.monotonic())))
        if time.monotonic() >= session["expires_at"]:
            return failure("Phiên đăng ký đã hết hạn")
        session["otp_hash"] = hash_code(registration_id, code)
        session["otp_expires_at"] = time.monotonic() + OTP_TTL_SECONDS
        session["attempts"] = 0
        return {"valid": True, "registration_id": registration_id,
                "retry_after": 60, "message": "Đã gửi mã xác minh tới email"}


def confirm_otp(data):
    error = check_request(data)
    if error:
        return failure(error)
    registration_id = data["registration_id"]
    with LOCK:
        cleanup_locked()
        session = SESSIONS.get(registration_id)
        if session is None or time.monotonic() >= session["expires_at"]:
            return failure("Phiên đăng ký đã hết hạn")
        if session["verified"]:
            return {"valid": True, "verified": True, "message": "Email đã được xác minh"}
        if session["sending"]:
            return failure("Đang gửi mã mới, hãy chờ", 3)
        if session["attempts"] >= OTP_MAX_ATTEMPTS:
            return failure("Nhập sai quá 5 lần, hãy yêu cầu mã mới")
        if not session["otp_hash"] or time.monotonic() >= session["otp_expires_at"]:
            return failure("Mã đã hết hạn, hãy yêu cầu mã mới")
        if not matches_code(registration_id, data["code"], session["otp_hash"]):
            session["attempts"] += 1
            if session["attempts"] >= OTP_MAX_ATTEMPTS:
                session["otp_hash"] = None
                return failure("Nhập sai quá 5 lần, hãy yêu cầu mã mới")
            return failure("Mã OTP không đúng")
        session["otp_hash"] = None
        session["verified"] = True
        return {"valid": True, "verified": True, "message": "Xác minh email thành công"}
