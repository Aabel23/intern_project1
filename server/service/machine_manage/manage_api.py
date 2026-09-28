"""Route đổi tên và gỡ máy; module tự nghe, server.main chỉ gọi handle()."""

from server.config.routing import APP_REMOVE_MACHINE, APP_RENAME_MACHINE
from server.lib.valid_api import handle_valid_routes
from .manage_flow import remove_machine, rename_machine


ROUTES = {
    APP_RENAME_MACHINE: rename_machine,
    APP_REMOVE_MACHINE: remove_machine,
}


def handle(request):
    """True nếu request thuộc module này và đã trả lời (server chính chỉ gọi hàm này)."""
    return handle_valid_routes(request, ROUTES)
