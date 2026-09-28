"""Route đăng ký tài khoản + OTP; module tự nghe, server.main chỉ gọi handle()/tick()."""

from server.config.routing import APP_REGISTER_USER, APP_SEND_OTP, APP_VERIFY_OTP
from server.lib.valid_api import handle_valid_routes
from .registration_flow import cleanup, confirm_otp, receive_register, resend_otp


ROUTES = {
    APP_REGISTER_USER: receive_register,
    APP_SEND_OTP: resend_otp,
    APP_VERIFY_OTP: confirm_otp,
}


def handle(request):
    """True nếu request thuộc module này và đã trả lời (server chính chỉ gọi hàm này)."""
    return handle_valid_routes(request, ROUTES, limited=True)


# Dọn phiên đăng ký/OTP hết hạn ngay cả khi không có request mới.
tick = cleanup
