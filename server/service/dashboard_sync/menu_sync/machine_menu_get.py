"""Luồng menu: JSON app → (kết quả máy hoặc lỗi, HTTP status)."""

from server.lib.machine.machine_access import check_access
from server.lib.machine.machine_transport import send

QUYEN_MENU = {"owner", "manager"}


def is_menu_version(value):
    # CRC32: số nguyên 0..2^32-1; app chưa có menu gửi 0.
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 2**32


def nhan_menu(data):
    # Bước 1: kiểm phiên và quyền máy; lỗi thì dừng.
    machine_id, error = check_access(data, QUYEN_MENU)
    if error:
        return error

    # Bước 2: kiểm gói tin và chuẩn bị dữ liệu lệnh.
    menu_version = data.get("menu_version", 0)
    if not is_menu_version(menu_version):
        return {"loi": "menu_version không hợp lệ"}, 400
    command_data = {"menu_version": menu_version}

    # Bước 3: giao lệnh, chờ máy trả kết quả hoặc lỗi transport.
    return send(machine_id, "nhan_menu", command_data)
