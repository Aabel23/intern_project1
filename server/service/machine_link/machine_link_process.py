"""Luồng phía máy: máy xưng key → báo còn sống / lấy lệnh / trả kết quả.

    heartbeat:   key → ghi giờ heartbeat
    poll:        key → chờ lệnh trong hộp thư của chính máy đó
    send_result: key → chuyển kết quả cho request app đang chờ lệnh id đó

Mỗi hàm nhận body JSON đã parse, trả (kết quả, HTTP status).
"""

from server.database.machine.machine_read import find_id_by_key_hash
from server.lib.hashing import sha256_hex
from server.lib.machine_transport import deliver, mark_seen, take


MACHINE_UNKNOWN = {"loi": "Máy chưa đăng ký hoặc sai product key"}


def machine_from_key(data):
    """machine_id nếu key đúng; None nếu thiếu, sai dạng hoặc chưa đăng ký."""
    key = data.get("product_key")
    if not isinstance(key, str) or not key.strip() or len(key) > 1024:
        return None
    return find_id_by_key_hash(sha256_hex(key))


def heartbeat(data):
    machine_id = machine_from_key(data)
    if machine_id is None:
        return MACHINE_UNKNOWN, 403
    mark_seen(machine_id)
    return {"da_nhan": True}, 200


def poll(data):
    machine_id = machine_from_key(data)
    if machine_id is None:
        return MACHINE_UNKNOWN, 403
    return {"lenh": take(machine_id)}, 200


def send_result(data):
    machine_id = machine_from_key(data)
    if machine_id is None:
        return MACHINE_UNKNOWN, 403
    deliver(machine_id, data.get("id"), data.get("ket_qua"))
    return {"da_nhan": True}, 200
