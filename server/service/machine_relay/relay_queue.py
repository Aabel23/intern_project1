"""Hộp thư lệnh của từng máy: module nào cần gửi lệnh xuống máy đều đi qua đây.

Máy không nhận kết nối từ ngoài (nằm sau router của quán), nên server không gọi
xuống máy được: module bỏ lệnh vào hộp thư bằng gui_va_cho() rồi chờ, máy
long-poll /machine/hoi-lenh lấy lệnh và gửi kết quả lên /machine/tra-ket-qua
(xem relay_api.py). Mỗi máy chỉ một long-poll cho mọi loại lệnh.
"""

import queue
import threading
import time
from itertools import count

from server.config.config import COMMAND_TIMEOUT_SECONDS, HEARTBEAT_TIMEOUT_SECONDS
from server.database.machine.machine_read import find_id_by_key_hash
from server.lib.hashing import sha256_hex

# Mỗi máy một hộp thư lệnh riêng: machine_id -> danh sách lệnh chờ máy lấy.
HOP_THU = {}
# Lệnh app đang chờ kết quả: id lệnh -> (machine_id, hàng chờ kết quả).
DANG_CHO = {}
KHOA = threading.Lock()
# Báo cho máy đang long-poll khi hộp thư có lệnh mới.
CO_LENH = threading.Condition(KHOA)
DEM_LENH = count(1)
LAN_HEARTBEAT_CUOI = {}
def machine_from_key(data):
    """Máy xưng danh bằng product key trên tem; trả machine_id server đã cấp."""
    key = data.get("product_key")
    if not isinstance(key, str) or not key.strip() or len(key) > 1024:
        return None
    return find_id_by_key_hash(sha256_hex(key))


def last_seen_of(machine_id):
    with KHOA:
        return LAN_HEARTBEAT_CUOI.get(machine_id)


def is_online(machine_id):
    last_seen = last_seen_of(machine_id)
    return last_seen is not None and time.time() - last_seen < HEARTBEAT_TIMEOUT_SECONDS


def gui_va_cho(machine_id, lenh):
    """Bỏ lệnh vào hộp thư của máy rồi chờ máy trả kết quả; hết giờ thì trả dict "loi"."""
    hop_ket_qua = queue.Queue(maxsize=1)
    with KHOA:
        DANG_CHO[lenh["id"]] = (machine_id, hop_ket_qua)
        HOP_THU.setdefault(machine_id, []).append(lenh)
        CO_LENH.notify_all()
    print("Server nhan lenh tu app:", machine_id, lenh, flush=True)

    try:
        ket_qua = hop_ket_qua.get(timeout=COMMAND_TIMEOUT_SECONDS)
    except queue.Empty:
        # Máy chưa lấy lệnh thì hủy, tránh máy chạy lệnh cũ khi online lại.
        with KHOA:
            hop_thu = HOP_THU.get(machine_id, [])
            chua_lay = lenh in hop_thu
            if chua_lay:
                hop_thu.remove(lenh)
        if chua_lay:
            ket_qua = {"loi": "Máy không phản hồi, lệnh đã được hủy"}
        else:
            ket_qua = {"loi": "Máy chưa trả kết quả, hãy tải lại để kiểm tra"}
    with KHOA:
        DANG_CHO.pop(lenh["id"], None)
    return ket_qua
