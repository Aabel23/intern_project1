"""Relay app ↔ máy: route máy (heartbeat, hỏi lệnh, trả kết quả, trả đồng bộ),
trạng thái máy, và các lệnh app còn đi qua relay (gửi lệnh, đồng bộ kho, nạp kho).

Hộp thư lệnh nằm ở relay_queue.py; module khác gửi lệnh xuống máy bằng
relay_queue.gui_va_cho(), không đi qua file này.
"""

import queue
import sqlite3
import time
from urllib.parse import parse_qs, urlparse

from server.config.config import POLL_WAIT_SECONDS
from server.config.routing import (
    APP_SEND_COMMAND,
    APP_SYNC,
    MACHINE_HEARTBEAT,
    MACHINE_POLL_COMMAND,
    MACHINE_REFILL,
    MACHINE_SEND_RESULT,
    MACHINE_SEND_SYNC,
    MACHINE_STATUS,
)
from server.database.machine.machine_read import can_manage, is_owner
from server.lib.checks import is_machine_id
from server.lib.http_json import read_json, send_json
from server.service.dashboard_sync.sync_rules import QUYEN_DONG_BO, QUYEN_LENH, QUYEN_NAP_KHO
from server.service.user_login.session import NOT_LOGGED_IN, user_from_request
from .relay_queue import (
    CO_LENH,
    DANG_CHO,
    DEM_LENH,
    HOP_THU,
    KHOA,
    LAN_HEARTBEAT_CUOI,
    gui_va_cho,
    is_online,
    last_seen_of,
    machine_from_key,
)

# Kết quả đồng bộ của máy có thể lớn hơn các gói tài khoản.
MAX_BODY = 1_000_000


def handle_get(request):
    # Xem máy còn liên lạc với server không.
    url = urlparse(request.path)
    if url.path != MACHINE_STATUS:
        return False
    machine_id = parse_qs(url.query).get("machine_id", [""])[0]
    send_json(request, {
        "machine_id": machine_id,
        "online": is_online(machine_id),
        "last_seen": last_seen_of(machine_id),
    })
    return True


def handle(request):
    """True nếu request POST thuộc relay và đã trả lời."""
    # Kết quả đồng bộ là JSON đã nén gzip, không đọc bằng read_json được.
    if request.path == MACHINE_SEND_SYNC:
        try:
            may_tra_dong_bo(request)
        except sqlite3.Error:
            send_json(request, {"loi": "Database tạm thời không sẵn sàng"}, 503)
        return True
    route = ROUTES.get(request.path)
    if route is None:
        return False
    data = read_json(request, MAX_BODY)
    if data is None:
        send_json(request, {"loi": "JSON không hợp lệ"}, 400)
        return True
    try:
        route(request, data)
    except sqlite3.Error:
        send_json(request, {"loi": "Database tạm thời không sẵn sàng"}, 503)
    return True


def app_gui_lenh(request, data):
    user_id = user_from_request(data)
    if user_id is None:
        send_json(request, {"loi": NOT_LOGGED_IN["message"], "login_required": True}, 401)
        return
    machine_id = data.get("machine_id")
    if not is_machine_id(machine_id) or not can_manage(machine_id, user_id):
        send_json(request, {"loi": "Bạn không quản lý máy này"}, 403)
        return
    vai_tro = "owner" if is_owner(machine_id, user_id) else "manager"
    ten, thamso = data.get("ten"), data.get("thamso", {})
    if not isinstance(ten, str) or vai_tro not in QUYEN_LENH.get(ten, ()):
        send_json(request, {"loi": "Lệnh không hợp lệ hoặc không đủ quyền"}, 403)
        return
    if not isinstance(thamso, dict):
        send_json(request, {"loi": "Tham số lệnh không hợp lệ"}, 400)
        return
    # Máy không heartbeat thì báo ngay, không để app chờ hết thời gian.
    if not is_online(machine_id):
        send_json(request, {"loi": "Máy đang offline"})
        return

    # Chỉ chuyển tên lệnh và tham số cho máy, không chuyển token của app.
    lenh = {"id": next(DEM_LENH), "ten": ten, "thamso": thamso}
    ket_qua = gui_va_cho(machine_id, lenh)
    # Lệnh thường không nhận gói đồng bộ; máy gửi nhầm thì báo lỗi thay vì trả byte thô.
    if isinstance(ket_qua, tuple):
        ket_qua = {"loi": "Máy trả kết quả không đúng loại lệnh"}
    send_json(request, ket_qua)


def app_dong_bo(request, data):
    # App đọc dữ liệu dashboard: kiểm tra quyền trước, hợp lệ mới gửi xuống máy.
    user_id = user_from_request(data)
    if user_id is None:
        send_json(request, {"loi": NOT_LOGGED_IN["message"], "login_required": True}, 401)
        return
    machine_id = data.get("machine_id")
    if not is_machine_id(machine_id) or not can_manage(machine_id, user_id):
        send_json(request, {"loi": "Bạn không quản lý máy này"}, 403)
        return
    vai_tro = "owner" if is_owner(machine_id, user_id) else "manager"
    ten = data.get("lenh")
    if not isinstance(ten, str) or vai_tro not in QUYEN_DONG_BO.get(ten, ()):
        send_json(request, {"loi": "Lệnh đồng bộ không hợp lệ hoặc không đủ quyền"}, 403)
        return
    if not is_online(machine_id):
        send_json(request, {"loi": "Máy đang offline"}, 503)
        return

    # ETag app đang giữ; máy so với dữ liệu hiện tại để trả 304 nếu không đổi.
    etag = request.headers.get("If-None-Match")
    if etag is not None and len(etag) > 100:
        etag = None
    lenh = {"id": next(DEM_LENH), "ten": ten, "thamso": {}, "etag": etag}
    ket_qua = gui_va_cho(machine_id, lenh)
    if not isinstance(ket_qua, tuple):
        # Máy báo lỗi (MySQL, lệnh lạ) hoặc hết thời gian chờ.
        if not isinstance(ket_qua, dict) or "loi" not in ket_qua:
            ket_qua = {"loi": "Máy trả kết quả không đúng loại lệnh"}
        send_json(request, ket_qua, 502)
        return

    # Chuyển nguyên gói nén cho app, không giải nén.
    etag_moi, goi = ket_qua
    request.send_response(200 if goi else 304)
    request.send_header("ETag", etag_moi)
    if goi:
        request.send_header("Content-Type", "application/json; charset=utf-8")
        request.send_header("Content-Encoding", "gzip")
        request.send_header("Content-Length", str(len(goi)))
    request.end_headers()
    try:
        request.wfile.write(goi)
    except (BrokenPipeError, ConnectionResetError):
        pass


def app_nap_kho(request, data):
    # App nạp kho: {token, machine_id, target, value}.
    # target = id nguyên liệu hoặc "all"; value = "full" hoặc số gram (chỉ với một nguyên liệu).
    user_id = user_from_request(data)
    if user_id is None:
        send_json(request, {"loi": NOT_LOGGED_IN["message"], "login_required": True}, 401)
        return
    machine_id = data.get("machine_id")
    if not is_machine_id(machine_id) or not can_manage(machine_id, user_id):
        send_json(request, {"loi": "Bạn không quản lý máy này"}, 403)
        return
    vai_tro = "owner" if is_owner(machine_id, user_id) else "manager"
    if vai_tro not in QUYEN_NAP_KHO:
        send_json(request, {"loi": "Không đủ quyền nạp kho"}, 403)
        return
    target, value = data.get("target"), data.get("value")
    target_hop_le = target == "all" or (
        isinstance(target, int) and not isinstance(target, bool) and target > 0)
    value_hop_le = value == "full" or (
        target != "all" and isinstance(value, (int, float))
        and not isinstance(value, bool) and 0 <= value <= 99999999.99)
    if not target_hop_le or not value_hop_le:
        send_json(request, {"loi": "Gói nạp kho không hợp lệ"}, 400)
        return
    if not is_online(machine_id):
        send_json(request, {"loi": "Máy đang offline"}, 503)
        return

    lenh = {"id": next(DEM_LENH), "ten": "nap_kho", "thamso": {"target": target, "value": value}}
    ket_qua = gui_va_cho(machine_id, lenh)
    if not isinstance(ket_qua, dict):
        ket_qua = {"loi": "Máy trả kết quả không đúng loại lệnh"}
    send_json(request, ket_qua, 502 if "loi" in ket_qua else 200)


def may_heartbeat(request, data):
    # Ghi thời điểm máy báo đang hoạt động.
    machine_id = machine_from_key(data)
    if machine_id is None:
        send_json(request, {"loi": "Máy chưa đăng ký hoặc sai product key"}, 403)
        return
    with KHOA:
        LAN_HEARTBEAT_CUOI[machine_id] = time.time()
    send_json(request, {"da_nhan": True})


def may_hoi_lenh(request, data):
    # Máy chỉ lấy lệnh trong hộp thư của chính nó.
    machine_id = machine_from_key(data)
    if machine_id is None:
        send_json(request, {"loi": "Máy chưa đăng ký hoặc sai product key"}, 403)
        return
    # Long-poll: giữ request tới khi có lệnh (tối đa POLL_WAIT_SECONDS), máy nhận
    # lệnh ngay thay vì chờ tới lượt hỏi kế tiếp.
    with CO_LENH:
        CO_LENH.wait_for(lambda: HOP_THU.get(machine_id), timeout=POLL_WAIT_SECONDS)
        hop_thu = HOP_THU.get(machine_id)
        lenh = hop_thu.pop(0) if hop_thu else None
    send_json(request, {"lenh": lenh})


def may_tra_ket_qua(request, data):
    # Chuyển kết quả cho request app đang chờ, chỉ khi lệnh được giao cho máy này.
    machine_id = machine_from_key(data)
    if machine_id is None:
        send_json(request, {"loi": "Máy chưa đăng ký hoặc sai product key"}, 403)
        return
    with KHOA:
        cho = DANG_CHO.get(data.get("id"))
    if cho is not None and cho[0] == machine_id:
        try:
            cho[1].put_nowait(data.get("ket_qua"))
        except queue.Full:
            pass
    send_json(request, {"da_nhan": True})


def may_tra_dong_bo(request):
    # Máy gửi kết quả đồng bộ: body là JSON đã nén gzip, rỗng nghĩa là dữ liệu không đổi.
    machine_id = machine_from_key({"product_key": request.headers.get("X-Product-Key")})
    if machine_id is None:
        send_json(request, {"loi": "Máy chưa đăng ký hoặc sai product key"}, 403)
        return
    etag = request.headers.get("ETag", "")
    try:
        lenh_id = int(request.headers.get("X-Lenh-Id", ""))
        length = int(request.headers.get("Content-Length", 0))
        if not etag or len(etag) > 100 or not 0 <= length <= MAX_BODY:
            raise ValueError
        goi = request.rfile.read(length)
    except (ValueError, TimeoutError):
        send_json(request, {"loi": "Gói đồng bộ không hợp lệ"}, 400)
        return
    with KHOA:
        cho = DANG_CHO.get(lenh_id)
    if cho is not None and cho[0] == machine_id:
        try:
            cho[1].put_nowait((etag, goi))
        except queue.Full:
            pass
    send_json(request, {"da_nhan": True})


ROUTES = {
    APP_SEND_COMMAND: app_gui_lenh,
    APP_SYNC: app_dong_bo,
    MACHINE_REFILL: app_nap_kho,
    MACHINE_HEARTBEAT: may_heartbeat,
    MACHINE_POLL_COMMAND: may_hoi_lenh,
    MACHINE_SEND_RESULT: may_tra_ket_qua,
}
