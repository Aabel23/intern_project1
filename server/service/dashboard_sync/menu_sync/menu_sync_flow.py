"""Luồng tab Menu: xỏ kiểm tra (menu_sync_verify) với chuyển lệnh xuống máy.

    nhan_menu: quyền → menu_version → máy trả up_to_date hoặc gói menu mới
    gui_menu:  quyền → menu_version + thay_doi → máy ghi rồi trả gói mới (hoặc conflict)

Mỗi hàm nhận body JSON đã parse, trả (kết quả, HTTP status); đọc/ghi HTTP nằm ở
menu_sync_api.py. Gói menu (base64 zlib) đi nguyên từ máy tới app, server không
giải nén, không lưu. Cấu trúc gói: machine/menu_sync/menu_sync_packet.py.

Chạy riêng module (chỉ có route menu + relay để máy nhận lệnh):
    python -m server.service.dashboard_sync.menu_sync.menu_sync_flow --port 8000
"""

# Thư viện chuẩn
import argparse
import sys

# Server chung: cấu hình, database, khung server (chỉ dùng khi chạy riêng)
from server.config.config import SERVER_HOST, SERVER_PORT
from server.database.machine.init_db import init_db
from server.lib.module_server import ModuleServer, make_handler

# Module khác: relay để máy nhận lệnh khi chạy riêng
from server.service.machine_relay import relay_api

# Trong module menu_sync
from . import menu_sync_api
from .menu_sync_verify import check_access, is_changes, is_menu_version, send_to_machine


def nhan_menu(data):
    # {token, machine_id, menu_version}
    machine_id, error = check_access(data)
    if error:
        return error
    menu_version = data.get("menu_version", 0)
    if not is_menu_version(menu_version):
        return {"loi": "menu_version không hợp lệ"}, 400
    return send_to_machine(machine_id, "nhan_menu", {"menu_version": menu_version})


def gui_menu(data):
    # {token, machine_id, menu_version, thay_doi: [{drink_id, available?, price?}]}.
    # menu_version là bản app đang sửa; máy từ chối (conflict) nếu đã có bản mới hơn.
    machine_id, error = check_access(data)
    if error:
        return error
    menu_version, thay_doi = data.get("menu_version"), data.get("thay_doi")
    if not is_menu_version(menu_version) or not is_changes(thay_doi):
        return {"loi": "Gói thay đổi menu không hợp lệ"}, 400
    return send_to_machine(machine_id, "gui_menu", {"menu_version": menu_version, "thay_doi": thay_doi})


def run_standalone(port):
    """Server chỉ gồm tab Menu và relay (máy cần heartbeat, hỏi lệnh, trả kết quả)."""
    modules = (menu_sync_api, relay_api)
    init_db()
    with ModuleServer((SERVER_HOST, port), make_handler(modules)) as server:
        server.modules = modules
        print(f"Menu sync chạy riêng: http://{SERVER_HOST}:{port}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Chạy riêng module menu sync.")
    parser.add_argument("--port", type=int, default=SERVER_PORT)
    try:
        run_standalone(parser.parse_args().port)
    except KeyboardInterrupt:
        pass
