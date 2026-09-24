"""Route đăng ký tài khoản + OTP; server.main gộp vào cùng cổng với các API khác."""

from server.config.routing import APP_REGISTER_USER, APP_SEND_OTP, APP_VERIFY_OTP
from .registration_flow import confirm_otp, receive_register, resend_otp


ROUTES = {
    APP_REGISTER_USER: receive_register,
    APP_SEND_OTP: resend_otp,
    APP_VERIFY_OTP: confirm_otp,
}
