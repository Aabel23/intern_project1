"""Phiên BLE nhận máy v2 phía máy (bt-claim.md + v2-decisions.md D3/D4).

Lõi giao thức không đụng radio: nhận/trả đúng byte của gói JSON logic (P), transport lo
khung F(P)=u32be(len)||P và phân mảnh GATT. Mọi lỗi trước khi mở được probe thì đóng im
lặng; sau đó trả lỗi đã mã hóa rồi đóng.

    hello H ─► R1 probe ─► Q1 authenticated          h1 = H(F(H)‖F(R1)‖F(Q1))
              R2 wifi{h1} (tùy chọn) ─► Q2 wifi_result  h2 = H(…‖F(R2)‖F(Q2))
              R3 claim{h1|h2} ─► Q3 claim_proof ─► đóng
"""

import hashlib
import json
import os
import struct
import threading
import time
import uuid

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pyhpke import AEADId, CipherSuite, KDFId, KEMId

from machine.config.identity import b64u, decode_b64u, json_bytes

PV = 2
CLAIM_LABEL = "flexmix-bt-claim-v2"
RESPONSE_LABEL = "flexmix-bt-response-v2"
MAX_PACKET = 8192
IDLE_SECONDS = 120
ABSOLUTE_SECONDS = 600
SEND_ID_CACHE = 3
ERROR_CODES = {"PAIRING_PROTOCOL_ERROR", "PAIRING_EXPIRED", "WIFI_FAILED", "SERVER_UNAVAILABLE",
               "CLAIM_INVALID", "CLAIM_EXPIRED", "ALREADY_OWNED"}


class SessionClosed(Exception):
    """Phiên kết thúc; `response` là gói cuối cần gửi (None nếu đóng im lặng)."""

    def __init__(self, response=None):
        super().__init__("closed")
        self.response = response


def frame(packet):
    return struct.pack(">I", len(packet)) + packet


def sha_b64u(data):
    return b64u(hashlib.sha256(data).digest())


def parse_object(raw):
    """JSON object chặt: không key trùng, không NaN/Infinity, UTF-8 hợp lệ."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate")
            result[key] = value
        return result

    def constant(_):
        raise ValueError("constant")

    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(value, dict):
        raise ValueError("object")
    return value


def suite():
    return CipherSuite.new(KEMId.DHKEM_X25519_HKDF_SHA256, KDFId.HKDF_SHA256, AEADId.AES128_GCM)


def psk_id(serial):
    return ("flexmix-seal-v1:" + serial).encode("ascii")


def context_info(serial, session_id, h0):
    return json_bytes([CLAIM_LABEL, "app", "machine", serial, session_id, h0])


def request_aad(serial, session_id, h0, send_id, stage):
    return json_bytes([PV, CLAIM_LABEL, "app", "machine", serial, session_id, h0, send_id, stage])


def response_aad(serial, session_id, h0, send_id, stage, request_packet):
    return json_bytes([PV, RESPONSE_LABEL, "machine", "app", serial, session_id, h0, send_id, stage,
                       sha_b64u(frame(request_packet))])


def _uuid4(value):
    if not isinstance(value, str):
        raise ValueError("uuid")
    parsed = uuid.UUID(value)
    if parsed.version != 4 or str(parsed) != value:
        raise ValueError("uuid")
    return value


class ClaimSession:
    """Một kết nối BLE = một phiên. Không tái dùng, không lưu gì ra đĩa.

    wifi(ssid, password) -> {"ok": bool, "online": bool} và machine_info() -> (machine_id|None, online)
    do lớp ngoài cấp; server_signing_key là khóa ghim để kiểm challenge claim.
    """

    def __init__(self, identity, seal, server_signing_key, wifi, machine_info, clock=time.monotonic):
        self.identity, self.seal = identity, seal
        self.server_signing_key = server_signing_key
        self.wifi, self.machine_info, self.clock = wifi, machine_info, clock
        self.lock = threading.Lock()
        self.serial = identity.serial
        self.session_id = str(uuid.uuid4())
        self.machine_nonce = b64u(os.urandom(32))
        self.client_nonce = None
        self.suite = suite()
        self.recipient = self.suite.kem.derive_key_pair(os.urandom(32))
        self.started = self.last = clock()
        self.state = "HELLO_SENT"
        self.seen = []
        self.transcript = b""
        self.authenticated = False
        self.closed = False
        public = self.recipient.public_key.to_public_bytes()
        self.hello_packet = json_bytes({"pv": PV, "type": "hello", "serial": self.serial, "session_id": self.session_id,
                                        "machine_nonce": self.machine_nonce, "public_key": b64u(public),
                                        "machine_public_key": b64u(identity.public_key)})
        self.transcript = frame(self.hello_packet)
        self.h0 = sha_b64u(self.transcript)

    # ------------------------------------------------------------ public API

    def handle(self, packet):
        """Trả gói phản hồi; ném SessionClosed khi phiên phải đóng (kèm gói cuối nếu có)."""
        with self.lock:
            if self.closed:
                raise SessionClosed()
            now = self.clock()
            if now - self.last > IDLE_SECONDS or now - self.started > ABSOLUTE_SECONDS:
                self._close()
                raise SessionClosed(None)
            try:
                request, stage, send_id, plain = self._open(packet)
            except Exception:
                self._close()
                raise SessionClosed(None) from None
            self.last = now
            try:
                body, final = self._dispatch(stage, plain)
            except _Refuse as refuse:
                body, final = {**self._common("error"), "code": refuse.code}, True
            response = self._seal_response(packet, stage, send_id, body)
            if stage in ("probe", "wifi") and not final:
                self.transcript += frame(packet) + frame(response)
            if final:
                self._close()
                raise SessionClosed(response)
            return response

    def close(self):
        with self.lock:
            self._close()

    # ------------------------------------------------------------ internals

    def _close(self):
        self.closed = True
        self.seal = b"\x00" * 32
        self.recipient = None
        self._context = None

    def _open(self, packet):
        if not 0 < len(packet) <= MAX_PACKET:
            raise ValueError("size")
        request = parse_object(packet)
        if set(request) != {"pv", "type", "session_id", "send_id", "stage", "enc", "ct"}:
            raise ValueError("fields")
        if request["pv"] != PV or request["type"] != "request" or request["session_id"] != self.session_id:
            raise ValueError("header")
        stage, send_id = request["stage"], _uuid4(request["send_id"])
        expected = {"HELLO_SENT": ("probe",), "AUTHENTICATED": ("wifi", "claim"), "WIFI_DONE": ("claim",)}
        if stage not in expected.get(self.state, ()):
            raise ValueError("stage")
        if send_id in self.seen or len(self.seen) >= SEND_ID_CACHE:
            raise ValueError("replay")
        enc, ct = decode_b64u(request["enc"]), decode_b64u(request["ct"])
        if len(enc) != 32 or len(ct) < 16:
            raise ValueError("lengths")
        context = self.suite.create_recipient_context(
            enc, self.recipient.private_key, info=context_info(self.serial, self.session_id, self.h0),
            psk=self.seal, psk_id=psk_id(self.serial))
        plain = parse_object(context.open(ct, aad=request_aad(self.serial, self.session_id, self.h0, send_id, stage)))
        # Một context chỉ mở một request và chỉ export một khóa phản hồi.
        self._response_key = context.export(RESPONSE_LABEL.encode("ascii"), 16)
        self.seen.append(send_id)
        common = {"serial": self.serial, "session_id": self.session_id, "machine_nonce": self.machine_nonce}
        for key, value in common.items():
            if plain.get(key) != value:
                raise ValueError("common")
        if stage == "probe":
            nonce = decode_b64u(plain.get("client_nonce"))
            if len(nonce) != 32:
                raise ValueError("nonce")
            self.client_nonce = plain["client_nonce"]
        elif plain.get("client_nonce") != self.client_nonce:
            raise ValueError("nonce")
        if plain.get("type") != stage:
            raise ValueError("type")
        return request, stage, send_id, plain

    def _common(self, kind):
        return {"type": kind, "serial": self.serial, "session_id": self.session_id,
                "machine_nonce": self.machine_nonce, "client_nonce": self.client_nonce}

    def _transcript_hash(self):
        return sha_b64u(self.transcript)

    def _dispatch(self, stage, plain):
        if stage == "probe":
            if set(plain) != {"type", "serial", "session_id", "machine_nonce", "client_nonce"}:
                raise _Refuse("PAIRING_PROTOCOL_ERROR")
            self.state = "AUTHENTICATED"
            machine_id, online = self.machine_info()
            return {**self._common("authenticated"), "machine_public_key": b64u(self.identity.public_key),
                    "machine_id": machine_id, "online": online}, False
        expected_transcript = self._transcript_hash()
        if plain.get("session_transcript") != expected_transcript:
            raise _Refuse("PAIRING_PROTOCOL_ERROR")
        if stage == "wifi":
            if set(plain) != {"type", "serial", "session_id", "machine_nonce", "client_nonce",
                              "session_transcript", "ssid", "password"}:
                raise _Refuse("PAIRING_PROTOCOL_ERROR")
            ssid, password = plain["ssid"], plain["password"]
            if (not isinstance(ssid, str) or not 1 <= len(ssid.encode("utf-8")) <= 32
                    or not isinstance(password, str) or len(password) > 63):
                raise _Refuse("PAIRING_PROTOCOL_ERROR")
            outcome = self.wifi(ssid, password)
            if not outcome.get("ok"):
                raise _Refuse("WIFI_FAILED")
            self.state = "WIFI_DONE"
            machine_id, online = self.machine_info()
            return {**self._common("wifi_result"), "session_transcript": expected_transcript, "ok": True,
                    "machine_id": machine_id, "online": online}, False
        # claim
        if set(plain) != {"type", "serial", "session_id", "machine_nonce", "client_nonce",
                          "session_transcript", "challenge", "server_challenge_signature"}:
            raise _Refuse("PAIRING_PROTOCOL_ERROR")
        return self._claim(plain["challenge"], plain["server_challenge_signature"]), True

    def _claim(self, challenge, signature):
        from machine.pairing.claim_crypto import accept_bytes, challenge_bytes, verify_raw
        fields = {"claim_id", "machine_id", "user_id", "purpose", "nonce", "expires_at"}
        if not isinstance(challenge, dict) or set(challenge) != fields or challenge["purpose"] != "claim_owner":
            raise _Refuse("CLAIM_INVALID")
        try:
            _uuid4(challenge["claim_id"]); _uuid4(challenge["machine_id"]); _uuid4(challenge["user_id"])
            if len(decode_b64u(challenge["nonce"])) != 32 or type(challenge["expires_at"]) is not int:
                raise ValueError()
            signature_bytes = decode_b64u(signature)
        except (ValueError, TypeError):
            raise _Refuse("CLAIM_INVALID") from None
        if not verify_raw(self.server_signing_key, challenge_bytes(challenge), signature_bytes):
            raise _Refuse("CLAIM_INVALID")
        machine_id, _ = self.machine_info()
        if machine_id is not None and machine_id != challenge["machine_id"]:
            raise _Refuse("CLAIM_INVALID")
        proof = self.identity.sign(accept_bytes(challenge, self.session_id))
        return {**self._common("claim_proof"), "claim_id": challenge["claim_id"],
                "local_session_binding": self.session_id, "machine_proof": b64u(proof)}

    def _seal_response(self, request_packet, stage, send_id, body):
        nonce = os.urandom(12)
        aad = response_aad(self.serial, self.session_id, self.h0, send_id, stage, request_packet)
        ct = AESGCM(self._response_key).encrypt(nonce, json_bytes(body), aad)
        self._response_key = None
        return json_bytes({"pv": PV, "type": "response", "session_id": self.session_id, "send_id": send_id,
                           "stage": stage, "nonce": b64u(nonce), "ct": b64u(ct)})


class _Refuse(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code
