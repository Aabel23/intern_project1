"""Bản sao hàm đối chiếu mật khẩu từ login_verify.py."""

import hashlib
import hmac


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
