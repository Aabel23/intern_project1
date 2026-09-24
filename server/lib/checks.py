"""Kiểm tra dữ liệu và dọn trạng thái hết hạn, dùng chung giữa các block."""

import re
import time


def is_request_id(value):
    """request_id app tự sinh: 32 ký tự hex."""
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{32}", value) is not None


def is_machine_id(value):
    return isinstance(value, str) and 0 < len(value) <= 100


def remove_expired(states):
    """Xóa các phiên trong RAM đã quá expires_at (time.monotonic); gọi khi đang giữ khóa."""
    now = time.monotonic()
    for key, state in list(states.items()):
        if now >= state["expires_at"]:
            del states[key]
