"""Kiểm tra lệnh kho server chuyển xuống trước khi đụng database.

Server đã kiểm quyền người dùng và dạng gói; máy kiểm lại dạng để không ghi bậy
nếu gói bị sửa trên đường. Sai thì raise ValueError, vòng lặp máy trả {"loi": ...}.
"""


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def check_version(data):
    version = data.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 0:
        raise ValueError("version không hợp lệ")
    return version


def check_refill(data):
    """Trả (target, value): target = id > 0 hoặc "all"; value = "full" hoặc số gram ≥ 0."""
    target, value = data.get("target"), data.get("value")
    target_ok = target == "all" or (isinstance(target, int) and not isinstance(target, bool) and target > 0)
    value_ok = value == "full" or (target != "all" and is_number(value) and value >= 0)
    if not target_ok or not value_ok:
        raise ValueError("Gói nạp kho không hợp lệ")
    return target, value
