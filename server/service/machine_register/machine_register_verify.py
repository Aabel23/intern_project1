"""Kiểm tra gói app gửi; chưa có danh sách key nhà máy để đối chiếu."""

import hashlib

from server.database.connection import get_connection


def verify_machine(data):
    if not isinstance(data, dict):
        return "Dữ liệu phải là JSON object"
    name = data.get("machine_name")
    key = data.get("product_key")
    if not isinstance(name, str) or not name.strip() or len(name) > 150:
        return "Tên máy không hợp lệ"
    if not isinstance(key, str) or not key.strip() or len(key) > 1024:
        return "Product key không hợp lệ"
    return None


def hash_product_key(key):
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def verify_registration(data):
    # App đối chiếu ID server trả về với key đang giữ sau Bluetooth.
    if not isinstance(data, dict):
        return {"valid": False, "message": "Dữ liệu phải là JSON object"}
    machine_id = data.get("machine_id")
    key = data.get("product_key")
    if not isinstance(machine_id, str) or not machine_id or len(machine_id) > 100:
        return {"valid": False, "message": "Thiếu mã máy hợp lệ"}
    if not isinstance(key, str) or not key.strip() or len(key) > 1024:
        return {"valid": False, "message": "Product key không hợp lệ"}

    key_hash = hash_product_key(key)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT machine_id FROM machines WHERE machine_id=? AND product_key_hash=?",
            (machine_id, key_hash),
        ).fetchone()
    if row is None:
        return {"valid": False, "verified": False, "message": "Thông tin đăng ký máy không khớp"}
    return {"valid": True, "verified": True, "machine_id": row["machine_id"],
            "message": "Đã xác minh đăng ký máy"}
