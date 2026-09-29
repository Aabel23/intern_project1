import time

from server.database.connection import get_connection
from server.database.machine import machine_share_store as store
from server.lib.http.http_json import invalid
from server.lib.security.user_session import check_login
from server.lib.security.data_hash import sha256_hex


INVITE_CODE_MIN_LENGTH = 20
INVITE_CODE_MAX_LENGTH = 100


def is_code(code):
    return isinstance(code, str) and INVITE_CODE_MIN_LENGTH <= len(code) <= INVITE_CODE_MAX_LENGTH


def accept_invite(data):
    # 1. Kiểm phiên đăng nhập và định dạng mã mời.
    user_id, error = check_login(data)
    if error:
        return error
    code = data.get("code")
    if not is_code(code):
        return invalid("Mã chia sẻ không hợp lệ")
    # 2. Khóa ghi để một mã không được hai người dùng cùng lúc.
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        invite = store.find_valid_invite(conn, sha256_hex(code), time.time())
        if invite is None:
            return invalid("Mã chia sẻ đã dùng hoặc hết hạn. Nhờ chủ máy tạo mã mới.")
        # 3. Đánh dấu dùng và cấp quyền cùng commit/rollback.
        store.mark_used(conn, sha256_hex(code), user_id)
        # Chủ quét mã của chính mình thì giữ nguyên quyền owner.
        store.add_manager(conn, invite["machine_id"], user_id)
    return {
        "valid": True,
        "machine_id": invite["machine_id"],
        "machine_name": invite["name"],
        "message": "Đã nhận quản lý máy",
    }
