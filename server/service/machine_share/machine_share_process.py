"""Luồng chia sẻ máy: chủ tạo mã mời (QR), nhân viên quét để được giao quản lý máy.

    create_invite: đăng nhập → mã máy → phải là chủ → mã mới (mã cũ chưa dùng hết hiệu lực)
    accept_invite: đăng nhập → mã đúng dạng → khóa ghi → mã còn hạn → đánh dấu đã dùng → thêm nhân viên
    list_staff:    đăng nhập → mã máy → phải là chủ → danh sách nhân viên
    revoke_staff:  đăng nhập → mã máy + nhân viên → phải là chủ → bỏ quyền (không xóa được quyền chủ)

Mỗi hàm nhận body JSON đã parse, trả thân {"valid", "message", ...}; api gắn status theo valid.
"""

import secrets
import time

from server.database.connection import get_connection
from server.database.machine import machine_read, machine_write
from server.lib.checks import is_machine_id
from server.lib.hashing import sha256_hex
from server.lib.http_json import invalid
from server.lib.session import check_login

from . import machine_share_store as store


# Mã mời chia sẻ máy, dùng một lần.
INVITE_TTL_SECONDS = 5 * 60
# 24 byte ngẫu nhiên -> mã base64url 32 ký tự.
INVITE_CODE_BYTES = 24
INVITE_CODE_MIN_LENGTH = 20
INVITE_CODE_MAX_LENGTH = 100


def check_request(data):
    """Trả (user_id, machine_id, None) nếu đã đăng nhập và mã máy đúng dạng, sai thì (None, None, lỗi)."""
    user_id, error = check_login(data)
    if error:
        return None, None, error
    machine_id = data.get("machine_id")
    if not is_machine_id(machine_id):
        return None, None, invalid("Thiếu mã máy hợp lệ")
    return user_id, machine_id, None


def is_code(code):
    return isinstance(code, str) and INVITE_CODE_MIN_LENGTH <= len(code) <= INVITE_CODE_MAX_LENGTH


def is_staff_id(value):
    return isinstance(value, int) and not isinstance(value, bool)


def create_invite(data):
    user_id, machine_id, error = check_request(data)
    if error:
        return error
    code = secrets.token_urlsafe(INVITE_CODE_BYTES)
    with get_connection() as conn:
        if not machine_read.is_owner(machine_id, user_id, conn):
            return invalid("Chỉ chủ máy mới chia sẻ được máy này")
        store.replace_invite(
            conn, sha256_hex(code), machine_id, user_id, time.time() + INVITE_TTL_SECONDS, time.time()
        )
    return {
        "valid": True,
        "code": code,
        "machine_id": machine_id,
        "expires_in": INVITE_TTL_SECONDS,
        "message": "Đã tạo mã chia sẻ",
    }


def accept_invite(data):
    user_id, error = check_login(data)
    if error:
        return error
    code = data.get("code")
    if not is_code(code):
        return invalid("Mã chia sẻ không hợp lệ")
    # Khóa ghi để một mã không được hai người dùng cùng lúc.
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        invite = store.find_valid_invite(conn, sha256_hex(code), time.time())
        if invite is None:
            return invalid("Mã chia sẻ đã dùng hoặc hết hạn. Nhờ chủ máy tạo mã mới.")
        store.mark_used(conn, sha256_hex(code), user_id)
        # Chủ quét mã của chính mình thì giữ nguyên quyền owner.
        store.add_manager(conn, invite["machine_id"], user_id)
    return {
        "valid": True,
        "machine_id": invite["machine_id"],
        "machine_name": invite["name"],
        "message": "Đã nhận quản lý máy",
    }


def list_staff(data):
    """Chủ máy xem nhân viên đang được giao máy để thu hồi khi cần."""
    user_id, machine_id, error = check_request(data)
    if error:
        return error
    with get_connection() as conn:
        if not machine_read.is_owner(machine_id, user_id, conn):
            return invalid("Chỉ chủ máy mới xem được nhân viên")
        staff = store.list_staff(machine_id, conn)
    return {"valid": True, "staff": staff}


def revoke_staff(data):
    """Chủ máy thu hồi quyền của một nhân viên; không xóa được quyền chủ."""
    user_id, error = check_login(data)
    if error:
        return error
    machine_id, staff_id = data.get("machine_id"), data.get("user_id")
    if not is_machine_id(machine_id) or not is_staff_id(staff_id):
        return invalid("Thiếu mã máy hoặc nhân viên")
    with get_connection() as conn:
        if not machine_read.is_owner(machine_id, user_id, conn):
            return invalid("Chỉ chủ máy mới thu hồi được quyền")
        machine_write.remove_manager(conn, machine_id, staff_id)
    return {"valid": True, "message": "Đã thu hồi quyền nhân viên"}
