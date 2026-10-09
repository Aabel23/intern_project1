"""The outer layer: BCD packing, AES-256-GCM sealing, and the decimal
rendering that lets an encrypted envelope travel inside a Numeric-mode
QR symbol.

    OUTER (printed): <VER:2><ENVELOPE:variable><OCRC:5>
    ENVELOPE       : decimal rendering of nonce(12B) || ciphertext || tag(16B)

`validate_outer_structure_and_crc` is the single choke point for
stages 1-2 (spec section 8.1-8.2) -- both `decrypt_payload` and
`qr.make_qr` route through it, so the envelope-value bound (spec
section 4.3) is enforced in exactly one place.
"""

import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import constants as C
from .crc import compute_crc
from .errors import ChecksumError, CryptoError, FormatError

from flexmix_debug import trace          # noqa: E402


def _generate_nonce() -> bytes:
    """Fresh random 12-byte nonce. Factored out (rather than calling
    os.urandom inline) so tests can monkeypatch this function to inject
    a fixed nonce for deterministic test vectors."""
    return os.urandom(C.NONCE_BYTES)


# --- BCD packing (spec section 4.2) ----------------------------------
def bcd_pack(digits: str) -> bytes:
    """Two digits per byte, big-endian digit order (earlier digit in
    the high nibble). The inner digit string is always odd length, so
    the final byte gets a 0xF pad nibble in its low half."""
    nibbles = [ord(c) - ord("0") for c in digits]
    if len(nibbles) % 2 == 1:
        nibbles.append(0xF)

    out = bytearray()
    for i in range(0, len(nibbles), 2):
        out.append((nibbles[i] << 4) | nibbles[i + 1])
    return bytes(out)


def bcd_unpack(data: bytes) -> str:
    """Inverse of bcd_pack. Strips a trailing 0xF pad nibble; any other
    value in the pad position, or any non-BCD (0xA-0xF) nibble
    elsewhere, is a FormatError."""
    nibbles = []
    for b in data:
        nibbles.append((b >> 4) & 0xF)
        nibbles.append(b & 0xF)

    if not nibbles:
        raise FormatError("stage 4 (inner structure): BCD unpack: empty plaintext")

    if nibbles[-1] != 0xF:
        raise FormatError(
            f"stage 4 (inner structure): BCD unpack: pad nibble is "
            f"0x{nibbles[-1]:X}, expected 0xF"
        )
    nibbles = nibbles[:-1]

    for v in nibbles:
        if not 0 <= v <= 9:
            raise FormatError(
                f"stage 4 (inner structure): BCD unpack: invalid digit nibble 0x{v:X}"
            )

    return "".join(str(v) for v in nibbles)


# --- decimal rendering of the envelope (spec section 4.3) -------------
def render_envelope(envelope_bytes: bytes) -> str:
    entry = C.B_TO_ENTRY.get(len(envelope_bytes))
    width = entry["D"] if entry is not None else C._decimal_width(len(envelope_bytes))
    value = int.from_bytes(envelope_bytes, "big")
    return str(value).zfill(width)


def parse_envelope(envelope_digits: str, byte_len: int) -> bytes:
    value = int(envelope_digits)
    return value.to_bytes(byte_len, "big")


# --- stages 1-2: outer structure + OCRC --------------------------------
@trace
def validate_outer_structure_and_crc(payload: str):
    """Stages 1 and 2 only. Returns (ver, envelope_digits, table_entry)."""
    if not C.is_digits_only(payload):
        raise FormatError("stage 1 (outer structure): payload must be digits only")

    entry = C.OUTER_LEN_TO_ENTRY.get(len(payload))
    if entry is None:
        raise FormatError(
            f"stage 1 (outer structure): length {len(payload)} is not in "
            f"the valid outer-length table"
        )

    ver = payload[:C.VER_DIGITS]
    envelope_digits = payload[C.VER_DIGITS:C.VER_DIGITS + entry["D"]]
    ocrc = payload[C.VER_DIGITS + entry["D"]:]

    if ver != C.VER:
        raise FormatError(f"stage 1 (outer structure): VER {ver!r} != {C.VER!r}")

    # D was sized as the *minimum* digit count that can hold any B-byte
    # value, so a D-digit decimal field can represent values up to
    # 10**D - 1, which is often >= 256**B. Stages 1-2 need no key (OCRC
    # is publicly computable), so a same-length, correctly-checksummed
    # payload can be hand-crafted with an envelope value too big to
    # convert back to B bytes. Checked here, before any crypto work, so
    # every caller is covered by this one choke point instead of
    # hitting a raw OverflowError deeper in int.to_bytes().
    if int(envelope_digits) >= 256 ** entry["B"]:
        raise FormatError(
            f"stage 1 (outer structure): envelope value exceeds {entry['B']} bytes"
        )

    expected_ocrc = compute_crc(ver + envelope_digits)
    if ocrc != expected_ocrc:
        raise ChecksumError(f"stage 2 (outer CRC): got {ocrc}, expected {expected_ocrc}")

    return ver, envelope_digits, entry


# --- encrypt / decrypt ---------------------------------------------------
@trace
def encrypt_payload(inner_digits: str, key: bytes) -> str:
    """VER + envelope + OCRC, built from an already-encoded inner digit
    string (see inner.encode_inner)."""
    if not C.is_digits_only(inner_digits):
        raise FormatError("encrypt_payload: inner_digits must be digits only")

    if len(inner_digits) not in C.INNER_LEN_TO_N:
        raise FormatError(
            f"encrypt_payload: inner length {len(inner_digits)} is not a valid "
            f"inner payload length"
        )

    plaintext = bcd_pack(inner_digits)
    nonce = _generate_nonce()
    ct_and_tag = AESGCM(key).encrypt(nonce, plaintext, C.AAD)
    envelope_bytes = nonce + ct_and_tag

    envelope_digits = render_envelope(envelope_bytes)
    body = C.VER + envelope_digits
    return body + compute_crc(body)


@trace
def decrypt_payload(outer_digits: str, key: bytes) -> str:
    """Stages 1, 2, 3 -> inner digit string."""
    ver, envelope_digits, entry = validate_outer_structure_and_crc(outer_digits)

    envelope_bytes = parse_envelope(envelope_digits, entry["B"])
    nonce = envelope_bytes[:C.NONCE_BYTES]
    ct_and_tag = envelope_bytes[C.NONCE_BYTES:]

    try:
        plaintext = AESGCM(key).decrypt(nonce, ct_and_tag, C.AAD)
    except InvalidTag as exc:
        raise CryptoError(
            "stage 3 (decrypt): AES-GCM authentication tag verification "
            "failed (forged payload, wrong key, or corrupt data)"
        ) from exc

    return bcd_unpack(plaintext)
