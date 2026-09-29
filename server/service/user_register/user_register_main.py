"""HTTP của đăng ký tài khoản: nhận POST từ app, đọc body, gọi flow, gửi JSON trả lời.

    POST /app/dang-ky-nguoi-dung  {request_id, full_name, username, password, email}
    POST /app/gui-ma-otp          {registration_id}          gửi lại OTP
    POST /app/xac-minh-otp        {registration_id, code}    xác minh OTP, tạo tài khoản

Chưa cần token nên giới hạn request theo IP (spam OTP).
"""

# Routing tập trung và HTTP dùng chung
from server.config.routing import USER_ACCOUNT_REGISTER, USER_OTP_SEND, USER_OTP_VERIFY
from server.lib.http.http_json import handle_routes, invalid, with_valid_status

# Trong module user_register
from .user_register_process import cleanup, confirm_otp, receive_register, resend_otp


ROUTES = with_valid_status({
    USER_ACCOUNT_REGISTER: receive_register,
    USER_OTP_SEND: resend_otp,
    USER_OTP_VERIFY: confirm_otp,
})
MAX_BODY = 4096


def handle(request):
    """True nếu request thuộc module này và đã trả lời (server chính chỉ gọi hàm này)."""
    return handle_routes(request, ROUTES, MAX_BODY, invalid, limited=True)


# Dọn phiên đăng ký/OTP hết hạn ngay cả khi không có request mới.
tick = cleanup
