"""Token phiên app: cấp sau khi đăng nhập, mọi module cần biết người gọi đều dùng file này."""

import secrets
import time

from server.config.config import (
    SESSION_TTL_SECONDS,
    TOKEN_BYTES,
    TOKEN_MAX_LENGTH,
    TOKEN_MIN_LENGTH,
)
from server.database.connection import get_connection
from server.lib.security.data_hash import sha256_hex

# login_required báo app xóa token đã lưu và quay về màn hình đăng nhập.
NOT_LOGGED_IN = {
    "valid": False,
    "login_required": True,
    "message": "Phiên đăng nhập hết hạn, hãy đăng nhập lại",
}


def create_session(user_id):
    token = secrets.token_urlsafe(TOKEN_BYTES)
    now = time.time()
    with get_connection() as conn:
        conn.execute("DELETE FROM app_sessions WHERE expires_at <= ?", (now,))
        conn.execute(
            "INSERT INTO app_sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (sha256_hex(token), user_id, now + SESSION_TTL_SECONDS),
        )
    return token


def user_from_request(data):
    """Trả user_id theo trường token trong JSON, None nếu thiếu hoặc hết hạn."""
    token = data.get("token") if isinstance(data, dict) else None
    if not isinstance(token, str) or not TOKEN_MIN_LENGTH <= len(token) <= TOKEN_MAX_LENGTH:
        return None
    with get_connection() as conn:
        row = conn.execute(
            "SELECT user_id FROM app_sessions WHERE token_hash=? AND expires_at > ?",
            (sha256_hex(token), time.time()),
        ).fetchone()
    return row["user_id"] if row else None


def check_login(data):
    """Trả (user_id, None) nếu token còn hiệu lực, sai thì (None, NOT_LOGGED_IN)."""
    user_id = user_from_request(data)
    if user_id is None:
        return None, NOT_LOGGED_IN
    return user_id, None


def end_session(data):
    """Đăng xuất: xóa token trên server để token cũ không dùng lại được."""
    token = data.get("token") if isinstance(data, dict) else None
    if isinstance(token, str):
        with get_connection() as conn:
            conn.execute("DELETE FROM app_sessions WHERE token_hash=?", (sha256_hex(token),))
    return {"valid": True, "message": "Đã đăng xuất"}
