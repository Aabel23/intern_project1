"""High-level API: create() and verify() are what production code
calls. Everything in constants/crc/inner/envelope exists to support
these two functions.

verify() runs the full eight-stage order from spec section 8:

    1-3  outer structure/CRC, decrypt        (envelope.decrypt_payload)
    4-5  inner structure, inner CRC          (inner._parse_inner_structure)
    6    machine ID match                    (here)
    7    freshness / clock skew              (here)
    8    per-pair semantics                  (inner._check_pair_semantics)

Stage 6 and 7 run between the two inner.py halves deliberately: a
payload that is both expired and carries a bad ingredient must be
rejected as ExpiredError, not as a semantic error about the
ingredient, per the ordering in spec section 8.
"""

import time

from . import constants as C
from .envelope import decrypt_payload, encrypt_payload
from .errors import ClockSkewError, ExpiredError, MachineMismatchError
from .inner import _check_pair_semantics, _parse_inner_structure, encode_inner

from flexmix_debug import trace          # noqa: E402


def _validate_key(key) -> None:
    """Reject a malformed key immediately with a clear ValueError,
    instead of letting it crash later inside AES-GCM (a confusing
    stdlib exception)."""
    if not isinstance(key, (bytes, bytearray)) or len(key) != C.KEY_BYTES:
        actual_len = len(key) if hasattr(key, "__len__") else "n/a"
        raise ValueError(
            f"key must be {C.KEY_BYTES} raw bytes, got "
            f"{type(key).__name__} of length {actual_len}"
        )


def _normalize_machine_id(machine_id) -> int:
    """Strict machine-id normalization: an int (bool excluded) or a
    pure digit string. Floats and every other type are rejected rather
    than truncated -- stage 6 is a security check, so a sloppy caller
    must fail closed, never silently match a different machine."""
    if isinstance(machine_id, int) and not isinstance(machine_id, bool):
        return machine_id
    if isinstance(machine_id, str) and machine_id.isdigit():
        return int(machine_id)
    raise ValueError(
        f"machine_id must be an int or a digit string, got "
        f"{type(machine_id).__name__}: {machine_id!r}"
    )


@trace
def create(sku, instructions, machine_id, key, *, now=None) -> str:
    """Build a complete outer (printed) payload string.

    now : injected Unix-epoch-seconds timestamp for the TS field, or
    None to use time.time(). Tests should always inject a fixed value;
    production code should not.
    """
    _validate_key(key)
    machine_id = _normalize_machine_id(machine_id)
    ts = int(now) if now is not None else int(time.time())

    inner_digits = encode_inner(sku, instructions, ts, machine_id)
    return encrypt_payload(inner_digits, key)


@trace
def verify(
    payload: str,
    key: bytes,
    machine_id: int,
    *,
    max_age_seconds: int = 600,
    clock_skew_seconds: int = 30,
    now=None,
    registry=None,
) -> dict:
    """Full 8-stage verification (spec section 8).

    Any failure raises a ProtocolError subclass and nothing from the
    payload is ever returned to the caller.

    Returns {"sku", "count", "instructions", "timestamp", "machine_id"}.
    """
    _validate_key(key)
    machine_id = _normalize_machine_id(machine_id)

    inner_digits = decrypt_payload(payload, key)          # stages 1, 2, 3
    parsed = _parse_inner_structure(inner_digits)          # stages 4, 5

    # --- stage 6: machine ID ------------------------------------------
    if parsed["machine_id"] != machine_id:
        raise MachineMismatchError(
            f"stage 6 (machine id): payload targets machine "
            f"{parsed['machine_id']:06d}, scanner is configured as "
            f"{machine_id:06d}"
        )

    # --- stage 7: expiry / clock skew ----------------------------------
    current = now if now is not None else time.time()
    ts = parsed["timestamp"]

    age = current - ts
    if age > max_age_seconds:
        raise ExpiredError(
            f"stage 7 (expiry): payload age {age}s exceeds "
            f"max_age_seconds={max_age_seconds}"
        )

    skew = ts - current
    if skew > clock_skew_seconds:
        raise ClockSkewError(
            f"stage 7 (clock skew): payload timestamp is {skew}s ahead "
            f"of now, exceeds clock_skew_seconds={clock_skew_seconds}"
        )

    # --- stage 8: semantics ---------------------------------------------
    instructions = _check_pair_semantics(parsed["pairs_raw"], registry=registry)

    return {
        "sku": parsed["sku"],
        "count": parsed["count"],
        "instructions": instructions,
        "timestamp": parsed["timestamp"],
        "machine_id": parsed["machine_id"],
    }
