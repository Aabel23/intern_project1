"""Key generation and loading. The API deals only in raw 32-byte keys --
no password-based derivation, since this protocol has no interactive
user to prompt and a human-memorable password has far less entropy
than 256 bits. Keys are machine-provisioned secrets.
"""

import os
from pathlib import Path

from . import constants as C

_HEX_CHARS = set("0123456789abcdefABCDEF")


def generate_key() -> bytes:
    """A fresh random 32-byte AES-256 key."""
    return os.urandom(C.KEY_BYTES)


def load_key_from_env(name: str) -> bytes:
    """Read a hex-encoded 32-byte key from environment variable `name`.
    Environments are text, so the key is carried hex-encoded (64 chars)."""
    value = os.environ.get(name)
    if value is None:
        raise KeyError(f"environment variable {name!r} is not set")

    hex_text = value.strip()
    try:
        key = bytes.fromhex(hex_text)
    except ValueError as exc:
        raise ValueError(f"environment variable {name!r} is not valid hex") from exc

    if len(key) != C.KEY_BYTES:
        raise ValueError(
            f"key from env {name!r} decodes to {len(key)} bytes, expected {C.KEY_BYTES}"
        )
    return key


def load_key_from_file(path) -> bytes:
    """Load a 32-byte key from a file, accepting either hex text (64
    hex characters) or exactly 32 raw bytes -- the loader distinguishes
    them by length."""
    data = Path(path).read_bytes()

    try:
        text = data.decode("ascii")
    except UnicodeDecodeError:
        text = None

    if text is not None:
        hex_candidate = "".join(text.split())
        if len(hex_candidate) == 2 * C.KEY_BYTES and all(c in _HEX_CHARS for c in hex_candidate):
            return bytes.fromhex(hex_candidate)

    if len(data) == C.KEY_BYTES:
        return data

    raise ValueError(
        f"key file {path!r} is neither {2 * C.KEY_BYTES} hex characters "
        f"nor exactly {C.KEY_BYTES} raw bytes"
    )
