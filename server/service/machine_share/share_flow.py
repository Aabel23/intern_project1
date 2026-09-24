"""Chủ máy tạo mã mời dạng QR, nhân viên quét để được giao quản lý máy."""

import hashlib
import secrets
import time

from server.database.connection import get_connection
from server.service.user_login.session import user_from_request


INVITE_TTL_SECONDS = 5 * 60
NOT_LOGGED_IN = {"valid": False, "message": "Phiên đăng nhập hết hạn, hãy đăng nhập lại"}


def hash_code(code):
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def create_invite(data):
    user_id = user_from_request(data)
    if user_id is None:
        return NOT_LOGGED_IN
    machine_id = data.get("machine_id")
    if not isinstance(machine_id, str) or not machine_id or len(machine_id) > 100:
        return {"valid": False, "message": "Thiếu mã máy hợp lệ"}

    code = secrets.token_urlsafe(24)
    expires_at = time.time() + INVITE_TTL_SECONDS
    with get_connection() as conn:
        owner = conn.execute(
            "SELECT 1 FROM machine_managers WHERE machine_id=? AND user_id=? AND role='owner'",
            (machine_id, user_id),
        ).fetchone()
        if owner is None:
            return {"valid": False, "message": "Chỉ chủ máy mới chia sẻ được máy này"}
        conn.execute("DELETE FROM machine_invites WHERE expires_at <= ?", (time.time(),))
        conn.execute(
            "INSERT INTO machine_invites (code_hash, machine_id, created_by, expires_at)"
            " VALUES (?, ?, ?, ?)",
            (hash_code(code), machine_id, user_id, expires_at),
        )
    return {
        "valid": True,
        "code": code,
        "machine_id": machine_id,
        "expires_in": INVITE_TTL_SECONDS,
        "message": "Đã tạo mã chia sẻ",
    }


def accept_invite(data):
    user_id = user_from_request(data)
    if user_id is None:
        return NOT_LOGGED_IN
    code = data.get("code")
    if not isinstance(code, str) or not 20 <= len(code) <= 100:
        return {"valid": False, "message": "Mã chia sẻ không hợp lệ"}

    # Khóa ghi để một mã không được hai người dùng cùng lúc.
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        invite = conn.execute(
            "SELECT i.machine_id, m.name FROM machine_invites i"
            " JOIN machines m ON m.machine_id = i.machine_id"
            " WHERE i.code_hash=? AND i.used_at IS NULL AND i.expires_at > ?",
            (hash_code(code), time.time()),
        ).fetchone()
        if invite is None:
            return {"valid": False, "message": "Mã chia sẻ đã dùng hoặc hết hạn. Nhờ chủ máy tạo mã mới."}
        conn.execute(
            "UPDATE machine_invites SET used_by=?, used_at=datetime('now') WHERE code_hash=?",
            (user_id, hash_code(code)),
        )
        # Chủ quét mã của chính mình thì giữ nguyên quyền owner.
        conn.execute(
            "INSERT OR IGNORE INTO machine_managers (machine_id, user_id, role) VALUES (?, ?, 'manager')",
            (invite["machine_id"], user_id),
        )
    return {
        "valid": True,
        "machine_id": invite["machine_id"],
        "machine_name": invite["name"],
        "message": "Đã nhận quản lý máy",
    }


def list_my_machines(data):
    user_id = user_from_request(data)
    if user_id is None:
        return NOT_LOGGED_IN
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT m.machine_id, m.name, mm.role FROM machine_managers mm"
            " JOIN machines m ON m.machine_id = mm.machine_id"
            " WHERE mm.user_id=? ORDER BY mm.created_at, m.name",
            (user_id,),
        ).fetchall()
    return {"valid": True, "machines": [dict(row) for row in rows]}
