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
from server.database.machine.machine_read import can_manage, find_id_by_key_hash
from server.service.machine_register.machine_register_verify import hash_product_key
from server.service.user_login.session import NOT_LOGGED_IN, user_from_request

# Mỗi máy một hộp thư lệnh riêng: machine_id -> danh sách lệnh chờ máy lấy.
HOP_THU = {}
# Lệnh app đang chờ kết quả: id lệnh -> (machine_id, hàng chờ kết quả).
DANG_CHO = {}
KHOA = threading.Lock()
DEM_LENH = count(1)
LAN_HEARTBEAT_CUOI = {}
# Kết quả menu của máy có thể lớn hơn các gói tài khoản.
MAX_BODY = 1_000_000

from server.service.machine_register.machine_register_api import ROUTES as REGISTER_ROUTES
from server.service.machine_share.share_api import ROUTES as SHARE_ROUTES
from server.service.machine_manage.manage_api import ROUTES as MANAGE_ROUTES

MACHINE_ROUTES = {**REGISTER_ROUTES, **SHARE_ROUTES, **MANAGE_ROUTES}
from server.database.machine.init_db import init_db as init_machine_db


def machine_from_key(data):
    """Máy xưng danh bằng product key trên tem; trả machine_id server đã cấp."""
    key = data.get("product_key")
    if not isinstance(key, str) or not key.strip() or len(key) > 1024:
        return None
    return find_id_by_key_hash(hash_product_key(key))


def last_seen_of(machine_id):
    with KHOA:
        return LAN_HEARTBEAT_CUOI.get(machine_id)


def is_online(machine_id):
    last_seen = last_seen_of(machine_id)
    return last_seen is not None and time.time() - last_seen < HEARTBEAT_TIMEOUT_SECONDS


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Xem máy còn liên lạc với server không.
        url = urlparse(self.path)
        if url.path != MACHINE_STATUS:
            self.send_error(404)
            return
        machine_id = parse_qs(url.query).get("machine_id", [""])[0]
        self.tra_json({
            "machine_id": machine_id,
            "online": is_online(machine_id),
            "last_seen": last_seen_of(machine_id),
        })

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

        routes = {
            APP_SEND_COMMAND: self.app_gui_lenh,
            MACHINE_HEARTBEAT: self.may_heartbeat,
            MACHINE_POLL_COMMAND: self.may_hoi_lenh,
            MACHINE_SEND_RESULT: self.may_tra_ket_qua,
        }
        handle = routes.get(self.path)
        if handle is None:
            self.send_error(404)
            return
        data = self.doc_json()
        if data is None:
            self.tra_json({"loi": "JSON không hợp lệ"}, 400)
            return
        try:
            handle(data)
        except sqlite3.Error:
            self.tra_json({"loi": "Database tạm thời không sẵn sàng"}, 503)

    def app_gui_lenh(self, data):
        user_id = user_from_request(data)
        if user_id is None:
            self.tra_json({"loi": NOT_LOGGED_IN["message"], "login_required": True}, 401)
            return
        machine_id = data.get("machine_id")
        if not isinstance(machine_id, str) or not can_manage(machine_id, user_id):
            self.tra_json({"loi": "Bạn không quản lý máy này"}, 403)
            return
        # Máy không heartbeat thì báo ngay, không để app chờ hết thời gian.
        if not is_online(machine_id):
            self.tra_json({"loi": "Máy đang offline"})
            return

        # Chỉ chuyển tên lệnh và tham số cho máy, không chuyển token của app.
        lenh = {"id": next(DEM_LENH), "ten": data.get("ten"), "thamso": data.get("thamso", {})}
        hop_ket_qua = queue.Queue(maxsize=1)
        with KHOA:
            DANG_CHO[lenh["id"]] = (machine_id, hop_ket_qua)
            HOP_THU.setdefault(machine_id, []).append(lenh)
        print("Server nhan lenh tu app:", machine_id, lenh, flush=True)

        try:
            ket_qua = hop_ket_qua.get(timeout=COMMAND_TIMEOUT_SECONDS)
        except queue.Empty:
            # Máy chưa lấy lệnh thì hủy, tránh máy chạy lệnh cũ khi online lại.
            with KHOA:
                hop_thu = HOP_THU.get(machine_id, [])
                chua_lay = lenh in hop_thu
                if chua_lay:
                    hop_thu.remove(lenh)
            if chua_lay:
                ket_qua = {"loi": "Máy không phản hồi, lệnh đã được hủy"}
            else:
                ket_qua = {"loi": "Máy chưa trả kết quả, hãy tải lại để kiểm tra"}
        with KHOA:
            DANG_CHO.pop(lenh["id"], None)
        self.tra_json(ket_qua)

    def may_heartbeat(self, data):
        # Ghi thời điểm máy báo đang hoạt động.
        machine_id = machine_from_key(data)
        if machine_id is None:
            self.tra_json({"loi": "Máy chưa đăng ký hoặc sai product key"}, 403)
            return
        with KHOA:
            LAN_HEARTBEAT_CUOI[machine_id] = time.time()
        self.tra_json({"da_nhan": True})

    def may_hoi_lenh(self, data):
        # Máy chỉ lấy lệnh trong hộp thư của chính nó.
        machine_id = machine_from_key(data)
        if machine_id is None:
            self.tra_json({"loi": "Máy chưa đăng ký hoặc sai product key"}, 403)
            return
        with KHOA:
            hop_thu = HOP_THU.get(machine_id)
            lenh = hop_thu.pop(0) if hop_thu else None
        self.tra_json({"lenh": lenh})

    def may_tra_ket_qua(self, data):
        # Chuyển kết quả cho request app đang chờ, chỉ khi lệnh được giao cho máy này.
        machine_id = machine_from_key(data)
        if machine_id is None:
            self.tra_json({"loi": "Máy chưa đăng ký hoặc sai product key"}, 403)
            return
        with KHOA:
            cho = DANG_CHO.get(data.get("id"))
        if cho is not None and cho[0] == machine_id:
            try:
                cho[1].put_nowait(data.get("ket_qua"))
            except queue.Full:
                pass
        self.tra_json({"da_nhan": True})

    def doc_json(self):
        """Đọc body JSON object; None nếu sai kích thước, sai định dạng hoặc quá thời gian."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 1 <= length <= MAX_BODY:
                return None
            data = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError, TimeoutError):
            return None
        return data if isinstance(data, dict) else None

    def tra_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass


if __name__ == "__main__":
    init_machine_db()
    # Nhieu request phai chay song song: app doi trong khi machine hoi server.
    with ThreadingHTTPServer((SERVER_HOST, SERVER_PORT), Handler) as server:
        print(f"Server dang nghe tai http://{SERVER_HOST}:{SERVER_PORT}", flush=True)
        server.serve_forever()
