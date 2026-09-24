"""Kiểm tra gói app gửi; chưa có danh sách key nhà máy để đối chiếu."""

from server.database.machine.machine_read import matches_key
from server.lib.checks import is_machine_id
from server.lib.hashing import sha256_hex


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


def verify_registration(data):
    # App đối chiếu ID server trả về với key đang giữ sau Bluetooth.
    if not isinstance(data, dict):
        return {"valid": False, "message": "Dữ liệu phải là JSON object"}
    machine_id = data.get("machine_id")
    key = data.get("product_key")
    if not is_machine_id(machine_id):
        return {"valid": False, "message": "Thiếu mã máy hợp lệ"}
    if not isinstance(key, str) or not key.strip() or len(key) > 1024:
        return {"valid": False, "message": "Product key không hợp lệ"}

    if not matches_key(machine_id, sha256_hex(key)):
        return {"valid": False, "verified": False, "message": "Thông tin đăng ký máy không khớp"}
    return {"valid": True, "verified": True, "machine_id": machine_id,
            "message": "Đã xác minh đăng ký máy"}
