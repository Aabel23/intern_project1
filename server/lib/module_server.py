"""Server HTTP chỉ biết gọi module: mỗi module tự nghe đường dẫn của mình.

Một module là một Python module có:
    handle(request) -> bool       bắt buộc: True nếu request POST thuộc module và đã trả lời
    handle_get(request) -> bool   tùy chọn: như trên cho GET
    tick()                        tùy chọn: việc định kỳ (dọn phiên hết hạn), gọi mỗi ~0,5 giây
"""

# Thư viện chuẩn
import argparse
import importlib
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Server chung: cấu hình, database
from server.config.config import SERVER_HOST, SERVER_PORT
from server.database.machine.init_db import init_db

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


def run_standalone(module_names, title):
    """Chạy riêng vài module trên một cổng: python -m <flow của module> [--port N].

    Nhận TÊN module (vd "server.service.machine_manage.manage_api") và import lúc
    chạy, để file flow gọi hàm này không phải import api của chính nó: api đã
    import flow, import ngược lại sẽ thành vòng.
    """
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=f"Chạy riêng module {title}.")
    parser.add_argument("--port", type=int, default=SERVER_PORT)
    port = parser.parse_args().port
    modules = tuple(importlib.import_module(name) for name in module_names)
    init_db()
    try:
        with ModuleServer((SERVER_HOST, port), make_handler(modules)) as server:
            server.modules = modules
            print(f"{title} chạy riêng: http://{SERVER_HOST}:{port}", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        pass
