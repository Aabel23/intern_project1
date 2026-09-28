"""HTTP của tab Menu: nhận POST từ app, đọc body, gọi flow, gửi JSON trả lời.

    POST /app/nhan-menu  {token, machine_id, menu_version}
    POST /app/gui-menu   {token, machine_id, menu_version, thay_doi}

Module tự quyết giới hạn body và status; server chính chỉ gọi handle() cho mỗi
request POST, handle() trả False nếu đường dẫn không thuộc tab Menu.
"""

import json
import sqlite3

from server.config.routing import APP_RECEIVE_MENU, APP_SEND_MENU
from .menu_sync_flow import gui_menu, nhan_menu

ROUTES = {
    APP_RECEIVE_MENU: nhan_menu,
    APP_SEND_MENU: gui_menu,
}
# Đủ cho 200 dòng thay_doi; gói menu trả về không bị giới hạn này.
MAX_BODY = 64_000


def handle(request):
    """request là BaseHTTPRequestHandler của server; True nếu đã trả lời."""
    route = ROUTES.get(request.path)
    if route is None:
        return False
    data = read_json(request)
    if data is None:
        send_json(request, {"loi": "JSON không hợp lệ"}, 400)
        return True
    try:
        result, status = route(data)
    except sqlite3.Error:
        result, status = {"loi": "Database tạm thời không sẵn sàng"}, 503
    send_json(request, result, status)
    return True


def read_json(request):
    """Body JSON object; None nếu sai kích thước, sai định dạng hoặc quá thời gian."""
    try:
        length = int(request.headers.get("Content-Length", 0))
        if not 1 <= length <= MAX_BODY:
            return None
        data = json.loads(request.rfile.read(length))
    except (ValueError, UnicodeDecodeError, TimeoutError):
        return None
    return data if isinstance(data, dict) else None


def send_json(request, data, status):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    try:
        request.send_response(status)
        request.send_header("Content-Type", "application/json; charset=utf-8")
        request.send_header("Content-Length", str(len(body)))
        request.end_headers()
        request.wfile.write(body)
    except (BrokenPipeError, ConnectionResetError):
        pass
