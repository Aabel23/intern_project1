"""Relay giữa app và máy: heartbeat, gửi lệnh, lấy lệnh, trả kết quả.

Chạy qua server.main (python -m server.main), không chạy riêng file này.
"""

import json
import sqlite3
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler
from itertools import count
from urllib.parse import parse_qs, urlparse

from server.config.config import (
    COMMAND_TIMEOUT_SECONDS,
    HEARTBEAT_TIMEOUT_SECONDS,
)
from server.config.routing import (
    APP_SEND_COMMAND,
    MACHINE_HEARTBEAT,
    MACHINE_POLL_COMMAND,
    MACHINE_SEND_RESULT,
    MACHINE_STATUS,
)
from server.database.machine.machine_read import can_manage, find_id_by_key_hash
from server.lib.checks import is_machine_id
from server.lib.hashing import sha256_hex
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



def machine_from_key(data):
    """Máy xưng danh bằng product key trên tem; trả machine_id server đã cấp."""
    key = data.get("product_key")
    if not isinstance(key, str) or not key.strip() or len(key) > 1024:
        return None
    return find_id_by_key_hash(sha256_hex(key))


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
        if not is_machine_id(machine_id) or not can_manage(machine_id, user_id):
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
        """Trả JSON cho mọi route (relay và các block trong server.main)."""
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if isinstance(data, dict) and "retry_after" in data:
            self.send_header("Retry-After", str(data["retry_after"]))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

