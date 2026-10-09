"""Field widths, bounds, and size tables for QR Payload Protocol v1.4,
carrying only the two opcode types this deployment actually uses.

Layout (spec sections 2.1-2.3):

    OUTER (printed): <VER:2><ENVELOPE:variable><OCRC:5>
    ENVELOPE       : decimal rendering of nonce(12B) || ciphertext || tag(16B)
    INNER (secret) : <SKU:4><COUNT:2><OP1:4><D1:4> ... <OPn:4><Dn:4><TS:10><MID:6><ICRC:5>

TYPE_WEIGHT (whole grams) and TYPE_BOOLEAN are the only two types.

The published spec assigns "01" to percentage and "02" to boolean, with
no type 03 defined at all. This deployment has no use for a percentage
type -- nothing in the live store GUI has ever emitted one, since the
sugar dial is converted to grams client-side before the pairs are
built (see store_gui/drinks-pos.js) -- so TYPE_WEIGHT was given "01" in
its place rather than leaving that slot unused or bolting weight on as
a third type. A decoder written against the published spec would read
a "01" pair here as a percentage; that mismatch is intentional and
local to this deployment, not a spec violation to fix later. If
percentage ever needs to be shown again (order history, a receipt),
that is a display concern resolved from a value recorded elsewhere --
not a reason to bring a percentage type back into the wire format.
"""

import math

# --- outer layer -------------------------------------------------------
VER_DIGITS = 2
VER = "14"
OCRC_DIGITS = 5

# --- inner layer --------------------------------------------------------
SKU_DIGITS = 4
COUNT_DIGITS = 2
OPCODE_DIGITS = 4
DATA_DIGITS = 4
TS_DIGITS = 10
MID_DIGITS = 6
ICRC_DIGITS = 5

PAIR_DIGITS = OPCODE_DIGITS + DATA_DIGITS                     # 8
INNER_HEADER_DIGITS = SKU_DIGITS + COUNT_DIGITS                # 6

MAX_PAIRS = 12

SKU_MIN, SKU_MAX = 0, 10 ** SKU_DIGITS - 1                     # 0000-9999
MID_MIN, MID_MAX = 1, 10 ** MID_DIGITS - 1                     # 000001-999999
MID_RESERVED = 0                                                # 000000, never valid
TS_MIN, TS_MAX = 0, 10 ** TS_DIGITS - 1

INGREDIENT_MIN = 1
INGREDIENT_MAX = 24

TYPE_BOOLEAN = "02"
TYPE_WEIGHT = "01"                # local extension -- whole grams for the pumps

BOOLEAN_FALSE = "0000"
BOOLEAN_TRUE = "0001"
WEIGHT_MAX_RAW = 9999             # grams; the field's own 4-digit ceiling

MIN_INNER_LEN = INNER_HEADER_DIGITS + TS_DIGITS + MID_DIGITS + ICRC_DIGITS        # 27, n=0
MAX_INNER_LEN = MIN_INNER_LEN + PAIR_DIGITS * MAX_PAIRS                            # 123, n=12

# --- cryptography --------------------------------------------------------
KEY_BYTES = 32
NONCE_BYTES = 12
TAG_BYTES = 16
AAD = VER.encode("ascii")


def inner_len(n: int) -> int:
    return MIN_INNER_LEN + PAIR_DIGITS * n


def plaintext_bytes(n: int) -> int:
    """BCD-packed size of the inner digit string: 2 digits/byte, with a
    trailing 0xF pad nibble since inner_len(n) is always odd."""
    return (inner_len(n) + 1) // 2


def envelope_bytes(n: int) -> int:
    return NONCE_BYTES + plaintext_bytes(n) + TAG_BYTES


def _decimal_width(n_bytes: int) -> int:
    return math.ceil(n_bytes * math.log10(256))


def outer_len(n: int) -> int:
    return VER_DIGITS + _decimal_width(envelope_bytes(n)) + OCRC_DIGITS


def is_digits_only(s: str) -> bool:
    return isinstance(s, str) and len(s) > 0 and s.isdigit()


# --- size table, generated at import time (spec section 2.3) -----------
# One entry per opcode count 0..12: byte length B, envelope digit width D,
# and the outer digit length a decoder can look the count back up from.
_ENTRIES = []
for _n in range(MAX_PAIRS + 1):
    _B = envelope_bytes(_n)
    _D = _decimal_width(_B)
    _outer = VER_DIGITS + _D + OCRC_DIGITS
    _ENTRIES.append({"n": _n, "B": _B, "D": _D, "inner_len": inner_len(_n), "outer_len": _outer})

B_TO_ENTRY = {e["B"]: e for e in _ENTRIES}
OUTER_LEN_TO_ENTRY = {e["outer_len"]: e for e in _ENTRIES}
INNER_LEN_TO_N = {e["inner_len"]: e["n"] for e in _ENTRIES}

# Two properties the whole length-recovery scheme depends on. Plain
# runtime checks, not asserts, so they survive `python -O` (spec A.3).
if len({e["outer_len"] for e in _ENTRIES}) != len(_ENTRIES):
    raise RuntimeError("qrproto.constants: outer_len is not one-to-one over the count table")
if [e["D"] for e in _ENTRIES] != sorted(e["D"] for e in _ENTRIES):
    raise RuntimeError("qrproto.constants: D(B) is not strictly increasing over the count table")
