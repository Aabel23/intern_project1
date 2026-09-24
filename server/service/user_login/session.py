"""Token phiên app: cấp sau khi đăng nhập, gửi kèm các API cần biết người gọi."""

import hashlib
import secrets
import time

from server.config.config import (
    SESSION_TTL_SECONDS,
    TOKEN_BYTES,
    TOKEN_MAX_LENGTH,
    TOKEN_MIN_LENGTH,
)
from server.database.connection import get_connection


def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(user_id):
    token = secrets.token_urlsafe(TOKEN_BYTES)
    now = time.time()
    with get_connection() as conn:
        conn.execute("DELETE FROM app_sessions WHERE expires_at <= ?", (now,))
        conn.execute(
            "INSERT INTO app_sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (hash_token(token), user_id, now + SESSION_TTL_SECONDS),
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
            (hash_token(token), time.time()),
        ).fetchone()
    return row["user_id"] if row else None
