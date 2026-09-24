"""Chủ máy tạo mã mời dạng QR, nhân viên quét để được giao quản lý máy."""

import hashlib
import secrets
import time

from server.config.config import (
    INVITE_CODE_BYTES,
    INVITE_CODE_MAX_LENGTH,
    INVITE_CODE_MIN_LENGTH,
    INVITE_TTL_SECONDS,
)
from server.database.connection import get_connection
from server.database.machine import machine_invite, machine_read, machine_write
from server.service.user_login.session import NOT_LOGGED_IN, user_from_request


def hash_code(code):
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def create_invite(data):
    user_id = user_from_request(data)
    if user_id is None:
        return NOT_LOGGED_IN
    machine_id = data.get("machine_id")
    if not isinstance(machine_id, str) or not machine_id or len(machine_id) > 100:
        return {"valid": False, "message": "Thiếu mã máy hợp lệ"}

    code = secrets.token_urlsafe(INVITE_CODE_BYTES)
    expires_at = time.time() + INVITE_TTL_SECONDS
    with get_connection() as conn:
        if not machine_read.is_owner(machine_id, user_id, conn):
            return {"valid": False, "message": "Chỉ chủ máy mới chia sẻ được máy này"}
        # Tạo mã mới thì mã cũ chưa dùng của máy này hết hiệu lực.
        machine_invite.replace_invite(
            conn, hash_code(code), machine_id, user_id, expires_at, time.time()
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
    if not isinstance(code, str) or not INVITE_CODE_MIN_LENGTH <= len(code) <= INVITE_CODE_MAX_LENGTH:
        return {"valid": False, "message": "Mã chia sẻ không hợp lệ"}

    # Khóa ghi để một mã không được hai người dùng cùng lúc.
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        invite = machine_invite.find_valid_invite(conn, hash_code(code), time.time())
        if invite is None:
            return {"valid": False, "message": "Mã chia sẻ đã dùng hoặc hết hạn. Nhờ chủ máy tạo mã mới."}
        machine_invite.mark_used(conn, hash_code(code), user_id)
        # Chủ quét mã của chính mình thì giữ nguyên quyền owner.
        machine_write.add_manager(conn, invite["machine_id"], user_id)
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
    return {"valid": True, "machines": machine_read.list_by_user(user_id)}


def list_staff(data):
    """Chủ máy xem nhân viên đang được giao máy để thu hồi khi cần."""
    user_id = user_from_request(data)
    if user_id is None:
        return NOT_LOGGED_IN
    machine_id = data.get("machine_id")
    if not isinstance(machine_id, str) or not machine_id:
        return {"valid": False, "message": "Thiếu mã máy hợp lệ"}
    with get_connection() as conn:
        if not machine_read.is_owner(machine_id, user_id, conn):
            return {"valid": False, "message": "Chỉ chủ máy mới xem được nhân viên"}
        staff = machine_read.list_staff(machine_id, conn)
    return {"valid": True, "staff": staff}


def revoke_staff(data):
    """Chủ máy thu hồi quyền của một nhân viên; không xóa được quyền chủ."""
    user_id = user_from_request(data)
    if user_id is None:
        return NOT_LOGGED_IN
    machine_id = data.get("machine_id")
    staff_id = data.get("user_id")
    if not isinstance(machine_id, str) or not machine_id or not isinstance(staff_id, int):
        return {"valid": False, "message": "Thiếu mã máy hoặc nhân viên"}
    with get_connection() as conn:
        if not machine_read.is_owner(machine_id, user_id, conn):
            return {"valid": False, "message": "Chỉ chủ máy mới thu hồi được quyền"}
        machine_write.remove_manager(conn, machine_id, staff_id)
    return {"valid": True, "message": "Đã thu hồi quyền nhân viên"}
