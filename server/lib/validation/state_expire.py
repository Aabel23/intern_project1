"""Dọn trạng thái hết hạn trong RAM; nơi gọi chịu trách nhiệm khóa."""

import time


def remove_expired(states):
    """Xóa các phiên trong RAM đã quá expires_at (time.monotonic); gọi khi đang giữ khóa."""
    now = time.monotonic()
    for key, state in list(states.items()):
        if now >= state["expires_at"]:
            del states[key]
