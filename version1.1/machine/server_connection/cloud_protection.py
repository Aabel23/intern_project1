"""Phong bì HPKE + chữ ký máy cho mọi request lên server (cloud-protection.md, v2 D1).

Request: HPKE mode_base tới khóa server đã ghim; AAD ràng route/send_id/thời điểm/key_id;
máy ký J(["flexmix-machine-envelope-v1", b64u(AAD), enc, ct]). Phản hồi: AES-GCM bằng khóa
export một lần từ chính context của request, nên chỉ máy gửi request mở được.
"""

from dataclasses import dataclass, field
import json
import uuid

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pyhpke import AEADId, CipherSuite, KDFId, KEMId

from machine.config.identity import b64u, decode_b64u, json_bytes

INFO = b"flexmix-cloud-v1"
RESPONSE_LABEL = b"flexmix-response-v1"
PUBLIC_ERRORS = {"INVALID_ENVELOPE", "UNSUPPORTED_VERSION", "UNKNOWN_KEY", "RATE_LIMITED", "SERVICE_UNAVAILABLE"}


class CloudError(Exception):
    def __init__(self, code, status=None):
        super().__init__(code)
        self.code = code
        self.status = status


@dataclass
class SealedRequest:
    envelope: dict
    send_id: str
    route: str
    response_key: bytes = field(repr=False)


def _suite():
    return CipherSuite.new(KEMId.DHKEM_X25519_HKDF_SHA256, KDFId.HKDF_SHA256, AEADId.AES128_GCM)


def seal_request(route, body, sent_at_ms, identity, trust):
    pin = trust["hpke"]
    send_id = str(uuid.uuid4())
    aad = json_bytes([1, route, "POST", "server", pin["kid"], send_id, sent_at_ms, identity.key_id])
    suite = _suite()
    server_key = suite.kem.deserialize_public_key(decode_b64u(pin["public_key"]))
    enc, sender = suite.create_sender_context(server_key, info=INFO)
    ciphertext = sender.seal(json_bytes({"auth": None, "body": body}), aad=aad)
    enc_text, ct_text = b64u(enc), b64u(ciphertext)
    signature = identity.sign(json_bytes(["flexmix-machine-envelope-v1", b64u(aad), enc_text, ct_text]))
    envelope = {"pv": 1, "route": route, "method": "POST", "receiver": "server", "kid": pin["kid"],
                "send_id": send_id, "sent_at_ms": sent_at_ms, "machine_key_id": identity.key_id,
                "enc": enc_text, "ct": ct_text, "sig": b64u(signature)}
    return SealedRequest(envelope, send_id, route, sender.export(RESPONSE_LABEL, 16))


def open_response(sealed, http_status, outer):
    """Trả data khi ok; lỗi nghiệp vụ hay lỗi phong bì công khai đều thành CloudError."""
    try:
        if not isinstance(outer, dict):
            raise CloudError("INVALID_RESPONSE")
        if "error" in outer:
            error = outer.get("error")
            code = error.get("code") if isinstance(error, dict) else None
            if set(outer) != {"pv", "error"} or code not in PUBLIC_ERRORS:
                raise CloudError("INVALID_RESPONSE")
            raise CloudError(code, http_status)
        if set(outer) != {"pv", "send_id", "status", "nonce", "ct"} or outer["pv"] != 1:
            raise CloudError("INVALID_RESPONSE")
        if outer["send_id"] != sealed.send_id or outer["status"] != http_status:
            raise CloudError("INVALID_RESPONSE")
        aad = json_bytes(["flexmix-response-v1", sealed.send_id, http_status, sealed.route])
        try:
            plain = AESGCM(sealed.response_key).decrypt(decode_b64u(outer["nonce"]), decode_b64u(outer["ct"]), aad)
        except Exception:
            raise CloudError("INVALID_RESPONSE") from None
        value = json.loads(plain)
        if not isinstance(value, dict) or value.get("v") != 1 or type(value.get("ok")) is not bool:
            raise CloudError("INVALID_RESPONSE")
        if value["ok"]:
            if http_status != 200 or not isinstance(value.get("data"), dict):
                raise CloudError("INVALID_RESPONSE")
            return value["data"]
        error = value.get("error")
        if not isinstance(error, dict) or not isinstance(error.get("code"), str):
            raise CloudError("INVALID_RESPONSE")
        raise CloudError(error["code"], http_status)
    finally:
        # Khóa phản hồi chỉ dùng một lần.
        sealed.response_key = b"\x00" * 16
