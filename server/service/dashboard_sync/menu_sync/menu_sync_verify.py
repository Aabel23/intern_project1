"""Kiểm tra dạng gói tab Menu app gửi lên; không đọc/ghi HTTP, không đụng database.

Quyền với máy kiểm ở sync_rules.check_access(), dùng chung cho các tab dashboard.
"""

MAX_CHANGES = 200
MAX_PRICE = 99999999.99


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_menu_version(value):
    # CRC32: số nguyên 0..2^32-1; app chưa có menu gửi 0.
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 2**32


def is_drink_id(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def is_price(value):
    return is_number(value) and 0 <= value <= MAX_PRICE


def is_available(value):
    return isinstance(value, bool)


# Cột app được sửa → hàm kiểm giá trị; máy cũng chỉ ghi đúng các cột này.
EDITABLE = {"available": is_available, "price": is_price}


def is_change(change):
    """Một dòng thay_doi: {drink_id, available?, price?}, ít nhất một cột được sửa."""
    if not isinstance(change, dict) or not is_drink_id(change.get("drink_id")):
        return False
    fields = {key: value for key, value in change.items() if key != "drink_id"}
    return bool(fields) and all(key in EDITABLE and EDITABLE[key](value) for key, value in fields.items())


def is_changes(thay_doi):
    return isinstance(thay_doi, list) and 1 <= len(thay_doi) <= MAX_CHANGES and all(map(is_change, thay_doi))
