"""Route đăng ký máy; server.main gộp vào cùng cổng với các API khác."""

from server.config.routing import APP_REGISTER_MACHINE, APP_REGISTER_MACHINE_VERIFY
from .machine_register_flow import receive_register
from .machine_register_verify import verify_registration


ROUTES = {
    APP_REGISTER_MACHINE: receive_register,
    APP_REGISTER_MACHINE_VERIFY: verify_registration,
}
