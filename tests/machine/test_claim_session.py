"""BLE claim v2 session: success paths and every tamper case must fail before Wi-Fi or signing."""
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "version1.1"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from bt_app_peer import AppPeer
from machine.config import identity as machine_identity
from machine.config.identity import b64u, decode_b64u, json_bytes
from machine.pairing.claim_crypto import accept_bytes, challenge_bytes, verify_raw
from machine.pairing.claim_session import ClaimSession, SessionClosed, parse_object


def server_signature(key, challenge):
    return b64u(machine_identity.Identity("0" * 16, key, b"", "").sign(challenge_bytes(challenge)))


class ClaimSessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.identity = machine_identity.provision(self.tmp.name, "00000000abcdef01")
        self.seal = machine_identity.load_seal_code(self.tmp.name)
        self.server_key = ec.generate_private_key(ec.SECP256R1())
        self.server_public = self.server_key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        self.wifi_calls = []
        self.machine_id = str(uuid.uuid4())
        self.online = False
        self.clock = [0.0]

    def tearDown(self):
        self.tmp.cleanup()

    def session(self):
        def wifi(ssid, password):
            self.wifi_calls.append((ssid, password))
            self.online = True
            return {"ok": ssid != "bad"}
        return ClaimSession(self.identity, self.seal, self.server_public, wifi,
                            lambda: (self.machine_id, self.online), clock=lambda: self.clock[0])

    def start(self, seal=None):
        machine = self.session()
        app = AppPeer(self.identity.serial, seal or self.seal)
        app.accept_hello(machine.hello_packet)
        return machine, app

    def probe(self, machine, app):
        return app.response(machine.handle(app.request("probe")))

    def challenge(self):
        challenge = {"claim_id": str(uuid.uuid4()), "machine_id": self.machine_id, "user_id": str(uuid.uuid4()),
                     "purpose": "claim_owner", "nonce": b64u(b"n" * 32), "expires_at": 1_800_000_000_000}
        return challenge, server_signature(self.server_key, challenge)

    def claim(self, machine, app, transcript=None, challenge=None, signature=None):
        if challenge is None:
            challenge, signature = self.challenge()
        packet = app.request("claim", {"session_transcript": transcript or app.transcript_hash,
                                       "challenge": challenge, "server_challenge_signature": signature})
        with self.assertRaises(SessionClosed) as closed:
            machine.handle(packet)
        return challenge, app.response(closed.exception.response)

    def test_wifi_then_claim(self):
        machine, app = self.start()
        q1 = self.probe(machine, app)
        self.assertEqual(q1["type"], "authenticated")
        self.assertEqual(decode_b64u(q1["machine_public_key"]), self.identity.public_key)
        h1 = app.transcript_hash
        q2 = app.response(machine.handle(app.request("wifi", {"session_transcript": h1, "ssid": "Cafe", "password": "secret-pass"})))
        self.assertEqual((q2["type"], q2["ok"], q2["online"]), ("wifi_result", True, True))
        self.assertEqual(self.wifi_calls, [("Cafe", "secret-pass")])
        challenge, q3 = self.claim(machine, app)
        self.assertEqual(q3["type"], "claim_proof")
        self.assertEqual(q3["local_session_binding"], machine.session_id)
        self.assertTrue(verify_raw(self.identity.public_key, accept_bytes(challenge, q3["local_session_binding"]),
                                   decode_b64u(q3["machine_proof"])))
        self.assertTrue(machine.closed)

    def test_claim_without_wifi_uses_h1(self):
        machine, app = self.start()
        self.online = True
        self.assertTrue(self.probe(machine, app)["online"])
        _, q = self.claim(machine, app)
        self.assertEqual(q["type"], "claim_proof")
        self.assertEqual(self.wifi_calls, [])

    def test_wrong_seal_closes_silently(self):
        machine, app = self.start(seal=b"x" * 32)
        with self.assertRaises(SessionClosed) as closed:
            machine.handle(app.request("probe"))
        self.assertIsNone(closed.exception.response)
        self.assertTrue(machine.closed)

    def test_stale_transcript_is_refused_before_wifi(self):
        machine, app = self.start()
        self.probe(machine, app)
        with self.assertRaises(SessionClosed) as closed:
            machine.handle(app.request("wifi", {"session_transcript": app.h0, "ssid": "Cafe", "password": "p"}))
        self.assertEqual(app.response(closed.exception.response)["code"], "PAIRING_PROTOCOL_ERROR")
        self.assertEqual(self.wifi_calls, [])

    def test_claim_with_h1_after_wifi_is_refused(self):
        machine, app = self.start()
        self.probe(machine, app)
        h1 = app.transcript_hash
        app.response(machine.handle(app.request("wifi", {"session_transcript": h1, "ssid": "Cafe", "password": "p"})))
        _, q = self.claim(machine, app, transcript=h1)
        self.assertEqual(q["code"], "PAIRING_PROTOCOL_ERROR")

    def test_replayed_request_and_wrong_stage(self):
        machine, app = self.start()
        probe = app.request("probe")
        machine.handle(probe)
        with self.assertRaises(SessionClosed) as closed:
            machine.handle(probe)
        self.assertIsNone(closed.exception.response)
        machine, app = self.start()
        with self.assertRaises(SessionClosed):
            machine.handle(app.request("claim", {"session_transcript": app.h0}))

    def test_request_from_other_session_fails(self):
        first, app = self.start()
        packet = app.request("probe")
        second = self.session()
        with self.assertRaises(SessionClosed):
            second.handle(packet)

    def test_tampered_ciphertext_fails(self):
        machine, app = self.start()
        packet = parse_object(app.request("probe"))
        ct = bytearray(decode_b64u(packet["ct"])); ct[0] ^= 1
        packet["ct"] = b64u(bytes(ct))
        with self.assertRaises(SessionClosed) as closed:
            machine.handle(json_bytes(packet))
        self.assertIsNone(closed.exception.response)

    def test_bad_server_signature_or_other_machine(self):
        machine, app = self.start()
        self.probe(machine, app)
        challenge, signature = self.challenge()
        forged = server_signature(ec.generate_private_key(ec.SECP256R1()), challenge)
        _, q = self.claim(machine, app, challenge=challenge, signature=forged)
        self.assertEqual(q["code"], "CLAIM_INVALID")
        machine, app = self.start()
        self.probe(machine, app)
        challenge = {**self.challenge()[0], "machine_id": str(uuid.uuid4())}
        _, q = self.claim(machine, app, challenge=challenge, signature=server_signature(self.server_key, challenge))
        self.assertEqual(q["code"], "CLAIM_INVALID")

    def test_wifi_failure_is_terminal(self):
        machine, app = self.start()
        self.probe(machine, app)
        with self.assertRaises(SessionClosed) as closed:
            machine.handle(app.request("wifi", {"session_transcript": app.transcript_hash, "ssid": "bad", "password": "p"}))
        self.assertEqual(app.response(closed.exception.response)["code"], "WIFI_FAILED")

    def test_idle_timeout(self):
        machine, app = self.start()
        self.clock[0] = 121
        with self.assertRaises(SessionClosed):
            machine.handle(app.request("probe"))

    def test_serial_mismatch_rejected_by_app(self):
        machine = self.session()
        with self.assertRaises(ValueError):
            AppPeer("ffffffffffffffff", self.seal).accept_hello(machine.hello_packet)


if __name__ == "__main__":
    unittest.main()
