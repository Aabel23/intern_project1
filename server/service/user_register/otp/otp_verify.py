"""Kiểm tra đầu vào và đối chiếu mã; không tự thay đổi phiên."""
import hmac
import re
from .otp_generator import hash_code


def check_request(data):
    if not isinstance(data, dict):
        return "Dữ liệu phải là JSON object"
    if not isinstance(data.get("registration_id"), str):
        return "Thiếu ID phiên đăng ký"
    if not isinstance(data.get("code"), str) or not re.fullmatch(r"[0-9]{6}", data["code"]):
        return "Mã OTP phải gồm 6 chữ số"
    return None


def matches_code(registration_id, code, otp_hash):
    return hmac.compare_digest(otp_hash, hash_code(registration_id, code))
