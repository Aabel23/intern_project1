"""Luồng tab Kho: quyền → dạng gói → gửi lệnh cho máy → trả nguyên kết quả máy.

    nhan_kho: quyền xem kho → version → máy trả up_to_date hoặc danh sách kho mới
    nap_kho:  quyền nạp kho → target + value → máy nạp rồi trả kết quả

Mỗi hàm nhận body JSON đã parse, trả (kết quả, HTTP status); đọc/ghi HTTP nằm ở
ingredient_sync_api.py. Server không lưu dữ liệu kho, chỉ chuyển qua lại.
"""

# Module khác: quyền của tab dashboard, hộp thư lệnh của máy
from server.service.dashboard_sync.sync_rules import QUYEN_KHO, QUYEN_NAP_KHO, check_access
from server.service.machine_link.link_queue import send

# Trong module ingredient_sync
from .ingredient_sync_verify import is_refill, is_version


def nhan_kho(data):
    # {token, machine_id, version}
    machine_id, error = check_access(data, QUYEN_KHO)
    if error:
        return error
    version = data.get("version", 0)
    if not is_version(version):
        return {"loi": "version không hợp lệ"}, 400
    return send(machine_id, "nhan_kho", {"version": version})


def nap_kho(data):
    # {token, machine_id, target: id | "all", value: "full" | số gram}
    machine_id, error = check_access(data, QUYEN_NAP_KHO)
    if error:
        return error
    target, value = data.get("target"), data.get("value")
    if not is_refill(target, value):
        return {"loi": "Gói nạp kho không hợp lệ"}, 400
    return send(machine_id, "nap_kho", {"target": target, "value": value})
