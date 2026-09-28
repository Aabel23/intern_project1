"""Server HTTP chỉ biết gọi module: mỗi module tự nghe đường dẫn của mình.

Một module là một Python module có:
    handle(request) -> bool       bắt buộc: True nếu request POST thuộc module và đã trả lời
    handle_get(request) -> bool   tùy chọn: như trên cho GET
    setup()                       tùy chọn: tạo/cập nhật dữ liệu riêng khi lắp module
    tick()                        tùy chọn: việc định kỳ (dọn phiên hết hạn), gọi mỗi ~0,5 giây
"""

# Thư viện chuẩn
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Trong lib
from .http_json import discard_body, send_json


def make_handler(modules):
    class Handler(BaseHTTPRequestHandler):
        timeout = 10

        def do_GET(self):
            for module in modules:
                handle_get = getattr(module, "handle_get", None)
                if handle_get is not None and handle_get(self):
                    return
            self.send_error(404)

        def do_POST(self):
            for module in modules:
                if module.handle(self):
                    return
            # Route của module đã tháo vẫn phải trả được 404 khi client gửi body.
            discard_body(self, 4096)
            send_json(self, {"valid": False, "message": "Không có endpoint này"}, 404)

    return Handler


class ModuleServer(ThreadingHTTPServer):
    def __init__(self, address, modules):
        self.modules = tuple(modules)
        # Trùng route phải báo ngay khi lắp, tránh module trước che mất module sau.
        owners = {}
        for module in self.modules:
            for method, routes in (("POST", module.ROUTES), ("GET", getattr(module, "GET_ROUTES", ()))):
                for path in routes:
                    key = (method, path)
                    if key in owners:
                        raise ValueError(f"Trùng route {method} {path}: {owners[key]} và {module.__name__}")
                    owners[key] = module.__name__
        for module in self.modules:
            setup = getattr(module, "setup", None)
            if setup is not None:
                setup()
        super().__init__(address, make_handler(self.modules))

    def service_actions(self):
        for module in self.modules:
            tick = getattr(module, "tick", None)
            if tick is not None:
                tick()

