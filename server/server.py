"""Server trung gian giua app va machine."""

import json
import sqlite3
import queue
import threading
import time
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import count
from pathlib import Path
from urllib.parse import parse_qs, urlparse

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.config.config import (
    COMMAND_TIMEOUT_SECONDS,
    HEARTBEAT_TIMEOUT_SECONDS,
    SERVER_HOST,
    SERVER_PORT,
)
from server.config.routing import (
    APP_SEND_COMMAND,
    MACHINE_HEARTBEAT,
    MACHINE_POLL_COMMAND,
    MACHINE_SEND_RESULT,
    MACHINE_STATUS,
)

# Hop thu lenh va noi de app cho ket qua tu machine.
HOP_THU = queue.Queue()
DANG_CHO = {}
KHOA = threading.Lock()
DEM_LENH = count(1)
LAN_HEARTBEAT_CUOI = {}

from server.service.machine_register.machine_register_api import ROUTES as REGISTER_ROUTES
from server.service.machine_share.share_api import ROUTES as SHARE_ROUTES

MACHINE_ROUTES = {**REGISTER_ROUTES, **SHARE_ROUTES}
from server.database.machine.init_db import init_db as init_machine_db


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Xem máy còn liên lạc với server không.
        url = urlparse(self.path)
        if url.path == MACHINE_STATUS:
            machine_id = parse_qs(url.query).get("machine_id", [""])[0]
            with KHOA:
                last_seen = LAN_HEARTBEAT_CUOI.get(machine_id)
            online = last_seen is not None and time.time() - last_seen < HEARTBEAT_TIMEOUT_SECONDS
            self.tra_json({"machine_id": machine_id, "online": online, "last_seen": last_seen})
            return

        # Machine hoi server xem co lenh moi khong.
        if url.path != MACHINE_POLL_COMMAND:
            self.send_error(404)
            return

        try:
            lenh = HOP_THU.get_nowait()
        except queue.Empty:
            lenh = None
        self.tra_json({"lenh": lenh})

    def do_POST(self):
        # Endpoint đăng ký và chia sẻ máy dùng chung flow với server.main.
        handle = MACHINE_ROUTES.get(self.path)
        if handle is not None:
            try:
                length = int(self.headers.get("Content-Length", 0))
                if not 1 <= length <= 4096:
                    raise ValueError("Body không hợp lệ")
                self.connection.settimeout(10)
                data = json.loads(self.rfile.read(length))
                result = handle(data)
            except (ValueError, UnicodeDecodeError):
                return self.tra_json({"valid": False, "message": "JSON không hợp lệ"}, 400)
            except TimeoutError:
                return self.tra_json({"valid": False, "message": "Hết thời gian nhận dữ liệu"}, 408)
            except sqlite3.Error:
                return self.tra_json({"valid": False, "message": "Database tạm thời không sẵn sàng"}, 503)
            return self.tra_json(result, 200 if result["valid"] else 400)

        # Doc JSON ma app hoac machine gui len.
        length = self.headers.get("Content-Length", 0)
        length = int(length)
        body = self.rfile.read(length)
        text = body.decode("utf-8")
        data = json.loads(text)

        if self.path == MACHINE_HEARTBEAT:
            # Ghi thời điểm máy báo đang hoạt động.
            machine_id = data.get("machine_id")
            if not machine_id:
                self.send_error(400, "Thieu machine_id")
                return
            with KHOA:
                LAN_HEARTBEAT_CUOI[machine_id] = time.time()
            self.tra_json({"da_nhan": True})
            return

        if self.path == APP_SEND_COMMAND:
            # Xep lenh vao hop thu va doi machine tra ket qua.
            lenh_id = next(DEM_LENH)
            data["id"] = lenh_id
            hop_ket_qua = queue.Queue(maxsize=1)
            with KHOA:
                DANG_CHO[lenh_id] = hop_ket_qua
            HOP_THU.put(data)
            print("Server nhan lenh tu app:", data, flush=True)

            try:
                ket_qua = hop_ket_qua.get(timeout=COMMAND_TIMEOUT_SECONDS)
            except queue.Empty:
                ket_qua = {"loi": "Machine khong tra loi"}
            with KHOA:
                DANG_CHO.pop(lenh_id, None)
            self.tra_json(ket_qua)
            return

        if self.path == MACHINE_SEND_RESULT:
            # Chuyen ket qua cua machine cho request app dang cho.
            lenh_id = data["id"]
            with KHOA:
                hop_ket_qua = DANG_CHO.get(lenh_id)
            if hop_ket_qua is not None:
                hop_ket_qua.put(data["ket_qua"])
            self.tra_json({"da_nhan": True})
            return

        self.send_error(404)

    def tra_json(self, data, status=200):
        text = json.dumps(data)
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    init_machine_db()
    # Nhieu request phai chay song song: app doi trong khi machine hoi server.
    with ThreadingHTTPServer((SERVER_HOST, SERVER_PORT), Handler) as server:
        print(f"Server dang nghe tai http://{SERVER_HOST}:{SERVER_PORT}", flush=True)
        server.serve_forever()
