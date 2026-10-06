import secrets
import time

from server.database.connection import get_connection
from server.database.machine import machine_read
from server.lib.http.http_json import invalid
from server.lib.security.user_session import check_login
from server.lib.validation.identifier_validate import is_machine_id
from server.lib.security.data_hash import sha256_hex
from server.database.machine import machine_share_store as store


INVITE_TTL_SECONDS = 5 * 60
INVITE_CODE_BYTES = 24


def create_invite(data):
    # 1. Kiểm phiên đăng nhập và mã máy.
    user_id, error = check_login(data)
    if error:
        return error
    machine_id = data.get("machine_id")
    if not is_machine_id(machine_id):
        return invalid("Thiếu mã máy hợp lệ")
    # 2. Sinh mã; kiểm quyền chủ và lưu hash trong cùng transaction.
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
