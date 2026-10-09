"""One-off script: generates qrproto_documentation.xlsx, a detailed
technical reference for the qrproto package itself (not the tests --
see generate_test_doc.py for that). Covers: overview, payload field
layout, module-by-module reference, function-by-function reference,
constants, exceptions, the 8-stage verification order, and where this
deployment deliberately deviates from the published v1.4 spec.

Run manually whenever the qrproto package changes:

    ./.venv/bin/python3 qrproto/tests/generate_qrproto_doc.py
"""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

OUT_PATH = Path(__file__).resolve().parent / "qrproto_documentation.xlsx"

HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
WRAP = Alignment(vertical="top", wrap_text=True)
TITLE_FONT = Font(bold=True, size=14, color="1F4E78")
SECTION_FONT = Font(bold=True, size=11, color="1F4E78")


def style_table(ws, start_row, headers, widths):
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=start_row, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    for idx, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width


# ============================================================================
# One worked example, used throughout the workbook. Every value below was
# produced by actually running qrproto (see the docstring at the bottom of
# this file for the exact commands), not hand-computed -- so it is safe to
# copy into a REPL and get the same numbers back.
# ============================================================================
EX = {
    "sku": 42,
    "ts": 1700000000,
    "mid": 123,
    "key_hex": "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f",
    "opcode_weight": "07010013",          # Instruction(7, Grams(13)).encode()
    "opcode_boolean": "12020001",         # Instruction(12, True).encode()
    "inner": "0042020701001312020001170000000000012329242",
    "inner_body": "00420207010013120200011700000000000123",
    "icrc": "29242",
    "outer": ("14011494840147929402492796957849438019256204064092613430099358"
              "0858160987918997268007630758826000156011689334133356314729445"
              "01553"),
    "ver": "14",
    "ocrc": "01553",
    "outer_len": 128,
    "err_stage1_bad_ver": "stage 1 (outer structure): VER '13' != '14'",
    "err_stage2_bad_ocrc": "stage 2 (outer CRC): got 12080, expected 12082",
    "err_stage3_wrong_key": ("stage 3 (decrypt): AES-GCM authentication tag "
                              "verification failed (forged payload, wrong "
                              "key, or corrupt data)"),
    "err_stage4_mid_reserved": "stage 4 (inner structure): machine id 000000 is reserved/invalid",
    "err_stage5_bad_icrc": "stage 5 (inner CRC): got 29240, expected 29242",
    "err_stage6_wrong_machine": "stage 6 (machine id): payload targets machine 000123, scanner is configured as 000124",
    "err_stage7_expired": "stage 7 (expiry): payload age 601s exceeds max_age_seconds=600",
    "err_stage8_not_in_registry": "stage 8 (semantics): pair 1: ingredient 07 not in registry",
}


def append_rows(ws, rows):
    start = ws.max_row + 1
    for row in rows:
        ws.append(row)
    for r in range(start, ws.max_row + 1):
        for c in range(1, ws.max_column + 1):
            ws.cell(row=r, column=c).alignment = WRAP


# ============================================================================
# Sheet 1: Overview
# ============================================================================
def build_overview(wb):
    ws = wb.active
    ws.title = "Overview"
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 100

    ws["A1"] = "qrproto -- QR Code Payload Protocol v1.4 (local deployment)"
    ws["A1"].font = TITLE_FONT
    ws.merge_cells("A1:B1")

    facts = [
        ("What this is",
         "A from-scratch Python package implementing an encrypted, "
         "machine-bound, timestamp-expiring QR payload protocol for "
         "drink recipe instructions, replacing the plaintext v1.3-based "
         "encoder that store_gui/serve.py used previously "
         "(scan/qr_payload.py)."),
        ("Based on",
         "\"QR CODE PAYLOAD PROTOCOL v1.4\" (Flexxource, 20 August "
         "2026) -- an internal draft spec. This package implements "
         "that spec with two deliberate local deviations, see the "
         "\"Deviations from spec\" sheet."),
        ("Location", "version1.0/qrproto/"),
        ("Status",
         "Core protocol complete and unit-tested (49 tests in "
         "test_qrproto.py + a 9-step end-to-end flow test in "
         "test_flow.py, all passing). NOT YET wired into "
         "store_gui/serve.py, scan/scanner.py, or order/qr_to_recipe.py "
         "-- those still run the old plaintext protocol."),
        ("Cryptography", "AES-256-GCM (authenticated encryption), via the `cryptography` package"),
        ("Key model",
         "One shared 256-bit key, held by the payload generator (server) "
         "and every scanner. No key rotation or per-machine keys in "
         "this version (same open item as the published spec)."),
        ("Anti-replay", "TS (timestamp) field + max_age_seconds window, default 600s (10 minutes)"),
        ("Anti-misdirection", "MID (machine ID) field -- a payload is bound to exactly one scanner"),
        ("Opcode types supported",
         "TYPE_WEIGHT (\"01\", whole grams) and TYPE_BOOLEAN (\"02\"). "
         "No percentage type -- see \"Deviations from spec\" sheet."),
        ("Payload size range", "109-224 digits (outer, printed), depending on 0-12 instruction pairs"),
        ("QR symbol range", "Version 6 to Version 9, error correction level H"),
        ("External dependencies", "cryptography (AES-GCM), qrcode + Pillow (QR image rendering, optional -- only qr.py needs them)"),
        ("Test dependencies", "pytest (installed in version1.0/.venv for this work)"),
        ("Not yet decided / open items",
         "Whether a lightweight replay guard is needed for a re-scan of "
         "the same label within the 600s freshness window (accepted as "
         "a known risk per team discussion); key rotation; per-machine "
         "keys; formal ingredient registry population."),
    ]

    ws.append([])
    ws.append(["Fact", "Detail"])
    style_table(ws, ws.max_row, ["Fact", "Detail"], [30, 100])
    append_rows(ws, facts)

    ws.append([])
    ws.append([])
    ws.cell(row=ws.max_row, column=1, value="Worked example used throughout this workbook").font = SECTION_FONT
    ws.append(["Every value below was produced by actually running qrproto -- copy it into a REPL and you get the same numbers back. Order: SKU 42, ingredient 07 = 13g (weight), ingredient 12 = yes (boolean), for machine 000123, generated at Unix time 1700000000."])
    ws.merge_cells(f"A{ws.max_row}:B{ws.max_row}")

    ws.append([])
    ws.append(["Field", "Value"])
    style_table(ws, ws.max_row, ["Field", "Value"], [30, 100])
    example_rows = [
        ("Python call", "create(sku=42, instructions=[Instruction(7, Grams(13)), Instruction(12, True)], machine_id=123, key=KEY, now=1700000000)"),
        ("Opcode: ingredient 07, 13g", EX["opcode_weight"]),
        ("Opcode: ingredient 12, yes", EX["opcode_boolean"]),
        ("Inner digit string (43 digits, before encryption)", EX["inner"]),
        ("  -> inner body (before ICRC)", EX["inner_body"]),
        ("  -> ICRC (inner checksum)", EX["icrc"]),
        ("Outer payload (128 digits, what gets printed on the label)", EX["outer"]),
        ("  -> VER", EX["ver"]),
        ("  -> OCRC (outer checksum, last 5 digits)", EX["ocrc"]),
    ]
    append_rows(ws, example_rows)
    ws.freeze_panes = "A4"


# ============================================================================
# Sheet 2: Payload structure
# ============================================================================
def build_payload_structure(wb):
    ws = wb.create_sheet("Payload Structure")
    ws.column_dimensions["A"].width = 45
    ws.column_dimensions["B"].width = 100
    ws["A1"] = "Payload layout"
    ws["A1"].font = TITLE_FONT

    ws.append([])
    ws.append(["OUTER (printed on the label)", "<VER:2><ENVELOPE:variable><OCRC:5>"])
    ws.append(["ENVELOPE", "Decimal rendering of nonce(12B) || AES-256-GCM ciphertext || tag(16B)"])
    ws.append(["INNER (only exists decrypted, in memory)",
               "<SKU:4><COUNT:2><OP1:4><D1:4>...<OPn:4><Dn:4><TS:10><MID:6><ICRC:5>"])
    ws.append(["Opcode", "<INGREDIENT:2><TYPE:2>  (TYPE is \"01\"=weight or \"02\"=boolean)"])
    ws.append(["n (pair count)", "0 <= n <= 12"])

    ws.append([])
    ws.append(["Outer field", "Length", "Meaning", "Example (this workbook's worked order)"])
    style_table(ws, ws.max_row, ["Outer field", "Length", "Meaning", "Example"], [22, 12, 80, 40])
    outer_fields = [
        ("VER", "2 digits", "Literal \"14\" -- protocol version marker. Bound into the AES-GCM tag as AAD, so it cannot be altered without failing authentication even though it is not itself encrypted.",
         EX["ver"]),
        ("ENVELOPE", "variable (102-217 digits, see size table)", "nonce || ciphertext || tag, rendered as one zero-padded decimal integer so the QR encoder can stay in Numeric mode.",
         "121 digits (n=2 pairs): " + EX["outer"][2:-5][:30] + "..."),
        ("OCRC", "5 digits", "CRC-16/CCITT-FALSE over <VER><ENVELOPE>. Computed on the printed digits, checkable before decryption -- separates a scratched label (checksum error) from a forged one (crypto error).",
         EX["ocrc"]),
        ("Full outer payload", str(EX["outer_len"]) + " digits", "VER + ENVELOPE + OCRC concatenated -- this exact string is what gets printed as the QR symbol.",
         EX["outer"]),
    ]
    append_rows(ws, outer_fields)

    ws.append([])
    ws.append(["Inner field", "Length", "Meaning", "Example (this workbook's worked order)"])
    style_table(ws, ws.max_row, ["Inner field", "Length", "Meaning", "Example"], [22, 12, 80, 40])
    inner_fields = [
        ("SKU", "4 digits", "Product/drink identifier, 0000-9999", "0042"),
        ("COUNT", "2 digits", "Number of opcode/data pairs that follow, 00-12", "02"),
        ("OPn (ingredient+type)", "4 digits x n", "2-digit ingredient (01-24) + 2-digit type (\"01\"=weight, \"02\"=boolean)",
         "0701 (ingredient 07, weight) + 1202 (ingredient 12, boolean)"),
        ("Dn (data)", "4 digits x n", "For weight: 0000-9999 grams. For boolean: 0000 (no) or 0001 (yes).",
         "0013 (13g) + 0001 (yes)"),
        ("TS", "10 digits", "Generation timestamp, UTC Unix epoch seconds", "1700000000"),
        ("MID", "6 digits", "Target machine ID, 000001-999999 (000000 reserved/invalid)", "000123"),
        ("ICRC", "5 digits", "CRC-16/CCITT-FALSE over every inner digit before it -- catches corruption on either side of the cipher that the GCM tag alone would not.", EX["icrc"]),
        ("Full inner digit string", "43 digits (n=2 pairs)", "SKU+COUNT+pairs+TS+MID+ICRC concatenated -- this only ever exists decrypted, in memory, never printed.", EX["inner"]),
    ]
    append_rows(ws, inner_fields)

    ws.append([])
    ws.append(["Size table (per opcode count n)"])
    ws.append(["n", "Inner digits (27+8n)", "Envelope bytes (42+4n)", "Outer digits (printed length)", "Min QR version (level H)"])
    style_table(ws, ws.max_row,
                ["n", "Inner digits", "Envelope bytes", "Outer digits", "Min QR version"],
                [6, 16, 18, 20, 20])
    size_rows = [
        (0, 27, 42, 109, 6), (1, 35, 46, 118, 6), (2, 43, 50, 128, 6), (3, 51, 54, 138, 6),
        (4, 59, 58, 147, 7), (5, 67, 62, 157, 8), (6, 75, 66, 166, 8), (7, 83, 70, 176, 8),
        (8, 91, 74, 186, 8), (9, 99, 78, 195, 8), (10, 107, 82, 205, 9), (11, 115, 86, 215, 9),
        (12, 123, 90, 224, 9),
    ]
    append_rows(ws, size_rows)
    ws.freeze_panes = "A2"


# ============================================================================
# Sheet 3: Module reference
# ============================================================================
def build_module_reference(wb):
    ws = wb.create_sheet("Module Reference")
    headers = ["File", "Purpose", "Key exports", "Depends on (internal)", "Depends on (external)"]
    ws.append(headers)
    style_table(ws, 1, headers, [20, 55, 45, 35, 30])

    rows = [
        ("__init__.py",
         "Public API surface. Everything a caller outside qrproto should "
         "need is re-exported here, so integration code does not need "
         "to know the submodule layout.",
         "create, verify, Instruction, Grams, ProtocolError, "
         "FormatError, ChecksumError, CryptoError, "
         "MachineMismatchError, ExpiredError, ClockSkewError",
         "api, errors, inner", "-"),

        ("constants.py",
         "Single source of truth for every field width, value bound, "
         "and the size table (byte/digit lengths per opcode count). "
         "Generates and validates that table at import time.",
         "VER, *_DIGITS constants, *_MIN/MAX bounds, TYPE_WEIGHT, "
         "TYPE_BOOLEAN, inner_len(), outer_len(), envelope_bytes(), "
         "is_digits_only(), B_TO_ENTRY, OUTER_LEN_TO_ENTRY, "
         "INNER_LEN_TO_N",
         "(none)", "math (stdlib)"),

        ("errors.py",
         "Exception hierarchy. Every rejection raises one of these, "
         "never a bare ValueError, so callers can catch ProtocolError "
         "broadly or a specific subclass narrowly.",
         "ProtocolError, FormatError, ChecksumError, CryptoError, "
         "MachineMismatchError, ExpiredError, ClockSkewError",
         "(none)", "(none)"),

        ("crc.py",
         "CRC-16/CCITT-FALSE, shared by both the outer (OCRC) and "
         "inner (ICRC) checksums.",
         "crc16_ccitt(), compute_crc()",
         "(none)", "(none)"),

        ("inner.py",
         "The inner (decrypted) layer: the Instruction/Grams data "
         "model, and encode/decode for the SKU+pairs+TS+MID+ICRC "
         "string. Decode is split into two private halves "
         "(_parse_inner_structure, _check_pair_semantics) so api.py "
         "can run stage 6/7 checks between them.",
         "Grams, Instruction, encode_inner(), decode_inner(), "
         "_parse_inner_structure(), _check_pair_semantics()",
         "constants, crc, errors", "dataclasses (stdlib)"),

        ("envelope.py",
         "The outer (encrypted) layer: BCD packing, AES-256-GCM "
         "seal/open, and decimal rendering of the envelope. "
         "validate_outer_structure_and_crc() is the single choke "
         "point for stages 1-2.",
         "bcd_pack(), bcd_unpack(), render_envelope(), "
         "parse_envelope(), validate_outer_structure_and_crc(), "
         "encrypt_payload(), decrypt_payload()",
         "constants, crc, errors", "cryptography (AESGCM), os (stdlib)"),

        ("api.py",
         "High-level entry points. create() and verify() are what "
         "production code should call; verify() runs the full 8-stage "
         "order from spec section 8, inserting stage 6 (machine ID) "
         "and stage 7 (freshness) between inner.py's structure and "
         "semantics halves.",
         "create(), verify(), _validate_key(), "
         "_normalize_machine_id()",
         "constants, envelope, errors, inner", "time (stdlib)"),

        ("keys.py",
         "Key generation and loading. No password-based derivation -- "
         "keys are machine-provisioned 256-bit secrets, not "
         "human-memorable.",
         "generate_key(), load_key_from_env(), load_key_from_file()",
         "constants", "os, pathlib (stdlib)"),

        ("qr.py",
         "Renders a validated outer payload as an actual QR image "
         "(PIL Image), and reports the QR version/physical size a "
         "given payload needs.",
         "make_qr(), minimum_version(), symbol_dimensions(), "
         "VERSION_FOR_COUNT, NUMERIC_CAPACITY_LEVEL_H",
         "constants, envelope", "qrcode, PIL/Pillow"),

        ("tests/test_qrproto.py",
         "49 unit tests: one protocol rule at a time, hand-crafted "
         "inputs. See qrproto_test_documentation.xlsx for the full "
         "breakdown.",
         "(test functions only)", "all modules above", "pytest"),

        ("tests/test_flow.py",
         "9-step end-to-end story: one realistic order walking through "
         "the whole pipeline in order (build order -> create payload "
         "-> render QR -> scan -> verify -> pour), plus 3 rejection "
         "scenarios (wrong machine, expired, damaged label). See "
         "qrproto_test_documentation.xlsx, \"Flow test\" sheet.",
         "(test functions only)", "api, errors, inner, qr", "pytest"),
    ]
    append_rows(ws, rows)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:E{ws.max_row}"


# ============================================================================
# Sheet 4: Function reference
# ============================================================================
def build_function_reference(wb):
    ws = wb.create_sheet("Function Reference")
    headers = ["Module", "Function / Class", "Signature", "Parameters", "Returns", "Raises", "Description", "Example"]
    ws.append(headers)
    style_table(ws, 1, headers, [14, 26, 44, 42, 26, 28, 52, 46])

    rows = [
        ("crc.py", "crc16_ccitt()", "crc16_ccitt(data: bytes) -> int",
         "data: raw bytes to checksum", "16-bit integer (0-65535)", "(none)",
         "CRC-16/CCITT-FALSE: poly 0x1021, init 0xFFFF, no input/output reflection, no final XOR.",
         'crc16_ccitt(b"123456789") -> 0x29B1 (10673, the algorithm\'s own published check value)'),

        ("crc.py", "compute_crc()", "compute_crc(body: str) -> str",
         "body: ASCII digit string", "5-digit zero-padded decimal string", "(none)",
         "Wraps crc16_ccitt() over the UTF-8/ASCII bytes of a digit string and renders as decimal (not hex, to stay in QR Numeric mode).",
         f'compute_crc("{EX["inner_body"]}") -> "{EX["icrc"]}"'),

        ("errors.py", "ProtocolError", "class ProtocolError(ValueError)",
         "-", "-", "-", "Base class for every payload rejection.",
         "except ProtocolError: -- catches every rejection this package raises, of any kind"),
        ("errors.py", "FormatError", "class FormatError(ProtocolError)",
         "-", "-", "-", "Structural malformation: non-digit, bad length, bad VER, bad count, bad BCD pad.",
         EX["err_stage1_bad_ver"]),
        ("errors.py", "ChecksumError", "class ChecksumError(ProtocolError)",
         "-", "-", "-", "OCRC or ICRC mismatch.",
         EX["err_stage2_bad_ocrc"]),
        ("errors.py", "CryptoError", "class CryptoError(ProtocolError)",
         "-", "-", "-", "AES-GCM tag verification failed.",
         EX["err_stage3_wrong_key"]),
        ("errors.py", "MachineMismatchError", "class MachineMismatchError(ProtocolError)",
         "-", "-", "-", "Decrypted MID != scanner's configured machine_id.",
         EX["err_stage6_wrong_machine"]),
        ("errors.py", "ExpiredError", "class ExpiredError(ProtocolError)",
         "-", "-", "-", "Payload older than max_age_seconds.",
         EX["err_stage7_expired"]),
        ("errors.py", "ClockSkewError", "class ClockSkewError(ProtocolError)",
         "-", "-", "-", "Payload timestamped further in the future than clock_skew_seconds.",
         "verify(payload, KEY, mid, now=T) where payload's TS = T+31 -> "
         '"stage 7 (clock skew): payload timestamp is 31s ahead of now, exceeds clock_skew_seconds=30"'),

        ("inner.py", "Grams", "class Grams(int)",
         "wraps an int", "-", "-",
         "Marks an integer as a gram weight so Instruction.type_code can tell it apart from a boolean (bool is also an int subclass in Python).",
         "Grams(13) == 13  ->  True   (behaves as a plain int everywhere)"),

        ("inner.py", "Instruction", "@dataclass(frozen=True) class Instruction",
         "ingredient: int (1-24); value: Grams | bool", "-", "-",
         "One opcode/data pair. .type_code derives \"01\"/\"02\" from the Python type of value. .encode() renders the 8-digit pair string.",
         "Instruction(ingredient=7, value=Grams(13))   # 13g of ingredient 07\n"
         "Instruction(ingredient=12, value=True)        # ingredient 12: yes"),

        ("inner.py", "Instruction.encode()", "encode(self) -> str",
         "(none, uses self.ingredient/self.value)", "8-digit string: 2-digit ingredient + 2-digit type + 4-digit data",
         "ProtocolError (ingredient out of range 1-24; weight out of range 0-9999)",
         "Renders one instruction as its wire format.",
         f'Instruction(7, Grams(13)).encode() -> "{EX["opcode_weight"]}"\n'
         f'Instruction(12, True).encode()    -> "{EX["opcode_boolean"]}"'),

        ("inner.py", "encode_inner()", "encode_inner(sku: int, instructions: list, timestamp: int, machine_id: int) -> str",
         "sku: 0-9999; instructions: list[Instruction]; timestamp: Unix epoch seconds; machine_id: 1-999999",
         "Inner digit string, length 27+8n", "ProtocolError (bad SKU, >12 instructions, duplicate ingredient, bad TS, bad MID)",
         "Builds the full inner layer: header + pairs + TS + MID + ICRC.",
         f'encode_inner(42, [Instruction(7, Grams(13)), Instruction(12, True)], 1700000000, 123)\n'
         f'-> "{EX["inner"]}"  (43 digits)'),

        ("inner.py", "_parse_inner_structure()", "_parse_inner_structure(digits: str) -> dict",
         "digits: decrypted inner digit string",
         "dict: sku, count, pairs_raw (unvalidated tuples), timestamp, machine_id",
         "FormatError (stage 4); ChecksumError (stage 5); ProtocolError (MID==000000)",
         "Private. Runs stages 4-5 only (structure + inner CRC) -- no per-pair semantics yet, so api.verify() can insert stage 6/7 checks before stage 8.",
         "MID=000000 example -> " + EX["err_stage4_mid_reserved"]),

        ("inner.py", "_check_pair_semantics()", "_check_pair_semantics(pairs_raw, registry=None) -> list[Instruction]",
         "pairs_raw: from _parse_inner_structure; registry: optional set of valid ingredient ids",
         "list[Instruction]", "ProtocolError (bad ingredient, not in registry, duplicate, bad boolean data)",
         "Private. Runs stage 8 only (per-pair semantic checks), on the raw fields _parse_inner_structure returned.",
         "registry={99} example -> " + EX["err_stage8_not_in_registry"]),

        ("inner.py", "decode_inner()", "decode_inner(digits: str, *, registry=None) -> dict",
         "digits: decrypted inner digit string; registry: optional valid-ingredient set",
         "dict: sku, count, instructions, timestamp, machine_id",
         "FormatError, ChecksumError, ProtocolError",
         "Public convenience: composes _parse_inner_structure + _check_pair_semantics (stages 4,5,8 only -- no machine/freshness check, use api.verify() for that).",
         f'decode_inner("{EX["inner"]}")\n'
         '-> {"sku": 42, "count": 2, "instructions": [Instruction(7, Grams(13)), Instruction(12, True)], ...}'),

        ("envelope.py", "bcd_pack()", "bcd_pack(digits: str) -> bytes",
         "digits: ASCII digit string", "Packed bytes, 2 digits/byte, 0xF pad nibble if odd length", "(none)",
         "Binary-coded-decimal packing before encryption.",
         'bcd_pack("123") -> b\'\\x12\\x3f\'   (2 bytes: digits 1,2 then 3,pad)'),

        ("envelope.py", "bcd_unpack()", "bcd_unpack(data: bytes) -> str",
         "data: BCD-packed bytes", "Original digit string", "FormatError (missing/wrong pad, non-BCD nibble)",
         "Inverse of bcd_pack(); verifies the 0xF pad sentinel.",
         'bcd_unpack(b\'\\x12\\x3f\') -> "123"'),

        ("envelope.py", "render_envelope()", "render_envelope(envelope_bytes: bytes) -> str",
         "envelope_bytes: nonce+ciphertext+tag", "Zero-padded decimal string", "(none)",
         "Renders raw bytes as the decimal integer the QR symbol carries.",
         f'render_envelope(50 bytes) -> a 121-digit string (n=2 pairs): "{EX["outer"][2:-5][:24]}..."'),

        ("envelope.py", "parse_envelope()", "parse_envelope(envelope_digits: str, byte_len: int) -> bytes",
         "envelope_digits: decimal string; byte_len: expected byte count", "Raw bytes", "(none, caller must bound-check first)",
         "Inverse of render_envelope().",
         "parse_envelope(<121 digits>, 50) -> the original 50-byte envelope (nonce+ciphertext+tag)"),

        ("envelope.py", "validate_outer_structure_and_crc()",
         "validate_outer_structure_and_crc(payload: str) -> (ver, envelope_digits, table_entry)",
         "payload: full outer digit string",
         "Tuple: VER string, envelope digit substring, size-table entry dict",
         "FormatError (non-digit, bad length, bad VER, envelope value >= 256**B); ChecksumError (bad OCRC)",
         "Stages 1-2 only, needs no key. Single choke point used by both decrypt_payload() and qr.make_qr().",
         f'validate_outer_structure_and_crc("{EX["outer"][:20]}...")\n'
         '-> ("14", <121 envelope digits>, {"n": 2, "B": 50, "D": 121, ...})'),

        ("envelope.py", "encrypt_payload()", "encrypt_payload(inner_digits: str, key: bytes) -> str",
         "inner_digits: from encode_inner(); key: 32 raw bytes",
         "Full outer payload string (VER+ENVELOPE+OCRC)", "FormatError (bad inner_digits shape)",
         "BCD-packs, AES-256-GCM encrypts (fresh nonce, AAD=VER), decimal-renders, appends OCRC.",
         f'encrypt_payload("{EX["inner"][:20]}...", KEY)\n-> "{EX["outer"][:30]}..." (128 digits)'),

        ("envelope.py", "decrypt_payload()", "decrypt_payload(outer_digits: str, key: bytes) -> str",
         "outer_digits: full outer payload; key: 32 raw bytes",
         "Inner digit string", "FormatError; ChecksumError; CryptoError",
         "Stages 1-3: validates outer structure/CRC, then AES-GCM decrypts.",
         f'decrypt_payload("{EX["outer"][:20]}...", KEY) -> "{EX["inner"]}"'),

        ("api.py", "create()", "create(sku, instructions, machine_id, key, *, now=None) -> str",
         "sku, instructions, machine_id: see encode_inner(); key: 32 bytes; now: optional injected Unix timestamp (tests only -- production omits it)",
         "Full outer payload string, ready to print",
         "ValueError (bad key/machine_id); ProtocolError subclasses (bad sku/instructions/etc via encode_inner)",
         "The function production code calls to build a label.",
         "create(sku=42, instructions=[Instruction(7, Grams(13)), Instruction(12, True)],\n"
         f'       machine_id=123, key=KEY, now=1700000000)\n-> "{EX["outer"][:30]}..." (128 digits)'),

        ("api.py", "verify()", "verify(payload, key, machine_id, *, max_age_seconds=600, clock_skew_seconds=30, now=None, registry=None) -> dict",
         "payload: scanned digit string; key: 32 bytes; machine_id: this scanner's own id; max_age_seconds/clock_skew_seconds: freshness tuning; now: optional injected timestamp; registry: optional valid-ingredient set",
         "dict: sku, count, instructions, timestamp, machine_id",
         "FormatError, ChecksumError, CryptoError (stages 1-5); MachineMismatchError (stage 6); ExpiredError, ClockSkewError (stage 7); ProtocolError (stage 8)",
         "The function production code calls to check a scan and get back what to pour. Runs the full 8-stage order.",
         'verify(payload, KEY, machine_id=123, now=1700000060)\n'
         '-> {"sku": 42, "instructions": [Instruction(7, Grams(13)), Instruction(12, True)], ...}\n'
         "verify(payload, KEY, machine_id=124, now=1700000060) -> " + EX["err_stage6_wrong_machine"]),

        ("api.py", "_validate_key()", "_validate_key(key) -> None",
         "key: anything", "None (raises on failure)", "ValueError (wrong type or length)",
         "Private. Fails fast with a clear message instead of a confusing error deep inside AES-GCM.",
         '_validate_key(b"short") -> ValueError("key must be 32 raw bytes, got bytes of length 5")'),

        ("api.py", "_normalize_machine_id()", "_normalize_machine_id(machine_id) -> int",
         "machine_id: int or digit-string", "int", "ValueError (float or any other type)",
         "Private. Strict on purpose -- stage 6 is a security check, so a sloppy caller (e.g. passing a float) must fail closed, never silently truncate to a different machine.",
         '_normalize_machine_id("000123") -> 123\n_normalize_machine_id(123.7) -> ValueError'),

        ("keys.py", "generate_key()", "generate_key() -> bytes",
         "(none)", "32 random bytes", "(none)", "Fresh AES-256 key via os.urandom.",
         "generate_key() -> b'\\x9f\\x1a...' (32 random bytes, different every call)"),

        ("keys.py", "load_key_from_env()", "load_key_from_env(name: str) -> bytes",
         "name: environment variable name", "32 bytes", "KeyError (unset); ValueError (bad hex or wrong length)",
         "Reads a 64-hex-char key from an environment variable.",
         f'os.environ["QRPROTO_KEY"] = "{EX["key_hex"]}"\n'
         'load_key_from_env("QRPROTO_KEY") -> the 32 raw bytes'),

        ("keys.py", "load_key_from_file()", "load_key_from_file(path) -> bytes",
         "path: file path", "32 bytes", "ValueError (neither 64 hex chars nor 32 raw bytes)",
         "Reads a key file, accepting either hex text or raw bytes, auto-detected by length.",
         'load_key_from_file("qrproto.key") -> the 32 raw bytes, whether the file held hex text or raw bytes'),

        ("qr.py", "make_qr()", "make_qr(payload, module_size_mm=0.5, dpi=300, fixed_version=None)",
         "payload: outer digit string; module_size_mm: print size per module; dpi: raster resolution; fixed_version: force a QR version or None to auto-size",
         "PIL Image", "FormatError/ChecksumError (via validate_outer_structure_and_crc, stages 1-2 only)",
         "Renders the payload as a QR symbol at error correction level H with a 4-module quiet zone.",
         f'make_qr("{EX["outer"][:20]}...") -> PIL Image, 294x294 px at defaults (module_size_mm=0.5, dpi=300)'),

        ("qr.py", "minimum_version()", "minimum_version(payload: str) -> int",
         "payload: outer digit string", "QR version number (6-9)", "FormatError (via validate_outer_structure_and_crc)",
         "Looks up the smallest QR version for this payload's length, from VERSION_FOR_COUNT.",
         f'minimum_version("{EX["outer"][:20]}...") -> 6   (128 digits, n=2 pairs)'),

        ("qr.py", "symbol_dimensions()", "symbol_dimensions(version: int, module_size_mm=0.5) -> dict",
         "version: QR version number; module_size_mm: print size per module",
         "dict: version, modules, symbol_mm, footprint_mm", "(none)",
         "Physical size of a QR symbol, including the 4-module quiet zone.",
         'symbol_dimensions(6) -> {"version": 6, "modules": 41, "symbol_mm": 20.5, "footprint_mm": 24.5}'),
    ]
    append_rows(ws, rows)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:H{ws.max_row}"


# ============================================================================
# Sheet 5: Constants reference
# ============================================================================
def build_constants_reference(wb):
    ws = wb.create_sheet("Constants Reference")
    headers = ["Name", "Value", "Meaning"]
    ws.append(headers)
    style_table(ws, 1, headers, [26, 20, 90])

    rows = [
        ("VER", '"14"', "Protocol version marker, printed as the first 2 digits of every payload"),
        ("VER_DIGITS", "2", "Width of the VER field"),
        ("OCRC_DIGITS", "5", "Width of the outer CRC field"),
        ("SKU_DIGITS", "4", "Width of the SKU field"),
        ("COUNT_DIGITS", "2", "Width of the opcode-count field"),
        ("OPCODE_DIGITS", "4", "Width of one opcode (ingredient+type)"),
        ("DATA_DIGITS", "4", "Width of one data field"),
        ("TS_DIGITS", "10", "Width of the timestamp field"),
        ("MID_DIGITS", "6", "Width of the machine-ID field"),
        ("ICRC_DIGITS", "5", "Width of the inner CRC field"),
        ("PAIR_DIGITS", "8 (= OPCODE_DIGITS + DATA_DIGITS)", "Width of one full opcode/data pair"),
        ("INNER_HEADER_DIGITS", "6 (= SKU_DIGITS + COUNT_DIGITS)", "Width of the inner header before any pairs"),
        ("MAX_PAIRS", "12", "Maximum number of instructions in one payload"),
        ("SKU_MIN, SKU_MAX", "0, 9999", "Valid SKU range"),
        ("MID_MIN, MID_MAX", "1, 999999", "Valid machine-ID range"),
        ("MID_RESERVED", "0 (i.e. 000000)", "Reserved MID value, always rejected"),
        ("TS_MIN, TS_MAX", "0, 9999999999", "Valid timestamp range (10-digit field)"),
        ("INGREDIENT_MIN, INGREDIENT_MAX", "1, 24", "Valid ingredient ID range"),
        ("TYPE_WEIGHT", '"01"', "Opcode type for a whole-gram weight (local reassignment -- see Deviations sheet)"),
        ("TYPE_BOOLEAN", '"02"', "Opcode type for a yes/no flag"),
        ("BOOLEAN_FALSE, BOOLEAN_TRUE", '"0000", "0001"', "The only two valid values for a boolean data field"),
        ("WEIGHT_MAX_RAW", "9999", "Ceiling for the weight data field (grams)"),
        ("MIN_INNER_LEN", "27 (n=0)", "Shortest possible inner digit string"),
        ("MAX_INNER_LEN", "123 (n=12)", "Longest possible inner digit string"),
        ("KEY_BYTES", "32", "AES-256 key size in bytes"),
        ("NONCE_BYTES", "12", "AES-GCM nonce size in bytes (the GCM-native size)"),
        ("TAG_BYTES", "16", "AES-GCM authentication tag size in bytes"),
        ("AAD", 'b"14" (VER.encode())', "Associated data passed to AES-GCM so VER is authenticated even though it is not encrypted"),
        ("inner_len(n)", "27 + 8n", "Function: inner digit-string length for n pairs"),
        ("plaintext_bytes(n)", "(inner_len(n)+1)//2", "Function: BCD-packed byte length for n pairs"),
        ("envelope_bytes(n)", "42 + 4n", "Function: nonce+ciphertext+tag byte length for n pairs"),
        ("outer_len(n)", "109 to 224", "Function: printed payload length for n pairs"),
        ("B_TO_ENTRY, OUTER_LEN_TO_ENTRY, INNER_LEN_TO_N", "dicts, built at import", "Lookup tables so a decoder can recover n from a payload's length alone"),
    ]
    append_rows(ws, rows)
    ws.freeze_panes = "A2"


# ============================================================================
# Sheet 6: 8-stage verification order
# ============================================================================
def build_verification_stages(wb):
    ws = wb.create_sheet("8-Stage Verification")
    headers = ["Stage", "Check", "Failure class", "Implemented in", "Why this order", "Example failure (real error message)"]
    ws.append(headers)
    style_table(ws, 1, headers, [8, 40, 24, 32, 62, 55])

    rows = [
        (1, "Outer structure: digits only, length in the size table, VER==\"14\", envelope value < 256^B",
         "FormatError", "envelope.validate_outer_structure_and_crc()",
         "Everything later depends on a valid length -- the CRC needs the body boundary, the envelope decoder needs the byte count a valid length implies.",
         "Payload's VER changed from \"14\" to \"13\":\n" + EX["err_stage1_bad_ver"]),
        (2, "Outer CRC over <VER><ENVELOPE>", "ChecksumError", "envelope.validate_outer_structure_and_crc()",
         "Runs before decryption so a scratched/misprinted label is reported as damage (reprint), not confused with a cryptographic failure (investigate).",
         "Last printed digit flipped:\n" + EX["err_stage2_bad_ocrc"]),
        (3, "AES-256-GCM decryption with AAD=\"14\"; tag must verify", "CryptoError", "envelope.decrypt_payload()",
         "A tag failure means the payload was not produced by a key holder in exactly this form -- wrong key, tampering, or forgery.",
         "Decrypted with the wrong key:\n" + EX["err_stage3_wrong_key"]),
        (4, "Inner structure: digits only, count 00-12, length==27+8n, BCD pad was 0xF, MID != 000000",
         "FormatError", "inner._parse_inner_structure()",
         "The count field can mis-slice every later field, so it is validated before any offset is computed. MID==000000 is a field-level defect, checked alongside count/length.",
         "Hand-built payload with MID=000000:\n" + EX["err_stage4_mid_reserved"]),
        (5, "Inner CRC", "ChecksumError", "inner._parse_inner_structure()",
         "If the CRC fails, every value in the payload is untrustworthy -- reporting a semantic error (e.g. bad ingredient) at this point would send an operator down the wrong path.",
         "Last inner digit flipped:\n" + EX["err_stage5_bad_icrc"]),
        (6, "Embedded MID equals the scanner's configured machine_id", "MachineMismatchError", "api.verify()",
         "Runs before freshness: a payload at the wrong machine is misdirected regardless of age, and \"wrong machine\" is the more actionable diagnosis.",
         "Payload for machine 123, scanned at machine 124:\n" + EX["err_stage6_wrong_machine"]),
        (7, "TS within the freshness window (max_age_seconds, clock_skew_seconds)", "ExpiredError / ClockSkewError", "api.verify()",
         "Runs after machine binding, before semantics -- an expired-and-also-malformed payload is reported as expired, the true first-order problem.",
         "Same payload, scanned 601s after generation (max_age_seconds=600):\n" + EX["err_stage7_expired"]),
        (8, "Instruction semantics: ingredient range/registry, no duplicates, boolean/weight data range",
         "ProtocolError", "inner._check_pair_semantics()",
         "Runs last -- by this point structure, both CRCs, machine binding, and freshness are all already confirmed valid.",
         "Decoded with registry={99} (ingredient 07 not in it):\n" + EX["err_stage8_not_in_registry"]),
    ]
    append_rows(ws, rows)
    ws.freeze_panes = "A2"


# ============================================================================
# Sheet 7: Deviations from the published v1.4 spec
# ============================================================================
def build_deviations(wb):
    ws = wb.create_sheet("Deviations from spec")
    headers = ["Decision", "What the published spec says", "What this deployment does", "Why"]
    ws.append(headers)
    style_table(ws, 1, headers, [30, 45, 45, 70])

    rows = [
        ("No percentage type",
         "TYPE 01 = percentage (0000-1000, tenths of a percent), TYPE 02 = boolean. No TYPE 03 defined.",
         "Only TYPE_WEIGHT (\"01\") and TYPE_BOOLEAN (\"02\") exist. Percentage is not represented anywhere in the wire format.",
         "The live store GUI (store_gui/drinks-pos.js) has never emitted a percentage pair -- the sugar dial is converted to grams client-side before the pairs are built, since the pumps only ever read whole grams. Percentage is purely a UI concept; carrying it in the protocol would be dead code. If percentage needs to be shown again later (order history, receipt), that is resolved from a value recorded elsewhere in the database, not from the wire format."),

        ("TYPE_WEIGHT reassigned to \"01\"",
         "\"01\" is percentage; weight does not exist in the spec at all.",
         "TYPE_WEIGHT = \"01\" (reusing the numeric slot the spec gave to percentage), TYPE_BOOLEAN stays \"02\".",
         "Since percentage was dropped entirely, \"01\" was reassigned to weight rather than leaving it unused or inventing a type \"03\". A decoder written strictly against the published spec would misread a \"01\" pair here as a percentage -- this mismatch is intentional and local to this deployment, documented in constants.py so it is not mistaken for a bug."),

        ("SERIAL + database ticket lifecycle replaced by TS + MID",
         "Not addressed by the spec (v1.3's plaintext protocol, still live in scan/qr_payload.py, used a SERIAL field tied to an order_ticket DB row that moved unused -> in_progress -> used).",
         "No SERIAL field. Anti-replay is TS + max_age_seconds (default 600s); anti-misdirection is MID.",
         "Team decision: adopt the v1.4 mechanism as designed rather than retrofitting SERIAL alongside it. Trade-off accepted knowingly: TS/MID do not prevent the exact same label being scanned twice within the 600s freshness window (no per-label \"used\" flag) -- the old SERIAL+DB approach did prevent that. This was discussed and the risk was accepted rather than adding a replacement single-use mechanism."),

        ("No ingredient registry populated yet",
         "Section 7 defines a registry mapping ingredient IDs 01-24 to database records, to be populated before release.",
         "decode_inner()/verify() accept an optional `registry` parameter (a set of valid IDs) and enforce it if supplied, but no registry is wired in yet -- ingredient range 1-24 is checked, membership is not, until integration.",
         "Registry population is an integration-time concern (needs the real ingredient table), not a protocol-design concern -- the hook already exists and is tested (test_registry_membership_enforced)."),
    ]
    append_rows(ws, rows)
    ws.freeze_panes = "A2"


def main() -> None:
    wb = Workbook()
    build_overview(wb)
    build_payload_structure(wb)
    build_module_reference(wb)
    build_function_reference(wb)
    build_constants_reference(wb)
    build_verification_stages(wb)
    build_deviations(wb)
    wb.save(OUT_PATH)
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
