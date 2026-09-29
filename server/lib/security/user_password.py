"""Băm và đối chiếu mật khẩu; định dạng dùng chung cho đăng ký và đăng nhập."""

import hashlib
import hmac
import os


def hash_password(password):
    if not password:
        raise ValueError("Mật khẩu không được để trống")

    salt = os.urandom(16)
    iterations = 200_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def parse_stored(stored_password):
    """(thuật toán, số vòng, salt, digest) từ chuỗi do hash_password tạo; None nếu sai dạng."""
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
