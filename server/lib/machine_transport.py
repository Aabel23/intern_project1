"""Hộp thư lệnh của từng máy và giờ heartbeat; chỉ nằm trong RAM.

Máy nằm sau router của quán nên server không gọi xuống máy được. Module cần máy
làm gì thì gọi send(): lệnh {id, instruction, data} nằm trong hộp thư tới khi
máy long-poll lên lấy (take), máy làm xong gửi kết quả lên (deliver) và send()
trả kết quả đó. Mỗi máy chỉ một long-poll cho mọi loại lệnh.
"""

# Thư viện chuẩn
import queue
import threading
import time
from itertools import count

# Server chung: cấu hình
from server.config.config import COMMAND_TIMEOUT_SECONDS, HEARTBEAT_TIMEOUT_SECONDS, POLL_WAIT_SECONDS

# machine_id -> các lệnh chờ máy lấy.
HOP_THU = {}
# id lệnh -> (machine_id, hàng chờ nhận kết quả của send() đang đợi).
DANG_CHO = {}
KHOA = threading.Lock()
# Đánh thức máy đang long-poll khi hộp thư có lệnh mới.
CO_LENH = threading.Condition(KHOA)
DEM_LENH = count(1)
# machine_id -> time.time() lần heartbeat cuối.
LAN_HEARTBEAT_CUOI = {}


def mark_seen(machine_id):
    with KHOA:
        LAN_HEARTBEAT_CUOI[machine_id] = time.time()


def last_seen_of(machine_id):
    with KHOA:
        return LAN_HEARTBEAT_CUOI.get(machine_id)


def is_online(machine_id):
    last_seen = last_seen_of(machine_id)
    return last_seen is not None and time.time() - last_seen < HEARTBEAT_TIMEOUT_SECONDS


def send(machine_id, instruction, data):
    """Gửi lệnh cho máy và chờ kết quả; trả (thân JSON trả app, HTTP status).

    Thành công: (kết quả máy trả, 200). Lỗi: ({"loi": câu cho người dùng}, status),
    503 khi máy offline, 502 khi máy báo lỗi hoặc không trả lời kịp.
    """
    if not is_online(machine_id):
        return {"loi": "Máy đang offline"}, 503
    lenh = {"id": next(DEM_LENH), "instruction": instruction, "data": data}
    hop_ket_qua = queue.Queue(maxsize=1)
    with KHOA:
        DANG_CHO[lenh["id"]] = (machine_id, hop_ket_qua)
        HOP_THU.setdefault(machine_id, []).append(lenh)
        CO_LENH.notify_all()
    try:
        ket_qua = hop_ket_qua.get(timeout=COMMAND_TIMEOUT_SECONDS)
    except queue.Empty:
        return {"loi": timeout_message(machine_id, lenh)}, 502
    finally:
        with KHOA:
            DANG_CHO.pop(lenh["id"], None)
    if not isinstance(ket_qua, dict):
        return {"loi": "Máy trả kết quả không đúng dạng"}, 502
    return ket_qua, 502 if "loi" in ket_qua else 200


def timeout_message(machine_id, lenh):
    """Máy chưa lấy lệnh thì hủy, để máy không chạy lệnh cũ khi online lại."""
    with KHOA:
        hop_thu = HOP_THU.get(machine_id, [])
        chua_lay = lenh in hop_thu
        if chua_lay:
            hop_thu.remove(lenh)
    if chua_lay:
        return "Máy không phản hồi, lệnh đã được hủy"
    return "Máy chưa trả kết quả, hãy tải lại để kiểm tra"


def take(machine_id):
    """Long-poll: chờ tối đa POLL_WAIT_SECONDS, có lệnh là trả ngay; None nếu hết giờ."""
    with CO_LENH:
        CO_LENH.wait_for(lambda: HOP_THU.get(machine_id), timeout=POLL_WAIT_SECONDS)
        hop_thu = HOP_THU.get(machine_id)
        return hop_thu.pop(0) if hop_thu else None


def deliver(machine_id, lenh_id, ket_qua):
    """Chuyển kết quả cho send() đang chờ, chỉ khi lệnh đó được giao cho đúng máy này."""
    with KHOA:
        cho = DANG_CHO.get(lenh_id)
    if cho is None or cho[0] != machine_id:
        return
    try:
        cho[1].put_nowait(ket_qua)
    except queue.Full:
        pass
