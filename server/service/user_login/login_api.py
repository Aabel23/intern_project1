"""Route đăng nhập/đăng xuất; module tự nghe, server.main chỉ gọi handle()/tick()."""

from server.config.routing import APP_LOGIN, APP_LOGOUT, APP_VERIFY_LOGIN
from server.lib.valid_api import handle_valid_routes
from .login_flow import cleanup, receive_login, send_verification
from .session import end_session


ROUTES = {
    APP_LOGIN: receive_login,
    APP_VERIFY_LOGIN: send_verification,
    APP_LOGOUT: end_session,
}


def handle(request):
    """True nếu request thuộc module này và đã trả lời (server chính chỉ gọi hàm này)."""
    return handle_valid_routes(request, ROUTES, limited=True)


# Dọn phiên đăng nhập hết hạn ngay cả khi không có request mới.
tick = cleanup
