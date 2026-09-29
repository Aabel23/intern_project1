"""HTTP của đăng nhập: nhận POST từ app, đọc body, gọi flow, gửi JSON trả lời.

    POST /app/dang-nhap           {request_id, username, password}   gửi yêu cầu đăng nhập
    POST /app/xac-minh-dang-nhap  {request_id, login_id}             lấy kết quả (token)
    POST /app/dang-xuat           {token}                            xóa phiên trên server

Đăng nhập chưa cần token nên giới hạn request theo IP (dò mật khẩu). Đăng xuất đã mang
token nên không tính, để kẻ cùng IP dò mật khẩu không chặn được việc xóa phiên.
"""

# Routing tập trung và HTTP dùng chung, phiên đăng nhập
from server.config.routing import USER_SESSION_LOGIN, USER_SESSION_LOGOUT, USER_LOGIN_VERIFY
from server.lib.http.http_json import handle_routes, invalid, with_valid_status
from server.lib.security.user_session import end_session

# Trong module user_login
from .user_login_process import cleanup, receive_login, send_verification


ROUTES = with_valid_status({
    USER_SESSION_LOGIN: receive_login,
    USER_LOGIN_VERIFY: send_verification,
    USER_SESSION_LOGOUT: end_session,
})
MAX_BODY = 4096


def handle(request):
    """True nếu request thuộc module này và đã trả lời (server chính chỉ gọi hàm này)."""
    return handle_routes(request, ROUTES, MAX_BODY, invalid, limited=request.path != USER_SESSION_LOGOUT)


# Dọn phiên đăng nhập hết hạn ngay cả khi không có request mới.
tick = cleanup
