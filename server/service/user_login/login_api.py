"""Route đăng nhập/đăng xuất; server.main gộp vào cùng cổng với các API khác."""

from server.config.routing import APP_LOGIN, APP_LOGOUT, APP_VERIFY_LOGIN
from .login_flow import receive_login, send_verification
from .session import end_session


ROUTES = {
    APP_LOGIN: receive_login,
    APP_VERIFY_LOGIN: send_verification,
    APP_LOGOUT: end_session,
}
