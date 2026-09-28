"""Sinh mã OTP; trạng thái phiên được quản lý tại user_otp_process.py."""
import secrets

from server.lib.hashing import sha256_hex

OTP_DIGITS = 6
OTP_TTL_SECONDS = 300
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60


def generate_code():
    return f"{secrets.randbelow(10 ** OTP_DIGITS):0{OTP_DIGITS}d}"


def hash_code(registration_id, code):
    return sha256_hex(f"{registration_id}:{code}")
