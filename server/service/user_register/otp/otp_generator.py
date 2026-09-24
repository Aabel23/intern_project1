"""Sinh mã OTP; trạng thái phiên được quản lý tại otp_flow.py."""
import hashlib
import secrets

OTP_DIGITS = 6
OTP_TTL_SECONDS = 300
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60


def generate_code():
    return f"{secrets.randbelow(10 ** OTP_DIGITS):0{OTP_DIGITS}d}"


def hash_code(registration_id, code):
    return hashlib.sha256(f"{registration_id}:{code}".encode()).hexdigest()
