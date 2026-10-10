"""Công cụ stress CRC menu máy: quyền MANAGER đổi menu liên tục qua API thật.

harness  — dựng server thật + vòng lặp machine/main.py thật (SQLite tạm).
oracle   — tự tính CRC/giải gói độc lập, không import code máy/server.
scenario — vòng lặp đổi menu, so CRC, khôi phục menu gốc, thống kê.
Chạy: python -m tests.tools.menu_crc_stress [--iterations N] [--seed S] [--json PATH]
"""
