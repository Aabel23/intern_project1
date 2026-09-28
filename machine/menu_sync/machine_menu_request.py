"""Lệnh tab Menu máy nhận qua relay: instruction → hàm xử lý.

machine/main.py gộp bảng COMMANDS này; mỗi hàm nhận data của lệnh, trả dict
kết quả gửi lên server (xem machine_menu_sync.py).
"""

# Trong module menu_sync
from .machine_menu_sync import gui_menu, nhan_menu

COMMANDS = {
    "nhan_menu": nhan_menu,
    "gui_menu": gui_menu,
}
