"""Vòng lặp của máy: hỏi server lệnh {request_id, instruction, data} → chạy → gửi kết quả lên.

main chỉ tra bảng COMMANDS của các module; module tự kiểm lệnh và tự đụng database.
Chạy từ thư mục version1.1:  python -m machine.main
"""

# Thư viện chuẩn
from collections import OrderedDict
import ssl
import time
import urllib.error

# Danh tính và kết nối server
from machine.config.env import SOFTWARE_VERSION, get_server_trust_path, get_server_url, get_state_dir
from machine.config.identity import load_identity, load_server_trust, read_cache, write_cache
from machine.server_connection.cloud_protection import CloudError
from machine.server_connection.machine_server_request import ServerClient

STARTED = time.monotonic()
RESULT_CACHE_SIZE = 32
_read_sequence = 0


def read_status(data):
    """machine.status.read: mỗi lần hỏi đọc trạng thái hiện tại của chính máy."""
    global _read_sequence
    if data:
        raise ValueError("INVALID_DATA")
    _read_sequence += 1
    return {"serial": _IDENTITY.serial, "software_version": SOFTWARE_VERSION,
            "uptime_seconds": int(time.monotonic() - STARTED), "read_sequence": _read_sequence}


def _business_commands():
    # Nạp module nghiệp vụ version1.1 lúc chạy để test lớp kết nối không cần MySQL máy pha.
    from machine.ingredient_sync.machine_ingredient_request import COMMANDS as INGREDIENT_COMMANDS
    from machine.menu_sync.machine_menu_request import COMMANDS as MENU_COMMANDS
    from machine.order_ticket.machine_order_ticket_request import COMMANDS as TICKET_COMMANDS
    from machine.reporting.machine_reporting_request import COMMANDS as REPORT_COMMANDS
    return {**MENU_COMMANDS, **INGREDIENT_COMMANDS, **TICKET_COMMANDS, **REPORT_COMMANDS}


_IDENTITY = None


class Dispatcher:
    """Chạy lệnh đúng một lần cho mỗi request_id; lệnh trùng trả lại kết quả cũ (v2 D7)."""

    def __init__(self, commands):
        self.commands = commands
        self.results = OrderedDict()

    def handle(self, command):
        request_id = command["request_id"]
        if request_id in self.results:
            return self.results[request_id]
        result = self._run(command)
        self.results[request_id] = result
        while len(self.results) > RESULT_CACHE_SIZE:
            self.results.popitem(last=False)
        return result

    def _run(self, command):
        remaining = command.get("remaining_ms", 0) / 1000 - (time.monotonic() - command.get("_received_monotonic", time.monotonic()))
        if remaining <= 0:
            return {"ok": False, "error": {"code": "COMMAND_EXPIRED"}}
        handler = self.commands.get(command.get("instruction"))
        if handler is None:
            return {"ok": False, "error": {"code": "UNSUPPORTED_INSTRUCTION"}}
        try:
            value = handler(command.get("data") or {})
        except ValueError as error:
            if str(error) == "INVALID_DATA":
                return {"ok": False, "error": {"code": "INVALID_DATA"}}
            # Lỗi kiểm dữ liệu của module version1.1 là thông báo cho người dùng, không phải traceback.
            return {"ok": False, "error": {"code": "COMMAND_FAILED", "message": str(error)[:200]}}
        except Exception:
            return {"ok": False, "error": {"code": "MACHINE_READ_FAILED"}}
        if isinstance(value, dict) and "loi" in value:
            return {"ok": False, "error": {"code": "COMMAND_FAILED", "message": str(value["loi"])[:200]}}
        return {"ok": True, "data": value if isinstance(value, dict) else {"value": value}}


def run(client, dispatcher, state_dir, stop=lambda: False):
    # Không có thread heartbeat: server suy online từ chính poll của vòng này.
    while not stop():
        try:
            if client.machine_id is None:
                client.hello()
            command = client.poll_command()
            # Dịch vụ BLE đọc cache này để báo app máy đã online/đã có chủ chưa.
            write_cache(state_dir, {"machine_id": client.machine_id, "owned": client.owned, "seen_at": time.time()})
        except CloudError as error:
            if error.code == "UNKNOWN_KEY":
                # Khóa không còn được server nhận: dừng, báo Operator; không tự đăng ký khóa khác.
                print("Server khong nhan khoa may (UNKNOWN_KEY); can Operator kiem tra", flush=True)
                return
            print("Loi server:", error.code, flush=True)
            time.sleep(1)
            continue
        except (urllib.error.URLError, OSError, ValueError) as error:
            print("Khong ket noi duoc server:", type(error).__name__, flush=True)
            time.sleep(1)
            continue
        if command is None:
            continue
        print("Machine nhan lenh:", command["instruction"], command["request_id"], flush=True)
        result = dispatcher.handle(command)
        try:
            client.send_result(command["request_id"], result)
        except (CloudError, urllib.error.URLError, OSError) as error:
            print("Khong gui duoc ket qua:", getattr(error, "code", type(error).__name__), flush=True)


def main():
    global _IDENTITY
    state_dir = get_state_dir()
    _IDENTITY = load_identity(state_dir)
    client = ServerClient(get_server_url(), _IDENTITY, load_server_trust(get_server_trust_path()), ssl.create_default_context())
    cache = read_cache(state_dir)
    client.machine_id = cache.get("machine_id")
    run(client, Dispatcher({"machine.status.read": read_status, **_business_commands()}), state_dir)


if __name__ == "__main__":
    main()
