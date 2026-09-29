"""Cửa vào menu_sync: nhận POST, đọc JSON, chọn luồng và trả response.

POST /app/nhan-menu: {token, machine_id, menu_version}
POST /app/cap-nhat-menu: {token, machine_id, menu_version, thay_doi}
"""

from server.config.routing import MACHINE_MENU_GET, MACHINE_MENU_UPDATE
from server.lib.http.http_json import handle_routes

from .machine_menu_get import nhan_menu
from .machine_menu_update import cap_nhat_menu

ROUTES = {
    MACHINE_MENU_GET: nhan_menu,
    MACHINE_MENU_UPDATE: cap_nhat_menu,
}
MAX_BODY = 64_000


def handle(request):
    """Khớp URL → đọc JSON → gọi luồng → trả HTTP; False nếu URL khác."""
    return handle_routes(request, ROUTES, MAX_BODY, lambda message: {"loi": message})
