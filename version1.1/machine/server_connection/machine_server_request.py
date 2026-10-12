"""Các hàm giao tiếp HTTPS giữa machine và server (relay-status.md, v2 D7).

Đồng hồ gửi = giờ server lấy từ hello + monotonic kể từ lúc nhận, nên Pi không cần RTC/NTP.
"""

import json
import ssl
import threading
import time
import urllib.error
import urllib.request

from machine.config.routing import MACHINE_COMMAND_POLL, MACHINE_HELLO_SEND, MACHINE_RESULT_SEND
from machine.server_connection.cloud_protection import CloudError, open_response, seal_request

POLL_HTTP_SECONDS = 25   # lớn hơn thời gian server giữ poll (20 s)
SHORT_HTTP_SECONDS = 10
CLOCK_REFRESH_SECONDS = 300


class ServerClient:
    def __init__(self, base_url, identity, trust, ssl_context=None, monotonic=time.monotonic):
        self.base_url = base_url.rstrip("/")
        self.identity = identity
        self.trust = trust
        self.ssl_context = ssl_context or ssl.create_default_context()
        self.monotonic = monotonic
        self._server_time = None
        self._receipt = 0.0
        self._lock = threading.Lock()
        self.machine_id = None
        self.owned = None

    def _post(self, route, body, sent_at_ms, timeout):
        sealed = seal_request(route, body, sent_at_ms, self.identity, self.trust)
        request = urllib.request.Request(self.base_url + route, data=json.dumps(sealed.envelope).encode("utf-8"),
                                         headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=self.ssl_context) as response:
                status, raw = response.status, response.read(65537)
        except urllib.error.HTTPError as error:
            status, raw = error.code, error.read(65537)
        if len(raw) > 65536:
            raise CloudError("INVALID_RESPONSE", status)
        try:
            outer = json.loads(raw)
        except ValueError:
            raise CloudError("INVALID_RESPONSE", status) from None
        try:
            return open_response(sealed, status, outer)
        except CloudError as error:
            if error.code == "INVALID_ENVELOPE":
                # Lệch giờ hay server vừa khởi động lại: lấy lại giờ trước request kế tiếp.
                with self._lock:
                    self._server_time = None
            raise

    def hello(self):
        """Lấy giờ server và machine_id; hello không đánh dấu online (chỉ poll mới tính)."""
        sent = self.monotonic()
        data = self._post(MACHINE_HELLO_SEND, {"v": 1}, 0, SHORT_HTTP_SECONDS)
        received = self.monotonic()
        if received - sent > 5 or not isinstance(data.get("server_time_ms"), int):
            raise CloudError("INVALID_RESPONSE")
        with self._lock:
            self._server_time, self._receipt = data["server_time_ms"], received
        self.machine_id, self.owned = data.get("machine_id"), data.get("owned")
        return data

    def now_ms(self):
        with self._lock:
            fresh = self._server_time is not None and self.monotonic() - self._receipt < CLOCK_REFRESH_SECONDS
        if not fresh:
            self.hello()
        with self._lock:
            return self._server_time + int((self.monotonic() - self._receipt) * 1000)

    def poll_command(self):
        """Lệnh kế tiếp hoặc None khi hết giờ long-poll."""
        data = self._post(MACHINE_COMMAND_POLL, {"v": 1}, self.now_ms(), POLL_HTTP_SECONDS)
        command = data.get("command")
        if command is not None:
            command["_received_monotonic"] = self.monotonic()
        return command

    def send_result(self, request_id, result):
        self._post(MACHINE_RESULT_SEND, {"v": 1, "request_id": request_id, "result": result},
                   self.now_ms(), SHORT_HTTP_SECONDS)
