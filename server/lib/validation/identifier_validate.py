"""Kiểm tra định dạng ID dùng chung."""

import re


def is_request_id(value):
    """request_id app tự sinh: 32 ký tự hex."""
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{32}", value) is not None


def is_machine_id(value):
    return isinstance(value, str) and 0 < len(value) <= 100
