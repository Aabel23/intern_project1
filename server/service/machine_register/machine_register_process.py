"""Luồng đăng ký máy: gói hợp lệ → đăng nhập → lưu máy (nếu mới) → gán chủ → trả ID.

    receive_register: người đầu tiên quét tem thành chủ; người khác phải được chủ chia sẻ.
                      Gửi lại cùng key trả cùng ID, không tạo bản ghi mới.

Nhận body JSON đã parse, trả thân {"valid", "message", ...}; api gắn status theo valid.
"""

from server.database.connection import get_connection
from server.database.machine.machine_read import find_id_by_key_hash, get_owner_id
from server.lib.hashing import sha256_hex
from server.lib.http_json import invalid
from server.lib.session import check_login

from .machine_register_store import add_machine, set_owner


def is_text(value, max_length):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= max_length


def check_machine(data):
    """Tên máy 1-150 ký tự, product key 1-1024 ký tự; trả lỗi hoặc None."""
    if not is_text(data.get("machine_name"), 150):
        return invalid("Tên máy không hợp lệ")
    if not is_text(data.get("product_key"), 1024):
        return invalid("Product key không hợp lệ")
    return None


def receive_register(data):
    error = check_machine(data)
    if error:
        return error
    user_id, error = check_login(data)
    if error:
        return error
    name = data["machine_name"].strip()
    key_hash = sha256_hex(data["product_key"])
    # Khóa ghi SQLite để hai request cùng key không tạo hai máy.
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        machine_id = find_id_by_key_hash(key_hash, conn)
        created = machine_id is None
        if created:
            machine_id = add_machine(conn, name, key_hash)
        owner_id = get_owner_id(machine_id, conn)
        if owner_id is None:
            set_owner(conn, machine_id, user_id)
        if owner_id not in (None, user_id):
            return invalid("Máy đã thuộc tài khoản khác. Hãy nhờ chủ máy chia sẻ.")
    return {
        "valid": True,
        "registered": True,
        "created": created,
        "machine_id": machine_id,
        "message": "Đăng ký máy thành công" if created else "Máy đã được đăng ký",
    }
