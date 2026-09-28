"""HTTP của tab Menu: nhận POST từ app, đọc body, gọi flow, gửi JSON trả lời.

    POST /app/nhan-menu  {token, machine_id, menu_version}
    POST /app/gui-menu   {token, machine_id, menu_version, thay_doi}

Module tự quyết giới hạn body và status; server chính chỉ gọi handle() cho mỗi
request POST, handle() trả False nếu đường dẫn không thuộc tab Menu.
"""

# Routing tập trung và HTTP dùng chung
from server.config.routing import APP_RECEIVE_MENU, APP_SEND_MENU
from server.lib.http_json import handle_routes

# Trong module menu_sync
from .machine_menu_sync import gui_menu, nhan_menu


ROUTES = {
    APP_RECEIVE_MENU: nhan_menu,
    APP_SEND_MENU: gui_menu,
}
# Đủ cho 200 dòng thay_doi; gói menu trả về không bị giới hạn này.
MAX_BODY = 64_000


def handle(request):
    """True nếu request thuộc module này và đã trả lời (server chính chỉ gọi hàm này)."""
    return handle_routes(request, ROUTES, MAX_BODY, lambda message: {"loi": message})
