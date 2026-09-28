"""Nhận thông tin máy (QR/Bluetooth) -> kiểm tra -> lưu máy, gán chủ -> trả ID cho app."""

from server.database.connection import get_connection
from server.database.machine.machine_read import find_id_by_key_hash, get_owner_id
from server.database.machine.machine_write import add_machine, set_owner
from server.service.user_login.session import NOT_LOGGED_IN, user_from_request
from server.lib.hashing import sha256_hex
from .machine_register_verify import verify_machine


def receive_register(data):
    error = verify_machine(data)
    if error:
        return {"valid": False, "message": error}

    user_id = user_from_request(data)
    if user_id is None:
        return NOT_LOGGED_IN

    name = data["machine_name"].strip()
    key_hash = sha256_hex(data["product_key"])

    # Khóa ghi SQLite để hai request cùng key không tạo hai máy.
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        machine_id = find_id_by_key_hash(key_hash, conn)
        created = machine_id is None
        if created:
            machine_id = add_machine(conn, name, key_hash)
        # Người đầu tiên quét tem thành chủ máy; người khác phải được chủ chia sẻ.
        owner_id = get_owner_id(machine_id, conn)
        if owner_id is None:
            set_owner(conn, machine_id, user_id)
        elif owner_id != user_id:
            return {"valid": False, "message": "Máy đã thuộc tài khoản khác. Hãy nhờ chủ máy chia sẻ."}

    return {
        "valid": True,
        "registered": True,
        "created": created,
        "machine_id": machine_id,
        "message": "Đăng ký máy thành công" if created else "Máy đã được đăng ký",
    }
