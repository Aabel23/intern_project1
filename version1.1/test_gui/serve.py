"""Serve the manual test screen and run what it asks for.

WHAT THIS IS FOR
    Exercising the machine by hand: prime one pump, prime all of them,
    walk the panel lamps, check every button answers. The things you want
    after changing a tube, moving the machine, or before opening.

    It is a workshop tool, not part of an order. Nothing here is reachable
    from the store screen and it refuses to run while an order is in
    progress -- see test_gui/hardware.py.

WHY THE WORK HAPPENS ON A WORKER THREAD
    Priming ten pumps takes over a minute and a lamp test is a minute more.
    Holding an HTTP request open that long means a browser timeout in the
    middle of a pour, and ThreadingHTTPServer would happily run a second
    request beside the first -- two threads inside the same I2C bus and
    HX711. So a request only starts a job or reads its progress, and one
    job runs at a time.

RUNNING IT
    python3 -m test_gui.serve                # http://<pi>:8090/test_gui/
    python3 -m test_gui.serve --port 9100
    python3 -m test_gui.serve --local        # this machine only

    Stop order/run_flow.py first: it owns the pumps and the panel while an
    order is running, and this will refuse to start a job until it is gone.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


TEST_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TEST_DIR.parent

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from configuration import net_addresses                          # noqa: E402
from configuration import served_paths                          # noqa: E402
from configuration import machine                                # noqa: E402
from test_gui import hardware                                    # noqa: E402


# Deliberately not 8000 (the runner) or 8080/8081 (the store screen), so
# this can be left running without ever colliding with a real order.
DEFAULT_PORT = machine.TEST_STANDALONE_PORT
TEST_PAGE = "/test_gui/index.html"

NEVER_CACHE = (".js", ".css", ".html", ".json")


# The endpoints this screen calls, and the one place they are handled.
# Pulled out of the handler so store_gui/serve.py can answer them too: the
# test screen is served from that one public port now, and duplicating this
# dispatch there is how the two would drift apart.
TEST_GET_PATHS = ("/api/status",)
TEST_POST_PATHS = (
    "/api/stop",
    "/api/pump/hold",
    "/api/pump/release",
    "/api/prime",
    "/api/panel/leds",
    "/api/panel/buttons",
    "/api/scale",
)


def handle_get(path: str) -> tuple[int, dict] | None:
    """Answer a test-screen GET, or None if the path is not one of ours."""
    if path != "/api/status":
        return None

    snapshot = hardware.JOB.snapshot()
    snapshot["busy_reason"] = hardware.order_in_progress()
    snapshot["held_pump"] = hardware.held_pump()

    return 200, snapshot


def handle_post(path: str, body: dict) -> tuple[int, dict] | None:
    """Answer a test-screen POST, or None if the path is not one of ours."""
    if path == "/api/stop":
        hardware.stop()
        return 200, {"ok": True}

    # Hold-to-run. Sent repeatedly while the button is down, and the pump
    # stops by itself when they stop arriving -- so a closed tab or a
    # dropped connection cannot leave it pouring. Handled before _dispatch()
    # because these answer directly instead of starting a job.
    if path == "/api/pump/hold":
        try:
            pump = int(body.get("pump"))
        except (TypeError, ValueError):
            return 400, {"ok": False, "error": "Thiếu số bơm."}

        ok, message = hardware.hold_pump(pump, str(body.get("token") or ""))

        return (200, {"ok": True, "held": message}) if ok \
            else (409, {"ok": False, "error": message})

    if path == "/api/pump/release":
        hardware.release_pump(str(body.get("token") or ""))
        return 200, {"ok": True}

    started, why = _dispatch_job(path, body or {})

    if started is None:
        return None

    return (200 if started else 409), {"ok": started, "error": why}


def _dispatch_job(path: str, body: dict):
    """Map an endpoint to a job. Returns (started, why-not) or (None, '')."""
    if path == "/api/prime":
        pumps = body.get("pumps")

        if pumps in (None, "all", []):
            return hardware.start("prime-all", hardware.prime_job(None))

        try:
            wanted = [int(p) for p in pumps]
        except (TypeError, ValueError):
            return False, "Danh sách bơm không hợp lệ."

        name = f"prime-{','.join(str(p) for p in wanted)}"
        return hardware.start(name, hardware.prime_job(wanted))

    if path == "/api/panel/leds":
        return hardware.start("panel-leds", hardware.led_job)

    if path == "/api/panel/buttons":
        return hardware.start("panel-buttons", hardware.button_job)

    if path == "/api/scale":
        return hardware.start("scale", hardware.scale_job)

    return None, ""


class TestHandler(SimpleHTTPRequestHandler):
    """Static files, plus the handful of endpoints the page calls."""

    def translate_path(self, path: str) -> str:
        """Refuse anything outside the served directories -- 404, not 403.

        The whole project directory is this server's document root, so
        without this a browser can ask for .env or configuration/ and get
        them. See configuration/served_paths.py.
        """
        return served_paths.guard(super().translate_path(path))


    def end_headers(self) -> None:
        if self.path.split("?")[0].endswith(NEVER_CACHE):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        answer = handle_get(path)

        if answer is not None:
            self._json(*answer)
            return

        super().do_GET()

    def do_POST(self) -> None:
        path = self.path.split("?")[0]

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, OSError):
            self._json(400, {"ok": False, "error": "Body không hợp lệ."})
            return

        answer = handle_post(path, body if isinstance(body, dict) else {})

        if answer is None:
            self.send_error(404, "Unknown endpoint")
            return

        self._json(*answer)

    def _json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args: object) -> None:
        """Quiet: the page polls /api/status about twice a second."""
        status = str(args[1]) if len(args) > 1 else ""
        request = str(args[0]) if args else ""

        if status.startswith(("4", "5")) or "/api/status" not in request:
            super().log_message(fmt, *args)


def local_addresses() -> list[str]:
    """Addresses this machine can likely be reached on."""
    found: list[str] = []

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            found.append(probe.getsockname()[0])
    except OSError:
        pass

    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Màn hình test tay cho máy pha chế.",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--local", action="store_true",
                        help="Chỉ cho máy này truy cập (đã là mặc định).")
    parser.add_argument("--host", default=None, metavar="ĐỊA_CHỈ",
                        help="Nghe trên đúng địa chỉ này. 0.0.0.0 = mọi "
                             "mạng — CHỈ dùng khi phát triển.")
    args = parser.parse_args(argv)

    # Mặc định LOOPBACK, không phải 0.0.0.0.
    #
    # Server này phục vụ /api/prime, /api/pump/hold, /api/panel/leds --
    # điều khiển phần cứng, và KHÔNG endpoint nào cần đăng nhập. Bản trước
    # mặc định mọi mạng, nghĩa là ai chạy nó bằng tay là cho cả Wi-Fi quán
    # quyền chạy bơm. main.py không mở cổng này nên máy bán hàng không bị.
    host = args.host or net_addresses.LOOPBACK_HOST
    handler = partial(TestHandler, directory=str(PROJECT_DIR))

    try:
        server = ThreadingHTTPServer((host, args.port), handler)
    except OSError as error:
        print(f"LỖI: không mở được cổng {args.port}: {error}", file=sys.stderr)
        return 1

    print(f"Màn hình test tay đang chạy trên cổng {args.port}.")
    # The button is watched by order/run_flow.py, not here -- see
    # panel_control/button_watch.py. This server only serves the page and
    # runs the jobs it asks for.
    print(f"Nút bảng số {hardware.TOGGLE_PANEL_ID} bật/tắt chế độ test "
          f"(do order/run_flow.py theo dõi).")
    print(f"  http://localhost:{args.port}{TEST_PAGE}")

    for address in local_addresses():
        print(f"  http://{address}:{args.port}{TEST_PAGE}")

    busy = hardware.order_in_progress()

    if busy:
        print(f"\nLƯU Ý: {busy}")

    print("\nCtrl+C để dừng.", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng.")
    finally:
        hardware.stop()
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
