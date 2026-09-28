"""Lệnh tab Kho máy nhận qua relay: instruction → hàm xử lý.

machine/main.py gộp bảng COMMANDS này; mỗi hàm nhận data của lệnh, trả dict
kết quả gửi lên server (xem ingredient_sync_flow.py).
"""

# Trong module ingredient_sync
from .ingredient_sync_flow import nap_kho, nhan_kho

COMMANDS = {
    "nhan_kho": nhan_kho,
    "nap_kho": nap_kho,
}
