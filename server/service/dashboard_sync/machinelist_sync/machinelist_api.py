"""HTTP của tab Máy: nhận POST từ app, đọc body, gọi flow, gửi JSON trả lời.

    POST /app/may-cua-toi  {token}                     danh sách máy của tài khoản
    POST /app/doi-ten-may  {token, machine_id, name}   chủ máy đổi tên
    POST /app/go-may       {token, machine_id}         chủ xóa máy / nhân viên bỏ quyền

Module tự quyết giới hạn body và status; server chính chỉ gọi handle() cho mỗi
request POST, handle() trả False nếu đường dẫn không thuộc module này.
"""

# Server chung: đường dẫn, xử lý HTTP
from server.config.routing import APP_MY_MACHINES, APP_REMOVE_MACHINE, APP_RENAME_MACHINE
from server.lib.http_json import handle_routes

# Trong module machinelist_sync
from .machinelist_flow import list_my_machines, remove_machine, rename_machine
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
