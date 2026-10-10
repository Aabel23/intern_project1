"""Luồng phía máy: máy xưng key → báo còn sống / lấy lệnh / trả kết quả.

    heartbeat:   key → giữ cho máy cũ, không ghi gì
    poll:        key → ghi đã thấy → chờ lệnh trong hộp thư của chính máy đó
    send_result: key → ghi đã thấy → chuyển kết quả cho request app đang chờ lệnh id đó

Mỗi hàm nhận body JSON đã parse, trả (kết quả, HTTP status).
"""

from server.database.machine.machine_read import find_id_by_key_hash
from server.lib.security.data_hash import sha256_hex
from server.lib.machine.machine_transport import deliver, mark_seen, take


MACHINE_UNKNOWN = {"loi": "Máy chưa đăng ký hoặc sai product key"}


# Xác minh danh tính máy; SQL tra ID nằm trong database.
def machine_from_key(data):
    """machine_id nếu key đúng; None nếu thiếu, sai dạng hoặc chưa đăng ký."""
    key = data.get("product_key")
    if not isinstance(key, str) or not key.strip() or len(key) > 1024:
        return None
    return find_id_by_key_hash(sha256_hex(key))


# Heartbeat: máy báo đang hoạt động, không lấy hoặc thực hiện lệnh.
def heartbeat(data):
    # 1. Xác minh product key trước khi cập nhật trạng thái.
    machine_id = machine_from_key(data)
    if machine_id is None:
        return MACHINE_UNKNOWN, 403
    # 2. Giữ route cho máy cũ; online nay suy từ poll và kết quả, không ghi gì ở đây.
    return {"da_nhan": True}, 200


# Hỏi lệnh: máy chủ động lấy việc từ hộp thư của chính nó.
def poll(data):
    # 1. Xác minh product key để chọn đúng hộp thư.
    machine_id = machine_from_key(data)
    if machine_id is None:
        return MACHINE_UNKNOWN, 403
    # 2. Máy đang hỏi lệnh là vòng lệnh còn chạy; ghi trước khi chờ, không ghi lúc trả về.
    mark_seen(machine_id)
    # 3. Long-poll chờ một lệnh; hết thời gian chờ thì trả lenh=null.
    return {"lenh": take(machine_id)}, 200


# Trả kết quả: máy báo kết quả cho request nghiệp vụ app đang chờ.
def send_result(data):
    # 1. Xác minh máy gửi kết quả.
    machine_id = machine_from_key(data)
    if machine_id is None:
        return MACHINE_UNKNOWN, 403
    # 2. Key đúng nghĩa là máy còn sống, kể cả khi id không khớp lệnh nào.
    mark_seen(machine_id)
    # 3. Transport ghép kết quả bằng machine_id và ID lệnh.
    deliver(machine_id, data.get("id"), data.get("ket_qua"))
    return {"da_nhan": True}, 200
