"""Hàm băm dùng chung: product key, token phiên, mã mời, OTP, dấu vân tay request."""

import hashlib
import hmac
import json
import secrets

# Khóa ngẫu nhiên mỗi lần chạy server; dấu vân tay chỉ cần so trong RAM.
FINGERPRINT_KEY = secrets.token_bytes(32)


def sha256_hex(text):
    """SHA-256 dạng hex của một chuỗi; DB chỉ lưu kết quả này, không lưu bản gốc."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def request_fingerprint(data):
    """Dấu vân tay nội dung request: app thử lại cùng request_id thì phải gửi y hệt."""
    payload = json.dumps(data, sort_keys=True, ensure_ascii=True).encode()
    return hmac.new(FINGERPRINT_KEY, payload, hashlib.sha256).hexdigest()
