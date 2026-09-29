"""HTTP của tab Kho: nhận POST từ app, đọc body, gọi flow, gửi JSON trả lời.

    POST /app/nhan-kho  {token, machine_id, version}          xem tồn kho
    POST /app/nap-kho   {token, machine_id, target, value}    nạp kho

Module tự quyết giới hạn body và status; server chính chỉ gọi handle() cho mỗi
request POST, handle() trả False nếu đường dẫn không thuộc module này.
"""

# Routing tập trung và HTTP dùng chung
from server.config.routing import MACHINE_INGREDIENT_GET, MACHINE_INGREDIENT_REFILL
from server.lib.http_json import handle_routes

# Trong module ingredient_sync
from .machine_ingredient_sync import nap_kho, nhan_kho


ROUTES = {
    MACHINE_INGREDIENT_GET: nhan_kho,
    MACHINE_INGREDIENT_REFILL: nap_kho,
}
MAX_BODY = 4096


def handle(request):
    """True nếu request thuộc module này và đã trả lời (server chính chỉ gọi hàm này)."""
    return handle_routes(request, ROUTES, MAX_BODY, lambda message: {"loi": message})
