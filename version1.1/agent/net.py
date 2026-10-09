"""Kênh HTTPS cho agent; codec FM1 được truyền vào từ khối mật mã.

VÌ SAO CÓ LỚP NÀY
    Chỉ response đã mở và xác thực mới có quyền báo máy bị thu hồi. HTTP
    401, mất mạng hoặc gói hỏng đều là lỗi vận chuyển và cần lùi rồi thử lại.
    CA ghim và lệnh cấm redirect giữ request trên đúng server HTTPS.

CÁCH DÙNG VÀ KIỂM
    net = AgentNet(endpoint, fm1_codec)
    status, body = net.call("AGENT_HELLO_PATH", hello_body)
    python3 -m unittest agent.tests.test_net -v

    fm1_codec phải do khối mật mã thật cung cấp. Không dùng codec giả trong
    test để kết nối server thật; hiện server chưa có S-FM1 chạy thật.
"""

from __future__ import annotations

import json
import ssl
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from agent.routing import ROUTES


BACKOFF = (1, 2, 5, 10, 30)


class Codec(Protocol):
    def seal(self, route_id: str, body: bytes) -> tuple[bytes, object]: ...
    def open(self, attempt: object, response: bytes) -> tuple[str, dict]: ...


class TransportError(Exception):
    """Lỗi kết nối hoặc gói chưa được xác thực."""


class NoRedirect(HTTPRedirectHandler):
    # Redirect có thể đổi sang HTTP hoặc host khác, làm mất ràng buộc CA/route.
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class Endpoint:
    base_url: str
    ca_file: Path

    def __post_init__(self) -> None:
        url = urlsplit(self.base_url)
        if (url.scheme != "https" or not url.hostname or url.username or
                url.password or url.query or url.fragment or url.path not in ("", "/")):
            raise ValueError("Agent chỉ nhận URL gốc HTTPS của server")
        if not self.ca_file.is_file():
            raise ValueError("Thiếu CA đã ghim")


class AgentNet:
    def __init__(self, endpoint: Endpoint, codec: Codec, *, timeout: float = 35):
        self.endpoint = endpoint
        self.codec = codec
        self.timeout = timeout
        context = ssl.create_default_context(cafile=str(endpoint.ca_file))
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        self._opener = build_opener(HTTPSHandler(context=context), NoRedirect())
        self._failures = 0

    def call(self, route_id: str, body: dict) -> tuple[str, dict]:
        if route_id not in ROUTES or not isinstance(body, dict):
            raise ValueError("Route hoặc body không hợp lệ")
        path, request_limit, response_limit = ROUTES[route_id]
        plain = json.dumps(body, ensure_ascii=False, separators=(",", ":"),
                           allow_nan=False).encode("utf-8")
        if len(plain) > request_limit:
            raise ValueError("Body vượt trần route")
        # Codec phải sinh attempt mới cho mỗi call, kể cả lần retry sau lỗi.
        wire, attempt = self.codec.seal(route_id, plain)
        request = Request(self.endpoint.base_url.rstrip("/") + path, data=wire,
                          headers={"Content-Type": "application/octet-stream"},
                          method="POST")
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise TransportError("HTTP không thành công")
                wire_response = response.read(response_limit + 4096 + 1)
                if len(wire_response) > response_limit + 4096:
                    raise TransportError("Response vượt trần")
            status, result = self.codec.open(attempt, wire_response)
        except (HTTPError, URLError, OSError, ssl.SSLError) as exc:
            self._failures += 1
            raise TransportError("Không kết nối hoặc xác thực được server") from exc
        except TransportError:
            self._failures += 1
            raise
        except Exception as exc:
            self._failures += 1
            raise TransportError("Không mở được response FM1") from exc
        if status not in {"ok", "bad_request", "not_found", "conflict",
                          "epoch_changed", "error", "revoked"} or not isinstance(result, dict):
            self._failures += 1
            raise TransportError("Response FM1 sai schema")
        self._failures = 0
        return status, result

    def retry_delay(self) -> int:
        return BACKOFF[min(max(self._failures - 1, 0), len(BACKOFF) - 1)]

    def call_with_retry(self, route_id: str, body: dict, *, stop=None):
        while stop is None or not stop.is_set():
            try:
                return self.call(route_id, body)
            except TransportError:
                if stop is None:
                    time.sleep(self.retry_delay())
                elif stop.wait(self.retry_delay()):
                    break
        return None
