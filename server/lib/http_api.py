import json
import sys
import time
import threading
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from server.config.config import SERVER_HOST, SERVER_PORT

IP_REQUESTS = {}
IP_LOCK = threading.Lock()


class RegisterHandler(BaseHTTPRequestHandler):
    timeout = 10

    def do_GET(self):
        self.send_json(404, {"valid": False, "message": "Không có endpoint này"})

    def do_POST(self):
        handle = self.server.routes.get(self.path)
        if handle is None:
            return self.send_json(404, {"valid": False, "message": "Không có endpoint này"})

        # Giới hạn theo IP trước khi đọc body hoặc gọi database/SMTP.
        now = time.monotonic()
        with IP_LOCK:
            for ip, record in list(IP_REQUESTS.items()):
                if now >= record[0]:
                    del IP_REQUESTS[ip]
            ip = self.client_address[0]
            record = IP_REQUESTS.get(ip)
            blocked = record is None and len(IP_REQUESTS) >= 1000
            if not blocked:
                record = IP_REQUESTS.setdefault(ip, [now + 60, 0])
                record[1] += 1
                blocked = record[1] > 30
        if blocked:
            return self.send_json(429, {"valid": False, "message": "Quá nhiều yêu cầu", "retry_after": 60})

        try:
            size = int(self.headers.get("Content-Length", 0))
            if size < 1 or size > 16_384:
                raise ValueError("Dữ liệu không hợp lệ")
            body = self.rfile.read(size)
            data = json.loads(body)
            result = handle(data)
        except (ValueError, UnicodeDecodeError) as error:
            print("INVALID: Invalid JSON request", flush=True)
            self.send_json(400, {"valid": False, "message": "JSON không hợp lệ"})
            return

        except TimeoutError:
            self.send_json(408, {"valid": False, "message": "Hết thời gian nhận dữ liệu"})
            return
        except sqlite3.Error:
            self.send_json(503, {"valid": False, "message": "Database tạm thời không sẵn sàng"})
            return

        status = 200 if result["valid"] else 400
        if not result["valid"] and "retry_after" in result:
            status = 429
        self.send_json(status, result)

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
            pass  # App đã ngắt kết nối; kết quả vẫn được giữ trong phiên.


class RegisterServer(ThreadingHTTPServer):
    def service_actions(self):
        self.cleanup()


def run_api(routes, cleanup):
    """routes: dict đường dẫn -> hàm xử lý(data) trả về {"valid", "message"}."""
    with RegisterServer((SERVER_HOST, SERVER_PORT), RegisterHandler) as server:
        server.routes = routes
        server.cleanup = cleanup
        for path in routes:
            print(f"API: http://{SERVER_HOST}:{SERVER_PORT}{path}", flush=True)
        server.serve_forever()
