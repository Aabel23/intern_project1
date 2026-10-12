"""Reference app side of the BLE claim v2 session (mirrors the Kotlin implementation); test only."""
import json
import os
import uuid

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from machine.config.identity import b64u, decode_b64u, json_bytes
from machine.pairing.claim_session import (PV, RESPONSE_LABEL, context_info, frame, parse_object, psk_id,
                                           request_aad, response_aad, sha_b64u, suite)


class AppPeer:
    def __init__(self, qr_serial, seal):
        self.serial, self.seal = qr_serial, seal
        self.client_nonce = b64u(os.urandom(32))
        self.transcript = b""

    def accept_hello(self, packet):
        hello = parse_object(packet)
        assert set(hello) == {"pv", "type", "serial", "session_id", "machine_nonce", "public_key", "machine_public_key"}
        assert hello["pv"] == PV and hello["type"] == "hello"
        if hello["serial"] != self.serial:
            raise ValueError("serial mismatch with QR")
        self.hello = hello
        self.session_id, self.machine_nonce = hello["session_id"], hello["machine_nonce"]
        self.machine_key = suite().kem.deserialize_public_key(decode_b64u(hello["public_key"]))
        self.transcript = frame(packet)
        self.h0 = sha_b64u(self.transcript)

    def common(self, kind):
        return {"type": kind, "serial": self.serial, "session_id": self.session_id,
                "machine_nonce": self.machine_nonce, "client_nonce": self.client_nonce}

    def request(self, stage, extra=None, *, seal=None, send_id=None):
        send_id = send_id or str(uuid.uuid4())
        hpke = suite()
        enc, sender = hpke.create_sender_context(self.machine_key, info=context_info(self.serial, self.session_id, self.h0),
                                                 psk=seal or self.seal, psk_id=psk_id(self.serial))
        plain = json_bytes({**self.common(stage), **(extra or {})})
        ct = sender.seal(plain, aad=request_aad(self.serial, self.session_id, self.h0, send_id, stage))
        packet = json_bytes({"pv": PV, "type": "request", "session_id": self.session_id, "send_id": send_id,
                             "stage": stage, "enc": b64u(enc), "ct": b64u(ct)})
        self.pending = (packet, stage, send_id, sender.export(RESPONSE_LABEL.encode("ascii"), 16))
        return packet

    def response(self, packet):
        request_packet, stage, send_id, key = self.pending
        outer = parse_object(packet)
        assert set(outer) == {"pv", "type", "session_id", "send_id", "stage", "nonce", "ct"}
        assert outer["send_id"] == send_id and outer["stage"] == stage and outer["session_id"] == self.session_id
        plain = AESGCM(key).decrypt(decode_b64u(outer["nonce"]), decode_b64u(outer["ct"]),
                                    response_aad(self.serial, self.session_id, self.h0, send_id, stage, request_packet))
        body = json.loads(plain)
        for name, value in self.common(body["type"]).items():
            assert body[name] == value, name
        if body["type"] in ("authenticated", "wifi_result"):
            self.transcript += frame(request_packet) + frame(packet)
        return body

    @property
    def transcript_hash(self):
        return sha_b64u(self.transcript)
