"""Khởi động toàn bộ module: python -m server.main."""

import argparse
import sys

from server.config.config import SERVER_HOST, SERVER_PORT
from server.database.machine.init_db import init_db
from server.lib.http.http_server import ModuleServer
from server.service.dashboard_sync.ingredient_sync import machine_ingredient_main
from server.service.dashboard_sync.machinelist_sync import machine_list_main
from server.service.dashboard_sync.menu_sync import machine_menu_main
from server.service.machine_link import machine_link_main
from server.service.machine_register import machine_register_main
from server.service.machine_share import machine_share_main
from server.service.user_login import user_login_main
from server.service.user_register import user_register_main


MODULES = (
    user_register_main,
    user_login_main,
    machine_register_main,
    machine_share_main,
    machine_list_main,
    machine_link_main,
    machine_menu_main,
    machine_ingredient_main,
)


def create_server(address):
    """Khởi tạo dữ liệu chung và chạy toàn bộ module đã đăng ký ở trên."""
    init_db()
    return ModuleServer(address, MODULES)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Chạy các module FlexMix trên một cổng.")
    parser.add_argument("--host", default=SERVER_HOST)
    parser.add_argument("--port", type=int, default=SERVER_PORT)
    args = parser.parse_args()
    try:
        with create_server((args.host, args.port)) as server:
            print(f"FlexMix server: http://{args.host}:{server.server_port}", flush=True)
            for module in server.modules:
                print(f"  - {module.__name__}", flush=True)
            print("Nhấn Ctrl+C để dừng.", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        print("Đã dừng server.", flush=True)


if __name__ == "__main__":
    main()
