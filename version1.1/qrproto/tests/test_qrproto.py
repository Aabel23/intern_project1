"""Test suite for qrproto: vectors, round trips, and one rejection per
verification stage (spec section 8). Run with pytest:

    python3 -m pytest qrproto/tests/ -v
"""

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest

from qrproto import ChecksumError  # noqa: F401  (re-export sanity, see test below)
from qrproto import create, verify
from qrproto.api import _normalize_machine_id, _validate_key
from qrproto.crc import compute_crc, crc16_ccitt
from qrproto.envelope import bcd_pack, bcd_unpack, decrypt_payload, encrypt_payload
from qrproto.errors import (
    ClockSkewError,
    CryptoError,
    ExpiredError,
    FormatError,
    MachineMismatchError,
    ProtocolError,
)
from qrproto.inner import Grams, Instruction, decode_inner, encode_inner
from qrproto.qr import VERSION_FOR_COUNT, minimum_version, symbol_dimensions

KEY = bytes(range(32))
NOW = 1700000000
MID = 123


# --- CRC -----------------------------------------------------------------

def test_crc_known_vector():
    # Standard CRC-16/CCITT-FALSE check value for ASCII "123456789".
    assert crc16_ccitt(b"123456789") == 0x29B1


def test_compute_crc_is_five_digits():
    assert len(compute_crc("004200")) == 5


# --- BCD packing -----------------------------------------------------------

def test_bcd_round_trip_odd_length():
    # Every inner payload this protocol produces is 27 + 8n digits,
    # always odd -- bcd_pack always appends a 0xF pad nibble for an
    # odd-length input, and bcd_unpack always expects to find one.
    # An even-length input is not a shape this protocol ever packs.
    assert bcd_unpack(bcd_pack("123")) == "123"


def test_bcd_unpack_rejects_wrong_pad():
    packed = bytearray(bcd_pack("123"))
    packed[-1] = (packed[-1] & 0xF0) | 0x3          # pad nibble should be 0xF
    with pytest.raises(FormatError):
        bcd_unpack(bytes(packed))


# --- inner layer: round trip for every opcode count ------------------------

@pytest.mark.parametrize("count", range(13))
def test_inner_round_trip_every_count(count):
    instructions = [
        Instruction(i, Grams(i * 10)) if i % 2 else Instruction(i, True)
        for i in range(1, count + 1)
    ]
    inner = encode_inner(sku=42, instructions=instructions, timestamp=NOW, machine_id=MID)
    assert len(inner) == 27 + 8 * count

    parsed = decode_inner(inner)
    assert parsed["sku"] == 42
    assert parsed["count"] == count
    assert parsed["timestamp"] == NOW
    assert parsed["machine_id"] == MID
    assert [i.ingredient for i in parsed["instructions"]] == list(range(1, count + 1))


def test_inner_mid_reserved_rejected_at_decode():
    # Hand-build a structurally valid inner body with MID = 000000.
    body = "0042" + "00" + f"{NOW:010d}" + "000000"
    inner = body + compute_crc(body)
    with pytest.raises(ProtocolError, match="reserved"):
        decode_inner(inner)


def test_inner_duplicate_ingredient_rejected_at_encode():
    with pytest.raises(ProtocolError, match="duplicate"):
        encode_inner(42, [Instruction(7, True), Instruction(7, Grams(5))], NOW, MID)


@pytest.mark.parametrize("bad_ingredient", [0, 25])
def test_inner_ingredient_out_of_range(bad_ingredient):
    with pytest.raises(ProtocolError):
        encode_inner(42, [Instruction(bad_ingredient, True)], NOW, MID)


@pytest.mark.parametrize("weight", [0, 9999])
def test_weight_boundary_values_round_trip(weight):
    inner = encode_inner(42, [Instruction(1, Grams(weight))], NOW, MID)
    parsed = decode_inner(inner)
    assert parsed["instructions"][0].value == weight


def test_weight_above_boundary_rejected():
    with pytest.raises(ProtocolError):
        Instruction(1, Grams(10000)).encode()


def test_boolean_invalid_data_rejected():
    # Hand-craft a pair with data 0007 under type 02 (boolean).
    body = "0042" + "01" + "0102" + "0007" + f"{NOW:010d}" + f"{MID:06d}"
    inner = body + compute_crc(body)
    with pytest.raises(ProtocolError, match="boolean"):
        decode_inner(inner)


def test_registry_membership_enforced():
    inner = encode_inner(42, [Instruction(7, True)], NOW, MID)
    with pytest.raises(ProtocolError, match="registry"):
        decode_inner(inner, registry={1, 2, 3})       # 7 not in registry
    decode_inner(inner, registry={7})                  # present -> fine


# --- envelope: encrypt/decrypt, tamper detection ---------------------------

def test_envelope_round_trip():
    inner = encode_inner(42, [Instruction(7, Grams(13)), Instruction(12, True)], NOW, MID)
    outer = encrypt_payload(inner, KEY)
    assert outer[:2] == "14"
    assert decrypt_payload(outer, KEY) == inner


def test_envelope_wrong_key_is_crypto_error():
    inner = encode_inner(42, [], NOW, MID)
    outer = encrypt_payload(inner, KEY)
    wrong_key = bytes((b + 1) % 256 for b in KEY)
    with pytest.raises(CryptoError):
        decrypt_payload(outer, wrong_key)


def test_envelope_bad_ocrc_is_checksum_error():
    inner = encode_inner(42, [], NOW, MID)
    outer = encrypt_payload(inner, KEY)
    tampered = outer[:-1] + ("0" if outer[-1] != "0" else "1")
    with pytest.raises(ChecksumError):
        decrypt_payload(tampered, KEY)


def test_envelope_bad_ver_is_format_error():
    inner = encode_inner(42, [], NOW, MID)
    outer = encrypt_payload(inner, KEY)
    bad = "13" + outer[2:]
    with pytest.raises(FormatError):
        decrypt_payload(bad, KEY)


def test_envelope_wrong_length_is_format_error():
    with pytest.raises(FormatError):
        decrypt_payload("140" * 20, KEY)          # not in the outer-length table


def test_old_v13_length_never_collides():
    """A v1.3 payload (11 + 8m digits, m=0..12) must never match a v1.4
    outer length -- this is the property that lets a v1.4 scanner reject
    a stale label on length alone. Same logic that motivated the SERIAL
    extension in the old plaintext protocol."""
    from qrproto import constants as C
    v13_lengths = {11 + 8 * m for m in range(13)}
    v14_lengths = {C.outer_len(n) for n in range(13)}
    assert v13_lengths & v14_lengths == set()


def test_envelope_value_overflow_is_format_error():
    """A hand-crafted, correctly-OCRC'd payload whose envelope digits
    spell a number >= 256**B must be rejected as a format error, not
    crash int.to_bytes() with a raw OverflowError (spec section 4.3)."""
    from qrproto import constants as C
    entry = C.OUTER_LEN_TO_ENTRY[109]              # count = 0
    huge = str(256 ** entry["B"])                   # exactly at the boundary, too big
    envelope_digits = huge.zfill(entry["D"])
    body = C.VER + envelope_digits
    outer = body + compute_crc(body)
    assert len(outer) == 109
    with pytest.raises(FormatError, match="exceeds"):
        decrypt_payload(outer, KEY)


# --- api.create / api.verify: full 8-stage order ----------------------------

def test_create_verify_happy_path():
    payload = create(42, [Instruction(7, Grams(13)), Instruction(12, True)], MID, KEY, now=NOW)
    result = verify(payload, KEY, MID, now=NOW)
    assert result["sku"] == 42
    assert [(i.ingredient, i.value) for i in result["instructions"]] == [(7, 13), (12, True)]


def test_stage6_machine_mismatch():
    payload = create(42, [], MID, KEY, now=NOW)
    with pytest.raises(MachineMismatchError):
        verify(payload, KEY, machine_id=MID + 1, now=NOW)


@pytest.mark.parametrize("age,should_pass", [(600, True), (601, False)])
def test_stage7_expiry_boundary_is_inclusive(age, should_pass):
    payload = create(42, [], MID, KEY, now=NOW)
    if should_pass:
        verify(payload, KEY, MID, now=NOW + age)
    else:
        with pytest.raises(ExpiredError):
            verify(payload, KEY, MID, now=NOW + age)


@pytest.mark.parametrize("skew,should_pass", [(30, True), (31, False)])
def test_stage7_clock_skew_boundary_is_inclusive(skew, should_pass):
    payload = create(42, [], MID, KEY, now=NOW + skew)
    if should_pass:
        verify(payload, KEY, MID, now=NOW)
    else:
        with pytest.raises(ClockSkewError):
            verify(payload, KEY, MID, now=NOW)


def test_stage_ordering_expiry_wins_over_semantics():
    """A payload that is both expired and fails a stage-8 semantic
    check (ingredient not in registry) must be reported as expired --
    stage 7 gates stage 8, per spec section 8."""
    payload = create(42, [Instruction(7, True)], MID, KEY, now=NOW)
    with pytest.raises(ExpiredError):
        verify(payload, KEY, MID, now=NOW + 601, registry={99})


def test_stage_ordering_machine_mismatch_wins_over_expiry():
    """Stage 6 (machine binding) runs before stage 7 (freshness) -- a
    payload that is both mistargeted and expired must be reported as
    a machine mismatch."""
    payload = create(42, [], MID, KEY, now=NOW)
    with pytest.raises(MachineMismatchError):
        verify(payload, KEY, machine_id=MID + 1, now=NOW + 601)


def test_validate_key_rejects_wrong_length():
    with pytest.raises(ValueError):
        _validate_key(b"short")


def test_validate_key_rejects_wrong_type():
    with pytest.raises(ValueError):
        _validate_key("not bytes")


def test_normalize_machine_id_rejects_float():
    with pytest.raises(ValueError):
        _normalize_machine_id(123.7)


def test_normalize_machine_id_accepts_digit_string():
    assert _normalize_machine_id("000123") == 123


# --- qr sizing ---------------------------------------------------------

def test_version_table_matches_spec_5_2():
    expected = {0: 6, 1: 6, 2: 6, 3: 6, 4: 7, 5: 8, 6: 8, 7: 8, 8: 8, 9: 8, 10: 9, 11: 9, 12: 9}
    assert VERSION_FOR_COUNT == expected


def test_minimum_version_matches_payload_count():
    payload = create(42, [Instruction(i, True) for i in range(1, 6)], MID, KEY, now=NOW)
    assert minimum_version(payload) == 8


def test_symbol_dimensions_version_6():
    dims = symbol_dimensions(6)
    assert dims["modules"] == 41
    assert dims["symbol_mm"] == 20.5
    assert dims["footprint_mm"] == 24.5


# --- __init__ re-exports ----------------------------------------------------

def test_top_level_reexports_work():
    payload = create(42, [], MID, KEY, now=NOW)
    with pytest.raises(ChecksumError):
        decrypt_payload(payload[:-1] + ("0" if payload[-1] != "0" else "1"), KEY)
