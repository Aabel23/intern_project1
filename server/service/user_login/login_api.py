"""HTTP API chỉ dành cho luồng đăng nhập."""

import json
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from server.config.config import SERVER_HOST, SERVER_PORT
from server.config.routing import (
    APP_LOGIN,
    APP_LOGOUT,
    APP_REGISTER_USER,
    APP_SEND_OTP,
    APP_VERIFY_LOGIN,
    APP_VERIFY_OTP,
)
from server.service.user_register.user_register.registration_flow import (
    cleanup as cleanup_registration,
    confirm_otp,
    receive_register,
    resend_otp,
)
from .login_flow import cleanup as cleanup_login, receive_login, send_verification
from .session import end_session


ROUTES = {
    APP_REGISTER_USER: receive_register,
    APP_SEND_OTP: resend_otp,
    APP_VERIFY_OTP: confirm_otp,
    APP_LOGIN: receive_login,
    APP_VERIFY_LOGIN: send_verification,
    APP_LOGOUT: end_session,
}
IP_REQUESTS = {}
IP_LOCK = threading.Lock()


class LoginHandler(BaseHTTPRequestHandler):
    timeout = 10

    def do_GET(self):
        self.send_json(404, {"valid": False, "message": "Không có endpoint này"})

    def do_POST(self):
        handle = ROUTES.get(self.path)
        if handle is None:
            return self.send_json(404, {"valid": False, "message": "Không có endpoint này"})
        if self.too_many_requests():
            return self.send_json(
                429,
                {"valid": False, "message": "Quá nhiều yêu cầu", "retry_after": 60},
            )

        try:
            size = int(self.headers.get("Content-Length", 0))
            if size < 1 or size > 4096:
                raise ValueError
            raw = self.rfile.read(size)
            data = json.loads(raw)
            result = handle(data)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            return self.send_json(400, {"valid": False, "message": "JSON không hợp lệ"})
        except sqlite3.Error:
            return self.send_json(
                503, {"valid": False, "message": "Database tạm thời không sẵn sàng"}
            )

        status = 200 if result["valid"] else 400
        # Gửi OTP thành công cũng kèm retry_after (thời gian chờ gửi lại), không phải 429.
        if not result["valid"] and "retry_after" in result:
            status = 429
        self.send_json(status, result)

    def too_many_requests(self):
        now = time.monotonic()
        ip = self.client_address[0]
        with IP_LOCK:
            for key, record in list(IP_REQUESTS.items()):
                if now >= record[0]:
                    del IP_REQUESTS[key]
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

    def log_message(self, format, *args):
        return


class LoginServer(ThreadingHTTPServer):
    def service_actions(self):
        cleanup_registration()
        cleanup_login()


def run_api():
    with LoginServer((SERVER_HOST, SERVER_PORT), LoginHandler) as server:
        for path in ROUTES:
            print(f"API: http://{SERVER_HOST}:{SERVER_PORT}{path}", flush=True)
        server.serve_forever()
