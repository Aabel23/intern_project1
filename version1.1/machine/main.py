"""Vòng lặp của máy: hỏi server lệnh {id, instruction, data} → chạy → gửi kết quả lên.

main chỉ tra bảng COMMANDS của các module; module tự kiểm lệnh và tự đụng database.
"""

# Thư viện chuẩn
import time
import urllib.error

# Kết nối server
from server_connection import machine_server_request

# Các module: instruction → hàm xử lý
from ingredient_sync.machine_ingredient_request import COMMANDS as INGREDIENT_COMMANDS
from menu_sync.machine_menu_request import COMMANDS as MENU_COMMANDS

COMMANDS = {**MENU_COMMANDS, **INGREDIENT_COMMANDS}


def handle_command(lenh):
    """Chạy một lệnh; lỗi tham số hay lỗi database trả {"loi"} cho app, máy vẫn chạy tiếp."""
    command = COMMANDS.get(lenh.get("instruction"))
    if command is None:
        return {"loi": "Lệnh không hợp lệ"}
    try:
        return command(lenh.get("data") or {})
    except Exception as error:
        return {"loi": str(error)}


def poll():
    """Lệnh kế tiếp, hoặc None khi hết giờ long-poll hay mất kết nối."""
    started = time.monotonic()
    try:
        lenh = machine_server_request.poll_command()
    except (urllib.error.URLError, OSError, ValueError) as error:
        print("Khong ket noi duoc server:", error, flush=True)
        time.sleep(1)
        return None
    # Server trả ngay (không giữ long-poll) thì chờ 1 giây trước khi hỏi lại.
    if lenh is None and time.monotonic() - started < 1:
        time.sleep(1)
    return lenh


def reply(lenh, ket_qua):
    try:
        machine_server_request.send_result(lenh["id"], ket_qua)
    except (urllib.error.URLError, OSError) as error:
        print("Khong gui duoc ket qua:", error, flush=True)


def run():
    # Không có thread heartbeat: server suy online từ chính poll và kết quả của vòng này,
    # nên vòng treo thì máy hiện offline (docs/heartbeat-vs-long-poll.md).
    while True:
        lenh = poll()
        if lenh is None:
            continue
        print("Machine nhan lenh:", lenh, flush=True)
        reply(lenh, handle_command(lenh))


if __name__ == "__main__":
    run()
