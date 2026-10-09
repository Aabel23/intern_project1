"""Kiểm ranh giới HTTPS và FM1 bằng codec/response giả.

VÌ SAO CÓ TEST NÀY
    HTTP 401 không được biến thành revoked; body vượt trần phải bị chặn
    trước khi gửi và route phải đi đúng URL của server.

CÁCH CHẠY
    python3 -m unittest agent.tests.test_net -v
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.net import AgentNet, Endpoint, TransportError


class Codec:
    def seal(self, route_id, body):
        return body, object()

    def open(self, attempt, response):
        return "ok", {"received": True}


class Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, limit):
        return b"sealed"


class NetTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        ca = Path(self.tmp.name) / "ca.crt"
        ca.write_text("placeholder")
        self.endpoint = Endpoint("https://server.example:8443", ca)

    def tearDown(self):
        self.tmp.cleanup()

    def make_net(self):
        with patch("agent.net.ssl.create_default_context"):
            return AgentNet(self.endpoint, Codec())

    def test_rejects_http_and_url_credentials(self):
        for url in ("http://server.example", "https://u:p@server.example",
                    "https://server.example/path"):
            with self.assertRaises(ValueError):
                Endpoint(url, self.endpoint.ca_file)

    def test_http_401_is_transport_error_not_revoked(self):
        from urllib.error import HTTPError
        net = self.make_net()
        with patch.object(net._opener, "open", side_effect=HTTPError("url", 401, "", {}, None)):
            with self.assertRaises(TransportError):
                net.call("AGENT_HELLO_PATH", {})
        self.assertEqual(net.retry_delay(), 1)

    def test_authenticated_response_and_new_attempt(self):
        net = self.make_net()
        with patch.object(net._opener, "open", return_value=Response()) as opened:
            self.assertEqual(net.call("AGENT_HELLO_PATH", {}), ("ok", {"received": True}))
            self.assertEqual(opened.call_args.args[0].full_url,
                             "https://server.example:8443/api/agent/hello")

    def test_rejects_oversized_body_before_network(self):
        net = self.make_net()
        with self.assertRaises(ValueError):
            net.call("AGENT_COMMANDS_PATH", {"x": "a" * 1024})


if __name__ == "__main__":
    unittest.main()
