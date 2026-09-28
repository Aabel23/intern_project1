"""HTTP của tab Kho: nhận POST từ app, đọc body, gọi flow, gửi JSON trả lời.

    POST /app/nhan-kho  {token, machine_id, version}          xem tồn kho
    POST /app/nap-kho   {token, machine_id, target, value}    nạp kho

Module tự quyết giới hạn body và status; server chính chỉ gọi handle() cho mỗi
request POST, handle() trả False nếu đường dẫn không thuộc module này.
"""

# Server chung: đường dẫn, xử lý HTTP
from server.config.routing import APP_RECEIVE_INGREDIENTS, APP_REFILL
from server.lib.http_json import handle_routes

# Trong module ingredient_sync
from .ingredient_sync_flow import nap_kho, nhan_kho

ROUTES = {
    APP_RECEIVE_INGREDIENTS: nhan_kho,
    APP_REFILL: nap_kho,
}
MAX_BODY = 4096


def handle(request):
    """True nếu request thuộc module này và đã trả lời (server chính chỉ gọi hàm này)."""
    return handle_routes(request, ROUTES, MAX_BODY, lambda message: {"loi": message})
