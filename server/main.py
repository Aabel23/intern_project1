"""Điểm khởi động chung: python -m server.main (từ thư mục gốc dự án)."""

import json
import sqlite3
import sys
import threading
import time
from http.server import ThreadingHTTPServer

from server.config.config import SERVER_HOST, SERVER_PORT
from server.config.routing import (
    APP_SEND_COMMAND,
    MACHINE_HEARTBEAT,
    MACHINE_POLL_COMMAND,
    MACHINE_SEND_RESULT,
)
from server.database.machine.init_db import init_db
from server.server import Handler as RelayHandler
from server.service.user_login.login_api import ROUTES as LOGIN_ROUTES
from server.service.user_login.login_flow import cleanup as cleanup_login
from server.service.user_register.user_register.registration_flow import cleanup as cleanup_registration
from server.service.machine_register.machine_register_api import ROUTES as MACHINE_ROUTES
from server.service.machine_share.share_api import ROUTES as SHARE_ROUTES
from server.service.machine_manage.manage_api import ROUTES as MANAGE_ROUTES


# LOGIN_ROUTES đã gồm đăng ký người dùng, gửi/xác minh OTP, đăng nhập và đăng xuất.
ROUTES = {**LOGIN_ROUTES, **MACHINE_ROUTES, **SHARE_ROUTES, **MANAGE_ROUTES}
RELAY_ROUTES = {APP_SEND_COMMAND, MACHINE_HEARTBEAT, MACHINE_POLL_COMMAND, MACHINE_SEND_RESULT}
# Chỉ giới hạn các API chưa cần token (dò mật khẩu, spam OTP). API máy/chia sẻ
# đã đòi token hợp lệ nên không tính, cả quán dùng chung một IP vẫn không bị chặn.
LIMITED_ROUTES = set(LOGIN_ROUTES)
IP_REQUESTS = {}
IP_LOCK = threading.Lock()


class Handler(RelayHandler):
    # GET trạng thái máy kế thừa nguyên từ relay hiện có.
    timeout = 10

    def do_POST(self):
        if self.path in RELAY_ROUTES:
            super().do_POST()
            return
        handle = ROUTES.get(self.path)
        if handle is None:
            self.send_json(404, {"valid": False, "message": "Không có endpoint này"})
            return
        if self.path in LIMITED_ROUTES and self.too_many_requests():
            self.send_json(429, {"valid": False, "message": "Quá nhiều yêu cầu", "retry_after": 60})
            return

        # Các flow nhận dict và trả dict; request lỗi không dừng server.
        try:
            size = int(self.headers.get("Content-Length", 0))
            if not 1 <= size <= 4096:
                raise ValueError("Kích thước không hợp lệ")
            body = self.rfile.read(size)
            data = json.loads(body)
            result = handle(data)
        except (ValueError, UnicodeDecodeError):
            self.send_json(400, {"valid": False, "message": "JSON không hợp lệ"})
            return
        except TimeoutError:
            self.send_json(408, {"valid": False, "message": "Hết thời gian nhận dữ liệu"})
            return
        except sqlite3.Error:
            self.send_json(503, {"valid": False, "message": "Database tạm thời không sẵn sàng"})
            return

        status = 200 if result["valid"] else 400
        # Gửi OTP thành công cũng kèm retry_after (thời gian chờ gửi lại), không phải 429.
        if not result["valid"] and "retry_after" in result:
            status = 429
        self.send_json(status, result)

    def too_many_requests(self):
        # Giới hạn 30 request/phút/IP cho các route trong LIMITED_ROUTES.
        now = time.monotonic()
        ip = self.client_address[0]
        with IP_LOCK:
            for key, record in list(IP_REQUESTS.items()):
                if now >= record[0]:
                    del IP_REQUESTS[key]
            if ip not in IP_REQUESTS and len(IP_REQUESTS) >= 1000:
                return True
            record = IP_REQUESTS.setdefault(ip, [now + 60, 0])
            record[1] += 1
            return record[1] > 30

    def send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if "retry_after" in data:
            self.send_header("Retry-After", str(data["retry_after"]))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass


class Server(ThreadingHTTPServer):
    def service_actions(self):
        # Dọn các phiên hết hạn ngay cả khi không có request mới.
        cleanup_registration()
        cleanup_login()


def main():
    # Terminal Windows hoặc log chuyển hướng ra file mặc định cp1252, không in được tiếng Việt.
    sys.stdout.reconfigure(encoding="utf-8")
    init_db()
    try:
        with Server((SERVER_HOST, SERVER_PORT), Handler) as server:
            print(f"FlexMix server: http://{SERVER_HOST}:{SERVER_PORT}", flush=True)
            print("Đăng ký / OTP / đăng nhập / đăng ký máy / chia sẻ máy / relay đã sẵn sàng.", flush=True)
            print("Nhấn Ctrl+C để dừng.", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng server.", flush=True)


if __name__ == "__main__":
    main()
