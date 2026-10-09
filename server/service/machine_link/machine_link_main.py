"""HTTP phía máy: chỉ máy gọi các route này, xưng danh bằng product key.

    POST /machine/heartbeat/send  {product_key}               mỗi 5 giây, báo còn sống
    POST /machine/command/poll    {product_key}               long-poll lấy lệnh {id, instruction, data}
    POST /machine/result/send     {product_key, id, ket_qua}  gửi kết quả lệnh

Module khác gửi lệnh xuống máy bằng machine_transport.send(), không qua file này.
"""

# Routing tập trung và HTTP dùng chung
from server.config.routing import MACHINE_HEARTBEAT_SEND, MACHINE_COMMAND_POLL, MACHINE_RESULT_SEND
from server.lib.http.http_json import handle_routes

# Trong module machine_link
from .machine_link_process import heartbeat, poll, send_result


ROUTES = {
    MACHINE_HEARTBEAT_SEND: heartbeat,
    MACHINE_COMMAND_POLL: poll,
    MACHINE_RESULT_SEND: send_result,
}
# Kết quả máy trả (gói menu, danh sách kho) lớn hơn các gói tài khoản.
MAX_BODY = 1_000_000


def handle(request):
    """True nếu request thuộc module này và đã trả lời (server chính chỉ gọi hàm này)."""
    return handle_routes(request, ROUTES, MAX_BODY, lambda message: {"loi": message})
