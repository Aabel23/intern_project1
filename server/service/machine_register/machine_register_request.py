"""HTTP của đăng ký máy: nhận POST từ app, đọc body, gọi flow, gửi JSON trả lời.

    POST /app/dang-ky-may  {token, machine_name, product_key, type?}   quét tem QR / nhận gói Bluetooth
"""

# Routing tập trung và HTTP dùng chung
from server.config.routing import USER_MACHINE_REGISTER
from server.lib.http_json import handle_routes, invalid, with_valid_status

# Trong module machine_register
from .machine_register_process import receive_register


ROUTES = with_valid_status({
    USER_MACHINE_REGISTER: receive_register,
})
MAX_BODY = 4096


def handle(request):
    """True nếu request thuộc module này và đã trả lời (server chính chỉ gọi hàm này)."""
    return handle_routes(request, ROUTES, MAX_BODY, invalid)
