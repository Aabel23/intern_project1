"""Kiểm tra dạng gói tab Kho app gửi lên; không đọc/ghi HTTP, không đụng database.

Quyền với máy kiểm ở sync_rules.check_access(), dùng chung cho các tab dashboard.
"""

MAX_GRAM = 99999999.99


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_version(value):
    # CRC32: số nguyên 0..2^32-1; app chưa có danh sách kho gửi 0.
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 2**32


def is_target(target):
    # Một nguyên liệu (id > 0) hoặc "all".
    return target == "all" or (isinstance(target, int) and not isinstance(target, bool) and target > 0)


def is_value(target, value):
    # "full" = đổ đầy tới max_gram; số gram chỉ hợp lệ khi nạp một nguyên liệu.
    return value == "full" or (target != "all" and is_number(value) and 0 <= value <= MAX_GRAM)


def is_refill(target, value):
    return is_target(target) and is_value(target, value)
