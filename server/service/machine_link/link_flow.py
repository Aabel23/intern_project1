"""Luồng phía máy: máy xưng key → báo còn sống / lấy lệnh / trả kết quả.

    heartbeat:   key → ghi giờ heartbeat
    poll:        key → chờ lệnh trong hộp thư của chính máy đó
    send_result: key → chuyển kết quả cho request app đang chờ lệnh id đó

Mỗi hàm nhận body JSON đã parse, trả (kết quả, HTTP status).
"""

# Trong module machine_link
from .link_queue import deliver, mark_seen, take
from .link_verify import MACHINE_UNKNOWN, machine_from_key


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
