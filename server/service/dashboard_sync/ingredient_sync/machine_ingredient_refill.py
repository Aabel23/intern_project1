"""Nạp kho: JSON app → (kết quả máy hoặc lỗi, HTTP status)."""

from server.lib.machine.machine_access import check_access
from server.lib.machine.machine_transport import send

QUYEN_NAP_KHO = {"owner", "manager"}
MAX_GRAM = 99999999.99


# Nhóm 1: kiểm nguyên liệu và lượng cần nạp.
def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_target(target):
    # Một nguyên liệu (id > 0) hoặc "all".
    return target == "all" or (isinstance(target, int) and not isinstance(target, bool) and target > 0)


def is_value(target, value):
    # "full" = đổ đầy tới max_gram; số gram chỉ hợp lệ khi nạp một nguyên liệu.
    return value == "full" or (target != "all" and is_number(value) and 0 <= value <= MAX_GRAM)


def is_refill(target, value):
    return is_target(target) and is_value(target, value)


# Nhóm 2: luồng chính được machine_ingredient_main gọi.
def nap_kho(data):
    # Bước 1: kiểm phiên và quyền máy trước khi kiểm nội dung.
    machine_id, error = check_access(data, QUYEN_NAP_KHO)
    if error:
        return error

    # Bước 2: kiểm gói nạp một nguyên liệu hoặc toàn bộ kho.
    target, value = data.get("target"), data.get("value")
    if not is_refill(target, value):
        return {"loi": "Gói nạp kho không hợp lệ"}, 400

    # Bước 3: giao lệnh và chờ máy; giữ cả warning nếu máy đã nạp nhưng dựng menu lỗi.
    return send(machine_id, "nap_kho", {"target": target, "value": value})
