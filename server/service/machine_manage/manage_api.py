"""HTTP của quản lý máy: nhận POST từ app, đọc body, gọi flow, gửi JSON trả lời.

    POST /app/doi-ten-may  {token, machine_id, name}   chủ máy đổi tên
    POST /app/go-may       {token, machine_id}         chủ xóa máy / nhân viên bỏ quyền

Module tự quyết giới hạn body và status; server chính chỉ gọi handle() cho mỗi
request POST, handle() trả False nếu đường dẫn không thuộc module này.
"""

# Thư viện chuẩn
import sqlite3

# Server chung: đường dẫn, đọc/ghi JSON
from server.config.routing import APP_REMOVE_MACHINE, APP_RENAME_MACHINE
from server.lib.http_json import read_json, send_json

# Trong module machine_manage
from .manage_flow import remove_machine, rename_machine

ROUTES = {
    APP_RENAME_MACHINE: rename_machine,
    APP_REMOVE_MACHINE: remove_machine,
}
MAX_BODY = 4096


def handle(request):
    """request là BaseHTTPRequestHandler của server; True nếu đã trả lời."""
    route = ROUTES.get(request.path)
    if route is None:
        return False
    data = read_json(request, MAX_BODY)
    if data is None:
        send_json(request, {"valid": False, "message": "JSON không hợp lệ"}, 400)
        return True
    try:
        result, status = route(data)
    except sqlite3.Error:
        result, status = {"valid": False, "message": "Database tạm thời không sẵn sàng"}, 503
    send_json(request, result, status)
    return True
