"""Luồng tab Kho: quyền → dạng gói → gửi lệnh cho máy → trả nguyên kết quả máy.

    nhan_kho: quyền xem kho → version → máy trả up_to_date hoặc danh sách kho mới
    nap_kho:  quyền nạp kho → target + value → máy nạp rồi trả kết quả

Mỗi hàm nhận body JSON đã parse, trả (kết quả, HTTP status); đọc/ghi HTTP nằm ở
machine_ingredient_request.py. Server không lưu dữ liệu kho, chỉ chuyển qua lại.
"""

# Tài nguyên chung: kiểm quyền và vận chuyển lệnh tới máy
from server.lib.machine_access import check_access
from server.lib.machine_transport import send

# Trong module ingredient_sync
from .machine_ingredient_validate import is_refill, is_version

QUYEN_KHO = {"owner", "manager"}
QUYEN_NAP_KHO = {"owner", "manager"}


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
