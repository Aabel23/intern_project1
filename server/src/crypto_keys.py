"""Load only Operator-provisioned private keys and verify pinned public bytes."""
import base64
from dataclasses import dataclass, field
import json
from pathlib import Path
import stat
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, x25519
from server.src.types import Settings


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')


def decode_b64u(value: str) -> bytes:
    if not isinstance(value, str):
        raise ValueError()
    raw = base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))
    if b64u(raw) != value:
        raise ValueError()
    return raw


@dataclass(frozen=True)
class ServerKeys:
    hpke_private: x25519.X25519PrivateKey = field(repr=False)
    signing_private: ec.EllipticCurvePrivateKey = field(repr=False)
    public_pins: dict


def load_server_keys(settings: Settings) -> ServerKeys:
    try:
        def private(path):
            path = Path(path)
            if not path.is_absolute() or stat.S_IMODE(path.stat().st_mode) != 0o600:
                raise ValueError()
            data = path.read_bytes()
            if not data.startswith(b'-----BEGIN PRIVATE KEY-----'):
                raise ValueError()
            return serialization.load_pem_private_key(data, password=None)
        hpke = private(settings.server_hpke_key_file)
        signing = private(settings.server_signing_key_file)
        if not isinstance(hpke, x25519.X25519PrivateKey):
            raise ValueError()
        if not isinstance(signing, ec.EllipticCurvePrivateKey) or not isinstance(signing.curve, ec.SECP256R1):
            raise ValueError()
        pins = json.loads(Path(settings.server_trust_file).read_text())
        if not isinstance(pins, dict) or set(pins) != {'v','hpke','signing'} or type(pins['v']) is not int or pins['v'] != 1:
            raise ValueError()
        expected = {
            'hpke': ('server-hpke-1', hpke.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)),
            'signing': ('server-sign-1', signing.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)),
        }
        for name, (kid, public) in expected.items():
            item = pins[name]
            if not isinstance(item, dict) or set(item) != {'kid','public_key'} or item['kid'] != kid or decode_b64u(item['public_key']) != public:
                raise ValueError()
        return ServerKeys(hpke, signing, pins)
    except (ValueError, TypeError, KeyError, OSError):
        raise ValueError('CONFIG_INVALID') from None
