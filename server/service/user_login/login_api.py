"""HTTP của đăng nhập: nhận POST từ app, đọc body, gọi flow, gửi JSON trả lời.

    POST /app/dang-nhap           {request_id, username, password}   gửi yêu cầu đăng nhập
    POST /app/xac-minh-dang-nhap  {request_id, login_id}             lấy kết quả (token)
    POST /app/dang-xuat           {token}                            xóa phiên trên server

Chưa cần token nên giới hạn request theo IP (dò mật khẩu).
"""

# Server chung: đường dẫn, xử lý HTTP, phiên đăng nhập
from server.config.routing import APP_LOGIN, APP_LOGOUT, APP_VERIFY_LOGIN
from server.lib.http_json import handle_routes, invalid, with_valid_status
from server.lib.session import end_session

# Trong module user_login
from .login_flow import cleanup, receive_login, send_verification

ROUTES = with_valid_status({
    APP_LOGIN: receive_login,
    APP_VERIFY_LOGIN: send_verification,
    APP_LOGOUT: end_session,
})
MAX_BODY = 4096


def handle(request):
    """True nếu request thuộc module này và đã trả lời (server chính chỉ gọi hàm này)."""
    return handle_routes(request, ROUTES, MAX_BODY, invalid, limited=True)


# Dọn phiên đăng nhập hết hạn ngay cả khi không có request mới.
tick = cleanup
