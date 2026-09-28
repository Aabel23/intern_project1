"""HTTP của đăng ký tài khoản: nhận POST từ app, đọc body, gọi flow, gửi JSON trả lời.

    POST /app/dang-ky-nguoi-dung  {request_id, full_name, username, password, email}
    POST /app/gui-ma-otp          {registration_id}          gửi lại OTP
    POST /app/xac-minh-otp        {registration_id, code}    xác minh OTP, tạo tài khoản

Chưa cần token nên giới hạn request theo IP (spam OTP).
"""

# Server chung: đường dẫn, xử lý HTTP
from server.config.routing import APP_REGISTER_USER, APP_SEND_OTP, APP_VERIFY_OTP
from server.lib.http_json import handle_routes, invalid, with_valid_status

# Trong module user_register
from .user_register_flow import cleanup, confirm_otp, receive_register, resend_otp

ROUTES = with_valid_status({
    APP_REGISTER_USER: receive_register,
    APP_SEND_OTP: resend_otp,
    APP_VERIFY_OTP: confirm_otp,
})
MAX_BODY = 4096


def handle(request):
    """True nếu request thuộc module này và đã trả lời (server chính chỉ gọi hàm này)."""
    return handle_routes(request, ROUTES, MAX_BODY, invalid, limited=True)


# Dọn phiên đăng ký/OTP hết hạn ngay cả khi không có request mới.
tick = cleanup
