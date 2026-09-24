"""Băm mật khẩu người dùng trước khi lưu vào database."""

import hashlib
import os


def hash_password(password):
    if not password:
        raise ValueError("Mật khẩu không được để trống")

    salt = os.urandom(16)
    iterations = 200_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"
