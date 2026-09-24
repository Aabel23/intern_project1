"""Nhận thông tin máy (QR/Bluetooth) -> kiểm tra -> lưu máy, gán chủ -> trả ID cho app."""

from uuid import uuid4

from server.config.routing import APP_REGISTER_MACHINE_VERIFY
from server.database.connection import get_connection
from server.service.user_login.session import user_from_request
from .machine_register_verify import hash_product_key, verify_machine


def receive_register(data):
    error = verify_machine(data)
    if error:
        return {"valid": False, "message": error}

    user_id = user_from_request(data)
    if user_id is None:
        return {"valid": False, "message": "Phiên đăng nhập hết hạn, hãy đăng nhập lại"}

    name = data["machine_name"].strip()
    key_hash = hash_product_key(data["product_key"])

    # Khóa ghi SQLite để hai request cùng key không tạo hai máy.
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT machine_id FROM machines WHERE product_key_hash=?", (key_hash,)
        ).fetchone()
        created = row is None
        if created:
            machine_id = "fm_" + uuid4().hex
            conn.execute(
                "INSERT INTO machines (machine_id, name, product_key_hash) VALUES (?, ?, ?)",
                (machine_id, name, key_hash),
            )
        else:
            machine_id = row["machine_id"]
        # Người đầu tiên quét tem thành chủ máy; người khác phải được chủ chia sẻ.
        owner = conn.execute(
            "SELECT user_id FROM machine_managers WHERE machine_id=? AND role='owner'",
            (machine_id,),
        ).fetchone()
        if owner is None:
            conn.execute(
                "INSERT INTO machine_managers (machine_id, user_id, role) VALUES (?, ?, 'owner')"
                " ON CONFLICT (machine_id, user_id) DO UPDATE SET role='owner'",
                (machine_id, user_id),
            )
        elif owner["user_id"] != user_id:
            return {"valid": False, "message": "Máy đã thuộc tài khoản khác. Hãy nhờ chủ máy chia sẻ."}

    return {
        "valid": True,
        "registered": True,
        "created": created,
        "machine_id": machine_id,
        "verify_route": APP_REGISTER_MACHINE_VERIFY,
        "message": "Đăng ký máy thành công" if created else "Máy đã được đăng ký",
    }
