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

# Routing tập trung và HTTP dùng chung
from server.config.routing import USER_MACHINE_LIST, USER_MACHINE_REMOVE, MACHINE_NAME_UPDATE, MACHINE_STATUS_GET
from server.lib.http_json import handle_routes, invalid, send_json, with_valid_status

# Trong module machinelist_sync
from .machine_list_manage import list_my_machines, machine_status, remove_machine, rename_machine


ROUTES = with_valid_status({
    USER_MACHINE_LIST: list_my_machines,
    MACHINE_NAME_UPDATE: rename_machine,
    USER_MACHINE_REMOVE: remove_machine,
})
GET_ROUTES = (MACHINE_STATUS_GET,)
MAX_BODY = 4096


def handle(request):
    """True nếu request thuộc module này và đã trả lời (server chính chỉ gọi hàm này)."""
    return handle_routes(request, ROUTES, MAX_BODY, invalid)


def handle_get(request):
    """GET trạng thái máy; False nếu đường dẫn không phải của module này."""
    url = urlparse(request.path)
    if url.path != MACHINE_STATUS_GET:
        return False
    machine_id = parse_qs(url.query).get("machine_id", [""])[0]
    send_json(request, machine_status(machine_id))
    return True
