"""QR Payload Protocol v1.4, local deployment: encrypted, TS+MID bound,
two opcode types (TYPE_WEIGHT and TYPE_BOOLEAN -- no percentage; see
constants.py for why).

Typical usage:

    from qrproto import create, verify, Instruction, Grams
    from qrproto.keys import load_key_from_env

    key = load_key_from_env("QRPROTO_KEY")

    payload = create(
        sku=42,
        instructions=[Instruction(7, Grams(13)), Instruction(12, True)],
        machine_id=123,
        key=key,
    )

    result = verify(payload, key, machine_id=123)
    # result["instructions"], result["sku"], ...

Everything else (constants, crc, inner, envelope, qr, keys) is
reachable as a submodule for tests, diagnostics, or label-printing
tooling that needs more than create()/verify() expose.
"""

from .api import create, verify
from .errors import (
    ChecksumError,
    ClockSkewError,
    CryptoError,
    ExpiredError,
    FormatError,
    MachineMismatchError,
    ProtocolError,
)
from .inner import Grams, Instruction

__all__ = [
    "create",
    "verify",
    "Instruction",
    "Grams",
    "ProtocolError",
    "FormatError",
    "ChecksumError",
    "CryptoError",
    "MachineMismatchError",
    "ExpiredError",
    "ClockSkewError",
]
