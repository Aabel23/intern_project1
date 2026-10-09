"""Đường dẫn và trần gói agent, đối chiếu với server/config/routing.py.

VÌ SAO TÁCH RIÊNG
    Route và giới hạn byte là hợp đồng với server. Tập trung chúng ở đây
    để đổi hợp đồng có một chỗ đối chiếu, còn net.py chỉ xử lý vận chuyển.

CÁCH DÙNG VÀ KIỂM
    from agent.routing import ROUTES
    path, request_limit, response_limit = ROUTES["AGENT_HELLO_PATH"]
    python3 -m unittest agent.tests.test_net -v

    Khi server đổi ROUTE_POLICY, so lại cả đường dẫn và hai giới hạn trước
    khi phát hành agent; không tự thêm route chưa được server hỗ trợ.
"""

ROUTES = {
    "AGENT_ENROLL_PATH": ("/api/agent/enroll", 4096, 4096),
    "AGENT_HELLO_PATH": ("/api/agent/hello", 256 * 1024, 4096),
    "AGENT_COMMANDS_PATH": ("/api/agent/commands", 1024, 64 * 1024),
    "AGENT_RESULTS_PATH": ("/api/agent/results", 256 * 1024, 16 * 1024),
    "AGENT_MENU_PATH": ("/api/agent/menu", 1024, 2 * 1024 * 1024),
    "AGENT_MENU_ACK_PATH": ("/api/agent/menu/ack", 64 * 1024, 1024),
    "AGENT_ORDERS_PATH": ("/api/agent/orders", 256 * 1024, 1024),
    "AGENT_ERRORS_PATH": ("/api/agent/errors", 256 * 1024, 1024),
    "AGENT_STOCK_PATH": ("/api/agent/stock", 16 * 1024, 1024),
}
