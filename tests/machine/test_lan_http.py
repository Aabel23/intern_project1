"""LAN/HTTP transport of the machine against a local fake server (no MySQL, no Pi)."""
import importlib.util
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "version1.1"))

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from pyhpke import KEMKey, AEADId, CipherSuite, KDFId, KEMId

from machine.config import identity as machine_identity
from machine.config import routing
from machine.config.env import get_server_url
from machine.config.identity import b64u, decode_b64u, json_bytes
from machine.server_connection.cloud_protection import CloudError
from machine.server_connection.machine_server_request import ServerClient

SUITE = CipherSuite.new(KEMId.DHKEM_X25519_HKDF_SHA256, KDFId.HKDF_SHA256, AEADId.AES128_GCM)


def load_provision_keys():
    spec = importlib.util.spec_from_file_location("provision_keys_under_test", ROOT / "server" / "tools" / "provision_keys.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeServer:
    """Opens the machine envelope with a real HPKE key and answers with the exporter-keyed response."""

    def __init__(self, handler_factory):
        self.requests = []
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(self))
        self.base = f"http://127.0.0.1:{self.httpd.server_port}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def redirect_handler(server):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            server.requests.append(self.path)
            self.send_response(302)
            self.send_header("Location", server.base + "/elsewhere")
            self.end_headers()
    return Handler


def protocol_handler(server):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass

        def do_POST(self):
            env = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            aad = json_bytes([env["pv"], env["route"], "POST", "server", env["kid"], env["send_id"],
                              env["sent_at_ms"], env["machine_key_id"]])
            recipient = SUITE.create_recipient_context(decode_b64u(env["enc"]), server.hpke_private, info=b"flexmix-cloud-v1")
            body = json.loads(recipient.open(decode_b64u(env["ct"]), aad=aad))["body"]
            server.requests.append((env["route"], body))
            data = {"/machine/hello/send": {"server_time_ms": 1_000_000, "machine_id": "m1", "owned": False},
                    "/machine/command/poll": {"command": {"request_id": "r1", "route": "x"}},
                    "/machine/result/send": {}}[env["route"]]
            status = 200
            plain = json_bytes({"v": 1, "ok": True, "data": data})
            nonce = b"\x01" * 12
            ct = AESGCM(recipient.export(b"flexmix-response-v1", 16)).encrypt(
                nonce, plain, json_bytes(["flexmix-response-v1", env["send_id"], status, env["route"]]))
            out = json_bytes({"pv": 1, "send_id": env["send_id"], "status": status, "nonce": b64u(nonce), "ct": b64u(ct)})
            self.send_response(status)
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
    return Handler


class ClientCase(unittest.TestCase):
    def make_client(self, server):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        identity = machine_identity.provision(Path(tmp.name), "00000000abcdef01")
        pyca = x25519.X25519PrivateKey.generate()
        server.hpke_private = KEMKey.from_pyca_cryptography_key(pyca)
        public = pyca.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        trust = {"v": 1, "hpke": {"kid": "server-hpke-1", "public_key": b64u(public)}}
        return ServerClient(server.base, identity, trust)


class RedirectTests(ClientCase):
    def test_302_is_not_followed(self):
        server = FakeServer(redirect_handler)
        self.addCleanup(server.close)
        client = self.make_client(server)
        with self.assertRaises(CloudError) as caught:
            client.hello()
        self.assertEqual(caught.exception.code, "REDIRECT_REFUSED")
        self.assertEqual(server.requests, [routing.MACHINE_HELLO_SEND])  # no second request


class LoopbackProtocolTests(ClientCase):
    def test_hello_poll_result_over_http(self):
        server = FakeServer(protocol_handler)
        self.addCleanup(server.close)
        client = self.make_client(server)
        self.assertEqual(client.hello()["machine_id"], "m1")
        self.assertEqual(client.poll_command()["request_id"], "r1")
        client.send_result("r1", {"ok": True})
        routes = [r for r, _ in server.requests]
        self.assertEqual(routes[0], routing.MACHINE_HELLO_SEND)
        self.assertIn(routing.MACHINE_COMMAND_POLL, routes)
        self.assertEqual(server.requests[-1], (routing.MACHINE_RESULT_SEND,
                                               {"v": 1, "request_id": "r1", "result": {"ok": True}}))


class PortValidationTests(unittest.TestCase):
    def test_machine_env_rejects_bad_port(self):
        for url in ("http://127.0.0.1:abc", "http://127.0.0.1:99999", "http://127.0.0.1:0",
                    "https://example.invalid:99999", "https://example.invalid:abc"):
            with self.subTest(url=url), patch("machine.config.env.read_env", return_value=url):
                with self.assertRaises(ValueError):
                    get_server_url()
        for url in ("http://127.0.0.1:65535", "https://example.invalid:443", "http://10.0.0.5"):
            with self.subTest(url=url), patch("machine.config.env.read_env", return_value=url):
                self.assertEqual(get_server_url(), url)

    def test_provision_keys_rejects_bad_port(self):
        check_url = load_provision_keys().check_url
        for url in ("http://127.0.0.1:abc", "http://127.0.0.1:99999", "http://127.0.0.1:0", "https://example.invalid:99999"):
            with self.subTest(url=url), self.assertRaises(SystemExit):
                check_url(url)
        self.assertEqual(check_url("http://192.168.1.10:8080/"), "http://192.168.1.10:8080")


if __name__ == "__main__":
    unittest.main()
