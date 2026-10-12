"""App Kotlin (ClaimProtocol.kt + Bouncy Castle) <-> machine Python (ClaimSession + PyHPKE), byte for byte.

Needs the JVM harness: (cd tests/kotlin-interop && gradle installDist).
"""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "version1.1"))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from machine.config import identity as machine_identity
from machine.config.identity import b64u, decode_b64u, json_bytes
from machine.pairing.claim_crypto import accept_bytes, challenge_bytes, verify_raw
from machine.pairing.claim_session import ClaimSession, SessionClosed

HARNESS = ROOT / "tests" / "kotlin-interop" / "build" / "install" / "flexmix-kotlin-interop" / "bin" / "flexmix-kotlin-interop"


@unittest.skipUnless(HARNESS.exists(), "build tests/kotlin-interop first (gradle installDist)")
class KotlinInteropTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.identity = machine_identity.provision(self.tmp.name, "00000000abcdef01")
        self.seal = machine_identity.load_seal_code(self.tmp.name)
        self.server_key = ec.generate_private_key(ec.SECP256R1())
        self.server_public = self.server_key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        self.wifi = []
        self.machine_id = str(uuid.uuid4())
        self.app = subprocess.Popen([str(HARNESS)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

    def tearDown(self):
        if self.app.poll() is None:
            self.app.kill()
        self.app.stdout.close(); self.app.stdin.close()
        self.tmp.cleanup()

    def send(self, line):
        self.app.stdin.write(line + "\n"); self.app.stdin.flush()

    def read(self, verb):
        line = self.app.stdout.readline().strip()
        self.assertTrue(line.startswith(verb + " "), line)
        return line[len(verb) + 1:]

    def start(self, seal):
        self.machine = ClaimSession(self.identity, self.seal, self.server_public,
                                    lambda ssid, password: self.wifi.append((ssid, password)) or {"ok": True},
                                    lambda: (self.machine_id, True))
        self.send("serial " + self.identity.serial)
        self.send("seal " + b64u(seal))
        self.send("hello " + b64u(self.machine.hello_packet))

    def exchange(self, command):
        self.send(command)
        request = decode_b64u(self.read("request"))
        try:
            response = self.machine.handle(request)
        except SessionClosed as closed:
            response = closed.response
        self.send("response " + b64u(response))
        return response

    def test_full_session_wifi_then_claim(self):
        self.start(self.seal)
        self.exchange("probe x")
        import json
        self.assertEqual(json.loads(decode_b64u(self.read("body")))["type"], "authenticated")
        self.exchange("wifi pa/ss\\word")
        self.assertEqual(json.loads(decode_b64u(self.read("body")))["type"], "wifi_result")
        self.assertEqual(self.wifi, [("Cafe/Shop", "pa/ss\\word")])
        challenge = {"claim_id": str(uuid.uuid4()), "machine_id": self.machine_id, "user_id": str(uuid.uuid4()),
                     "purpose": "claim_owner", "nonce": b64u(b"n" * 32), "expires_at": 1_800_000_000_000}
        signature = machine_identity.Identity("0" * 16, self.server_key, b"", "").sign(challenge_bytes(challenge))
        self.exchange("claim " + b64u(json_bytes({"challenge": challenge, "signature": b64u(signature)})))
        proof = json.loads(decode_b64u(self.read("body")))
        self.assertEqual(proof["type"], "claim_proof")
        self.assertTrue(verify_raw(self.identity.public_key, accept_bytes(challenge, proof["local_session_binding"]),
                                   decode_b64u(proof["machine_proof"])))
        self.send("end")

    def test_wrong_seal_fails_closed(self):
        self.start(b"z" * 32)
        self.send("probe x")
        request = decode_b64u(self.read("request"))
        with self.assertRaises(SessionClosed) as closed:
            self.machine.handle(request)
        self.assertIsNone(closed.exception.response)

    def test_cloud_aad_matches_server_bytes(self):
        self.start(self.seal)
        self.send("aad x")
        self.assertEqual(decode_b64u(self.read("aad")), json_bytes([1, "/app/user/session/login", "POST", "server", "server-hpke-1", "x", 0, None]))


if __name__ == "__main__":
    unittest.main()
