"""Server HTTP chỉ biết gọi module: mỗi module tự nghe đường dẫn của mình.

Một module là một Python module có:
    handle(request) -> bool       bắt buộc: True nếu request POST thuộc module và đã trả lời
    handle_get(request) -> bool   tùy chọn: như trên cho GET
    tick()                        tùy chọn: việc định kỳ (dọn phiên hết hạn), gọi mỗi ~0,5 giây
"""

# Thư viện chuẩn
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Trong lib
from .http_json import send_json


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
            send_json(self, {"valid": False, "message": "Không có endpoint này"}, 404)

    return Handler


class ModuleServer(ThreadingHTTPServer):
    modules = ()

    def service_actions(self):
        for module in self.modules:
            tick = getattr(module, "tick", None)
            if tick is not None:
                tick()

