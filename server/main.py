"""Điểm khởi động chung: python -m server.main (từ thư mục gốc dự án).

main chỉ gọi các module lên: mỗi module tự nghe đường dẫn của mình, tự đọc body,
tự kiểm tra và tự trả lời (xem server/lib/module_server.py). Thêm tính năng mới
là thêm một dòng vào MODULES.
"""

# Thư viện chuẩn
import sys

# Server chung: cấu hình, database, khung server
from server.config.config import SERVER_HOST, SERVER_PORT
from server.database.machine.init_db import init_db
from server.lib.module_server import ModuleServer, make_handler

# Các module: mỗi module tự nghe đường dẫn của mình
from server.service.dashboard_sync.machinelist_sync import machinelist_api
from server.service.dashboard_sync.menu_sync import menu_sync_api
from server.service.machine_register import machine_register_api
from server.service.machine_relay import relay_api
from server.service.machine_share import share_api
from server.service.user_login import login_api
from server.service.user_register.user_register import user_register_api

MODULES = (
    user_register_api,
    login_api,
    machine_register_api,
    share_api,
    machinelist_api,
    relay_api,
    menu_sync_api,
)

Handler = make_handler(MODULES)


class Server(ModuleServer):
    modules = MODULES


def main():
    # Terminal Windows hoặc log chuyển hướng ra file mặc định cp1252, không in được tiếng Việt.
    sys.stdout.reconfigure(encoding="utf-8")
    init_db()
    try:
        with Server((SERVER_HOST, SERVER_PORT), Handler) as server:
            print(f"FlexMix server: http://{SERVER_HOST}:{SERVER_PORT}", flush=True)
            for module in MODULES:
                print(f"  - {module.__name__.rsplit('.', 1)[-1]}", flush=True)
            print("Nhấn Ctrl+C để dừng.", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng server.", flush=True)


if __name__ == "__main__":
    main()
