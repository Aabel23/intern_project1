"""Kiểm tra máy gọi lên: product key trên tem → machine_id server đã cấp."""

# Server chung: database máy, băm key
from server.database.machine.machine_read import find_id_by_key_hash
from server.lib.hashing import sha256_hex

MACHINE_UNKNOWN = {"loi": "Máy chưa đăng ký hoặc sai product key"}


def machine_from_key(data):
    """machine_id nếu key đúng; None nếu thiếu, sai dạng hoặc chưa đăng ký."""
    key = data.get("product_key")
    if not isinstance(key, str) or not key.strip() or len(key) > 1024:
        return None
    return find_id_by_key_hash(sha256_hex(key))
