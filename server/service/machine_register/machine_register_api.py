"""Chạy: python -m server.service.machine_register.machine_register_api"""

import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from server.config.config import SERVER_HOST, SERVER_PORT
from server.config.routing import APP_REGISTER_MACHINE, APP_REGISTER_MACHINE_VERIFY
from server.database.machine.init_db import init_db
from .machine_register_flow import receive_register
from .machine_register_verify import verify_registration


ROUTES = {
    APP_REGISTER_MACHINE: receive_register,
    APP_REGISTER_MACHINE_VERIFY: verify_registration,
}


class MachineRegisterHandler(BaseHTTPRequestHandler):
    timeout = 10

    def do_GET(self):
        self.send_json(404, {"valid": False, "message": "Không có endpoint này"})

    def do_POST(self):
        handle = ROUTES.get(self.path)
        if handle is None:
            self.send_json(404, {"valid": False, "message": "Không có endpoint này"})
            return

        # Đọc gói JSON từ app rồi chuyển cho flow tương ứng.
        try:
            size = int(self.headers.get("Content-Length", 0))
            if not 1 <= size <= 4096:
                raise ValueError("Kích thước gói không hợp lệ")
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
        self.send_json(status, result)

    def send_json(self, status, data):
        text = json.dumps(data, ensure_ascii=False)
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass


def run_api():
    init_db()
    with ThreadingHTTPServer((SERVER_HOST, SERVER_PORT), MachineRegisterHandler) as server:
        for path in ROUTES:
            print(f"API: http://{SERVER_HOST}:{SERVER_PORT}{path}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    run_api()
