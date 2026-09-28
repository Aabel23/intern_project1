"""Chạy riêng vài module server trên một cổng, để thử một module mà không bật cả server.

Chạy từ thư mục gốc androidv0.1 (dùng chung server/database/database.db với server đầy đủ):
    python sandbox/server_module/run_modules.py menu_sync relay login
    python sandbox/server_module/run_modules.py machinelist login --port 8001

Module code không tự chạy riêng; danh sách module nào ghép với module nào nằm ở đây.
Menu, kho cần "relay" để máy có chỗ heartbeat và hỏi lệnh; module nào đòi token cần
"login" để lấy token ngay trên server này.
"""

# Thư viện chuẩn
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Server chung: cấu hình, database, khung server
from server.config.config import SERVER_HOST, SERVER_PORT  # noqa: E402
from server.database.machine.init_db import init_db  # noqa: E402
from server.lib.module_server import ModuleServer, make_handler  # noqa: E402

# Các module
from server.service.dashboard_sync.ingredient_sync import ingredient_sync_api  # noqa: E402
from server.service.dashboard_sync.machinelist_sync import machinelist_api  # noqa: E402
from server.service.dashboard_sync.menu_sync import menu_sync_api  # noqa: E402
from server.service.machine_register import machine_register_api  # noqa: E402
from server.service.machine_relay import relay_api  # noqa: E402
from server.service.machine_share import share_api  # noqa: E402
from server.service.user_login import login_api  # noqa: E402
from server.service.user_register.user_register import user_register_api  # noqa: E402

MODULES = {
    "register": user_register_api,
    "login": login_api,
    "machine_register": machine_register_api,
    "share": share_api,
    "machinelist": machinelist_api,
    "relay": relay_api,
    "menu_sync": menu_sync_api,
    "ingredient_sync": ingredient_sync_api,
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Chạy riêng vài module server.")
    parser.add_argument("modules", nargs="+", choices=sorted(MODULES))
    parser.add_argument("--port", type=int, default=SERVER_PORT)
    args = parser.parse_args()
    modules = tuple(MODULES[name] for name in args.modules)
    init_db()
    with ModuleServer((SERVER_HOST, args.port), make_handler(modules)) as server:
        server.modules = modules
        print(f"Module {', '.join(args.modules)}: http://{SERVER_HOST}:{args.port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
