"""HTTP phía máy: chỉ máy gọi các route này, xưng danh bằng product key.

    POST /machine/heartbeat    {product_key}                  mỗi 5 giây, báo còn sống
    POST /machine/hoi-lenh     {product_key}                  long-poll lấy lệnh {id, instruction, data}
    POST /machine/tra-ket-qua  {product_key, id, ket_qua}     gửi kết quả lệnh

Module khác gửi lệnh xuống máy bằng relay_queue.send(), không qua file này.
"""

# Server chung: đường dẫn, xử lý HTTP
from server.config.routing import MACHINE_HEARTBEAT, MACHINE_POLL_COMMAND, MACHINE_SEND_RESULT
from server.lib.http_json import handle_routes

# Trong module machine_relay
from .relay_flow import heartbeat, poll, send_result

ROUTES = {
    MACHINE_HEARTBEAT: heartbeat,
    MACHINE_POLL_COMMAND: poll,
    MACHINE_SEND_RESULT: send_result,
}
# Kết quả máy trả (gói menu, danh sách kho) lớn hơn các gói tài khoản.
MAX_BODY = 1_000_000


def handle(request):
    """True nếu request thuộc module này và đã trả lời (server chính chỉ gọi hàm này)."""
    return handle_routes(request, ROUTES, MAX_BODY, lambda message: {"loi": message})
