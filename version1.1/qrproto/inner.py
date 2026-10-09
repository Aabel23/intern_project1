"""The inner (encrypted) payload: instruction model, encode, decode.

Layout (spec section 2.2, this deployment's two types):

    <SKU:4><COUNT:2><OP1:4><D1:4> ... <OPn:4><Dn:4><TS:10><MID:6><ICRC:5>

where each opcode is <INGREDIENT:2><TYPE:2>, 0 <= n <= 12, and TYPE is
either TYPE_WEIGHT ("01", whole grams) or TYPE_BOOLEAN ("02"). See
constants.py for why "01" means weight here rather than percentage.

decode_inner() is a composition of two private halves so that
api.verify() (stage 6 machine ID, stage 7 freshness) can run *between*
them: `_parse_inner_structure` does stages 4-5 only (structure, inner
CRC) and returns raw, not-yet-semantically-checked fields;
`_check_pair_semantics` does stage 8 only. Fusing all three into one
function would force stage 8 to run before stages 6/7, which is not
the order the spec requires (section 8).
"""

from dataclasses import dataclass

from . import constants as C
from .crc import compute_crc
from .errors import ChecksumError, FormatError, ProtocolError

from flexmix_debug import trace          # noqa: E402


class Grams(int):
    """A whole-gram weight, so a value carries its own protocol type.
    Behaves as a plain int everywhere else: Grams(120) == 120."""

    def __repr__(self) -> str:
        return f"Grams({int(self)})"


@dataclass(frozen=True)
class Instruction:
    """One opcode/data pair.

    ingredient : 1-24, the database ingredient identifier
    value      : Grams for a weight, or bool for a flag
    """

    ingredient: int
    value: "Grams | bool"

    @property
    def type_code(self) -> str:
        # bool is checked first: in Python bool is a subclass of int, so a
        # plain isinstance(value, int) check would misclassify it.
        if isinstance(self.value, bool):
            return C.TYPE_BOOLEAN
        return C.TYPE_WEIGHT

    def encode(self) -> str:
        if not C.INGREDIENT_MIN <= self.ingredient <= C.INGREDIENT_MAX:
            raise ProtocolError(
                f"stage 8 (semantics): ingredient {self.ingredient} "
                f"outside range {C.INGREDIENT_MIN}-{C.INGREDIENT_MAX}"
            )

        opcode = f"{self.ingredient:02d}{self.type_code}"

        if isinstance(self.value, bool):
            data = C.BOOLEAN_TRUE if self.value else C.BOOLEAN_FALSE
            return opcode + data

        raw = int(self.value)
        if not 0 <= raw <= C.WEIGHT_MAX_RAW:
            raise ProtocolError(
                f"stage 8 (semantics): weight {raw} g outside range "
                f"0-{C.WEIGHT_MAX_RAW} g"
            )
        return opcode + f"{raw:04d}"


@trace
def encode_inner(sku: int, instructions: list, timestamp: int, machine_id: int) -> str:
    """Build the inner digit string from a SKU, instruction list,
    Unix-epoch-seconds timestamp, and target machine ID.

    Raises ProtocolError (or a subclass) on any out-of-range value.
    Duplicate ingredients are rejected here as well as at decode time,
    so a faulty payload is never produced.
    """
    if not C.SKU_MIN <= sku <= C.SKU_MAX:
        raise ProtocolError(f"SKU {sku} outside range 0000-9999")

    if len(instructions) > C.MAX_PAIRS:
        raise ProtocolError(
            f"{len(instructions)} instructions exceeds maximum {C.MAX_PAIRS}"
        )

    seen = set()
    for inst in instructions:
        if inst.ingredient in seen:
            raise ProtocolError(
                f"stage 8 (semantics): duplicate ingredient {inst.ingredient:02d}"
            )
        seen.add(inst.ingredient)

    if not C.TS_MIN <= timestamp <= C.TS_MAX:
        raise ProtocolError(f"timestamp {timestamp} outside range {C.TS_MIN}-{C.TS_MAX}")

    if not C.MID_MIN <= machine_id <= C.MID_MAX:
        raise ProtocolError(
            f"machine_id {machine_id} outside range "
            f"{C.MID_MIN}-{C.MID_MAX} (000000 is reserved/invalid)"
        )

    body = f"{sku:0{C.SKU_DIGITS}d}{len(instructions):0{C.COUNT_DIGITS}d}"
    body += "".join(inst.encode() for inst in instructions)
    body += f"{timestamp:0{C.TS_DIGITS}d}{machine_id:0{C.MID_DIGITS}d}"

    return body + compute_crc(body)


def _parse_inner_structure(digits: str) -> dict:
    """Stages 4 (structure) and 5 (inner CRC) only -- no pair semantics
    (stage 8). Returns the raw, not-yet-semantically-checked fields:
    sku, count, a list of (ingredient_digits, type_code, data_digits)
    tuples per pair, timestamp, and machine_id.
    """
    # --- stage 4: structure ------------------------------------------
    if not C.is_digits_only(digits):
        raise FormatError("stage 4 (inner structure): payload must be digits only")

    if not C.MIN_INNER_LEN <= len(digits) <= C.MAX_INNER_LEN:
        raise FormatError(
            f"stage 4 (inner structure): length {len(digits)} outside "
            f"valid range {C.MIN_INNER_LEN}-{C.MAX_INNER_LEN}"
        )

    count_str = digits[C.SKU_DIGITS:C.INNER_HEADER_DIGITS]
    count = int(count_str)
    if not 0 <= count <= C.MAX_PAIRS:
        raise FormatError(
            f"stage 4 (inner structure): count {count_str} exceeds maximum {C.MAX_PAIRS}"
        )

    expected_len = C.inner_len(count)
    if len(digits) != expected_len:
        raise FormatError(
            f"stage 4 (inner structure): count {count:02d} implies "
            f"{expected_len} digits, got {len(digits)}"
        )

    # --- stage 5: inner CRC -------------------------------------------
    split = expected_len - C.ICRC_DIGITS
    body, icrc = digits[:split], digits[split:]
    expected_icrc = compute_crc(body)
    if icrc != expected_icrc:
        raise ChecksumError(f"stage 5 (inner CRC): got {icrc}, expected {expected_icrc}")

    sku = int(body[0:C.SKU_DIGITS])

    pairs_raw = []
    for index in range(count):
        base = C.INNER_HEADER_DIGITS + index * C.PAIR_DIGITS
        pairs_raw.append(
            (body[base:base + 2], body[base + 2:base + 4], body[base + 4:base + 8])
        )

    pairs_end = C.INNER_HEADER_DIGITS + C.PAIR_DIGITS * count
    ts_str = body[pairs_end:pairs_end + C.TS_DIGITS]
    mid_str = body[pairs_end + C.TS_DIGITS:pairs_end + C.TS_DIGITS + C.MID_DIGITS]
    timestamp = int(ts_str)
    machine_id = int(mid_str)

    # 000000-reserved is a property of the MID field itself (like a bad
    # VER or a bad count), not a per-pair semantic rule and not "does
    # this MID match the scanner" (that is stage 6, in api.verify,
    # which needs the scanner's configured machine_id -- context this
    # function does not have).
    if machine_id == C.MID_RESERVED:
        raise ProtocolError("stage 4 (inner structure): machine id 000000 is reserved/invalid")

    return {
        "sku": sku,
        "count": count,
        "pairs_raw": pairs_raw,
        "timestamp": timestamp,
        "machine_id": machine_id,
    }


def _check_pair_semantics(pairs_raw, registry=None) -> list:
    """Stage 8 only: opcode/data pair semantics (ingredient range,
    registry membership, duplicate check, and the data range for the
    pair's type). Split out of decode_inner so api.verify() can run
    this after stages 6 and 7."""
    instructions = []
    seen = set()

    for index, (ingredient_s, type_code, data) in enumerate(pairs_raw):
        pair = index + 1
        ingredient = int(ingredient_s)

        if not C.INGREDIENT_MIN <= ingredient <= C.INGREDIENT_MAX:
            raise ProtocolError(
                f"stage 8 (semantics): pair {pair}: ingredient {ingredient_s} "
                f"outside range {C.INGREDIENT_MIN:02d}-{C.INGREDIENT_MAX:02d}"
            )

        if registry is not None and ingredient not in registry:
            raise ProtocolError(
                f"stage 8 (semantics): pair {pair}: ingredient {ingredient_s} not in registry"
            )

        if ingredient in seen:
            raise ProtocolError(
                f"stage 8 (semantics): pair {pair}: duplicate ingredient {ingredient_s}"
            )
        seen.add(ingredient)

        if type_code == C.TYPE_WEIGHT:
            # Every 4-digit value is a legal weight -- 9999 is the
            # field's own ceiling, so there is no separate bound to check.
            value = Grams(int(data))
        elif type_code == C.TYPE_BOOLEAN:
            if data not in (C.BOOLEAN_FALSE, C.BOOLEAN_TRUE):
                raise ProtocolError(
                    f"stage 8 (semantics): pair {pair}: boolean must be "
                    f"{C.BOOLEAN_FALSE} or {C.BOOLEAN_TRUE}, got {data}"
                )
            value = data == C.BOOLEAN_TRUE
        else:
            raise ProtocolError(f"stage 8 (semantics): pair {pair}: unknown type {type_code}")

        instructions.append(Instruction(ingredient=ingredient, value=value))

    return instructions


@trace
def decode_inner(digits: str, *, registry=None) -> dict:
    """Parse and validate the inner digit string: stages 4, 5, and 8
    only -- no machine-ID or expiry check, since those need context
    (the scanner's machine_id and the current time) this function does
    not receive. See api.verify() for the full 8-stage check.

    Returns {"sku", "count", "instructions", "timestamp", "machine_id"}.
    """
    parsed = _parse_inner_structure(digits)
    instructions = _check_pair_semantics(parsed["pairs_raw"], registry=registry)
    return {
        "sku": parsed["sku"],
        "count": parsed["count"],
        "instructions": instructions,
        "timestamp": parsed["timestamp"],
        "machine_id": parsed["machine_id"],
    }
