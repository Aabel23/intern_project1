"""HTTP của đăng nhập: nhận POST từ app, đọc body, gọi flow, gửi JSON trả lời.

    POST /app/user/session/login   {username, password}  kiểm tài khoản, trả token
    POST /app/user/session/logout  {token}               xóa phiên trên server

Đăng nhập chưa cần token nên giới hạn request theo IP (dò mật khẩu). Đăng xuất đã mang
token nên không tính, để kẻ cùng IP dò mật khẩu không chặn được việc xóa phiên.
"""

# Routing tập trung và HTTP dùng chung, phiên đăng nhập
from server.config.routing import USER_SESSION_LOGIN, USER_SESSION_LOGOUT
from server.lib.http.http_json import handle_routes, invalid, with_valid_status
from server.lib.security.user_session import end_session

# Trong module user_login
from .user_login_process import receive_login


ROUTES = with_valid_status({
    USER_SESSION_LOGIN: receive_login,
    USER_SESSION_LOGOUT: end_session,
})
MAX_BODY = 4096


def handle(request):
    """True nếu request thuộc module này và đã trả lời (server chính chỉ gọi hàm này)."""
    return handle_routes(request, ROUTES, MAX_BODY, invalid, limited=request.path != USER_SESSION_LOGOUT)