"""Lệnh tab Menu máy nhận qua relay: tên lệnh → hàm xử lý.

machine/main.py gộp bảng COMMANDS này; mỗi hàm nhận thamso của lệnh, trả dict
kết quả gửi lên server (xem menu_sync_flow.py).
"""

# Trong module menu_sync
from .menu_sync_flow import gui_menu, nhan_menu

COMMANDS = {
    "nhan_menu": nhan_menu,
    "gui_menu": gui_menu,
}
