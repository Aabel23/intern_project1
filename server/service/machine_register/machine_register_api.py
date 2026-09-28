"""Route đăng ký máy; module tự nghe, server.main chỉ gọi handle()."""

from server.config.routing import APP_REGISTER_MACHINE
from server.lib.valid_api import handle_valid_routes
from .machine_register_flow import receive_register


ROUTES = {
    APP_REGISTER_MACHINE: receive_register,
}


def handle(request):
    """True nếu request thuộc module này và đã trả lời (server chính chỉ gọi hàm này)."""
    return handle_valid_routes(request, ROUTES)
