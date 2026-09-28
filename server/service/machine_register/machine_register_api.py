"""Route đăng ký máy; module tự nghe, server.main chỉ gọi handle()."""

from server.config.routing import APP_REGISTER_MACHINE, APP_REGISTER_MACHINE_VERIFY
from server.lib.valid_api import handle_valid_routes
from .machine_register_flow import receive_register
from .machine_register_verify import verify_registration


ROUTES = {
    APP_REGISTER_MACHINE: receive_register,
    APP_REGISTER_MACHINE_VERIFY: verify_registration,
}


def handle(request):
    """True nếu request thuộc module này và đã trả lời (server chính chỉ gọi hàm này)."""
    return handle_valid_routes(request, ROUTES)
