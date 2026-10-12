"""Byte chuẩn của challenge claim và chữ ký, khớp server/src/devices.py (hợp đồng v2)."""

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

from machine.config.identity import P256_ORDER, b64u, json_bytes


def challenge_bytes(challenge):
    return json_bytes(["flexmix-claim-v1", challenge["claim_id"], challenge["machine_id"], challenge["user_id"],
                       challenge["purpose"], challenge["nonce"], challenge["expires_at"]])


def accept_bytes(challenge, local_session_binding):
    return json_bytes(["flexmix-claim-accept-v1", b64u(challenge_bytes(challenge)), local_session_binding])


def verify_raw(public_key, message, signature):
    """Kiểm chữ ký raw r||s low-s bằng khóa server đã ghim (SEC1 65 byte)."""
    if len(signature) != 64 or len(public_key) != 65 or public_key[0] != 4:
        return False
    r, s = int.from_bytes(signature[:32], "big"), int.from_bytes(signature[32:], "big")
    if not 0 < r < P256_ORDER or not 0 < s <= P256_ORDER // 2:
        return False
    try:
        key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), public_key)
        key.verify(encode_dss_signature(r, s), message, ec.ECDSA(hashes.SHA256()))
        return True
    except (ValueError, InvalidSignature):
        return False
