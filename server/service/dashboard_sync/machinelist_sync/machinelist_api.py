"""HTTP của tab Máy: nhận POST từ app, đọc body, gọi flow, gửi JSON trả lời.

    POST /app/may-cua-toi  {token}                     danh sách máy của tài khoản
    POST /app/doi-ten-may  {token, machine_id, name}   chủ máy đổi tên
    POST /app/go-may       {token, machine_id}         chủ xóa máy / nhân viên bỏ quyền
    GET  /machine/trang-thai?machine_id=...            máy Online/Offline

Module tự quyết giới hạn body và status; server chính chỉ gọi handle() cho mỗi
request POST, handle() trả False nếu đường dẫn không thuộc module này.
"""

# Thư viện chuẩn
from urllib.parse import parse_qs, urlparse

# Server chung: đường dẫn, xử lý HTTP
from server.config.routing import APP_MY_MACHINES, APP_REMOVE_MACHINE, APP_RENAME_MACHINE, MACHINE_STATUS
from server.lib.http_json import handle_routes, send_json

# Trong module machinelist_sync
from .machinelist_flow import list_my_machines, machine_status, remove_machine, rename_machine
from .machinelist_verify import invalid

ROUTES = {
    APP_MY_MACHINES: list_my_machines,
    APP_RENAME_MACHINE: rename_machine,
    APP_REMOVE_MACHINE: remove_machine,
}
MAX_BODY = 4096


def handle(request):
    """True nếu request thuộc module này và đã trả lời (server chính chỉ gọi hàm này)."""
    return handle_routes(request, ROUTES, MAX_BODY, invalid)


def handle_get(request):
    """GET trạng thái máy; False nếu đường dẫn không phải của module này."""
    url = urlparse(request.path)
    if url.path != MACHINE_STATUS:
        return False
    machine_id = parse_qs(url.query).get("machine_id", [""])[0]
    send_json(request, machine_status(machine_id))
    return True
