"""Build and validate QR payloads: protocol v1.3 plus a serial number.

WHAT THIS FILE IS
    An implementation of the numeric payload format described in
    "QR CODE PAYLOAD PROTOCOL v1.3" (Flexxource, 23 July 2026), extended
    with a serial field. It has no third-party dependencies and knows
    nothing about the database -- it only turns a SKU, a serial and a list
    of instructions into a digit string and back.

    store_gui/drinks-pos.js encodes the same format in JavaScript for the
    customer's order; order/qr_to_recipe.py decodes whatever was scanned.

THE PAYLOAD LAYOUT
    <SKU:4><SERIAL:6><COUNT:2><OP1:4><D1:4> ... <OPn:4><Dn:4><CRC:5>

    where each opcode is <INGREDIENT:2><TYPE:2>, 0 <= n <= 12, and the
    total length is exactly 17 + 8n digits (17 minimum, 113 maximum).
    Digits only -- no delimiters, no whitespace -- so the QR encoder can
    use Numeric mode at 3.33 bits per character instead of Byte mode at 8.

    TYPE 01  PERCENTAGE  data is tenths of a percent, 0000-1000
    TYPE 02  BOOLEAN     data is 0000 (no) or 0001 (yes)
    TYPE 03  WEIGHT      data is whole grams, 0000-9999

THE SERIAL, AND WHY IT IS NOT ENOUGH ON ITS OWN
    Two customers ordering the same drink the same way used to produce
    byte-identical payloads, so one printed label could be photographed
    and redeemed forever. The serial makes every label distinct.

    But distinct is not the same as single-use: the digits alone can never
    say whether they have been redeemed, because paper does not change
    when it is scanned. The serial is only a key. What makes a label
    single-use is the order_ticket row it points at, which moves
    unused -> in_progress -> used -- see the table's comment in
    database/database.sql, and the claim in order/qr_to_recipe.py.

    SERIAL_NONE (000000) is the deliberate exception: a well-formed
    payload that no ticket will ever match. scan/generate_drink_qr.py uses
    it for menu and reference labels, so those decode and print and can be
    checked by eye, but pour nothing if anybody scans one.

    Six digits gives 999,999 tickets. If that is ever widened, use 7 or 9
    digits -- NOT 8, which would make the new length rule collide with
    v1.3's own and destroy the property below.

WHY OLD LABELS FAIL CLEANLY RATHER THAN QUIETLY
    A v1.3 payload is 11 + 8m digits; this one is 17 + 8n. Those two sets
    never intersect -- one is always 3 more than a multiple of 8, the
    other always 1 -- so a label printed before the serial existed is
    refused on the length rule alone, before any field is read out of it.
    It cannot be mis-sliced into a different but plausible drink. The
    self-test checks this for every combination of m and n.

TYPE 03 IS A LOCAL EXTENSION
    v1.3 of the specification defines only types 01 and 02. Type 03 is
    added here because a customer's choice has to reach the machine as an
    amount it can pour. Sugar is 50 g in the recipe and the customer picks
    25%, so the screen works out 13 g and sends that -- the machine reads
    grams and never multiplies anything.

    Section 7.6 anticipates exactly this ("a revision that changes only
    field semantics -- adding a type 03, say") and points out that the
    length rule will not catch it. The type-value check in section 7.3
    does: a scanner built against v1.3 rejects a type-03 payload outright
    rather than mis-reading it. That is the intended failure, but it does
    mean every scanner in the fleet must be updated before type-03 labels
    are printed.

    The data field is whole grams, not tenths. Digits then read directly
    as the gram figure on a printed label -- section 5.2 makes a point of
    payloads being debugged by eye -- and 9999 g is a ceiling no single
    ingredient in a drink will reach. The cost is that 37.5 g encodes as
    38, which is far below what the pumps or the load cell resolve.

THE FLOW OF ONE ENCODE
    encode() checks the SKU and serial ranges, the pair count, and that no
    ingredient appears twice; asks each Instruction to render its own 8
    digits; concatenates SKU + serial + count + pairs; then appends the CRC
    of that body. A payload is never produced in a state decode() would
    reject -- a bad label costs far more to find than an exception here.

THE FLOW OF ONE DECODE
    Validation runs in the order the specification mandates, and each
    stage must pass before the next is attempted:

        1. structure  length within 17-113, digits only, count 00-12,
                      and length exactly 17 + 8n for that count
        2. checksum   CRC recomputed over the first 12 + 8n characters
        3. semantics  per pair: ingredient range, registry, duplicates,
                      type value, and the data range for that type

    The order is not arbitrary. Offsets are all derived from the count, so
    a corrupt count would mis-slice every later field -- it has to be
    checked first. And semantics come last because if the CRC failed, every
    value read out of the payload is untrustworthy: "unknown ingredient 41"
    is usually a valid ingredient with a flipped digit, and reporting it as
    an ingredient problem sends whoever is debugging down the wrong path.

    Note what is NOT checked here: whether the serial has been used. That
    needs the database, and this file deliberately has no database. A
    payload that decodes is well-formed, not authorised.

    Any failure rejects the whole payload. Nothing is partially executed --
    a half-made drink is a fault nobody notices, while a refused scan is
    one everybody does.

RUNNING IT
    python3 -m scan.qr_payload --self-test    # spec test vectors + checks
    python3 -m scan.qr_payload --decode 004200001702070102501202000133707
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


if __package__ in {None, ""}:
    project_dir = str(Path(__file__).resolve().parent.parent)

    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)


# --- field widths (spec section 2.1, plus the local serial) ----------------
SKU_DIGITS = 4
SERIAL_DIGITS = 6                                # local extension
COUNT_DIGITS = 2
OPCODE_DIGITS = 4
DATA_DIGITS = 4
CRC_DIGITS = 5

PAIR_DIGITS = OPCODE_DIGITS + DATA_DIGITS        # 8
HEADER_DIGITS = SKU_DIGITS + SERIAL_DIGITS + COUNT_DIGITS           # 12

# Where the count sits. Named because it is now two fields in, and an
# off-by-one here mis-slices the whole payload rather than failing loudly.
COUNT_OFFSET = SKU_DIGITS + SERIAL_DIGITS        # 10

MAX_PAIRS = 12
MIN_LENGTH = HEADER_DIGITS + CRC_DIGITS          # 17
MAX_LENGTH = HEADER_DIGITS + MAX_PAIRS * PAIR_DIGITS + CRC_DIGITS   # 113

SKU_MIN = 0
SKU_MAX = 9999

SERIAL_MIN = 0
SERIAL_MAX = 999999

# The serial that means "this label was never a ticket". Well-formed, so it
# decodes and prints, but no order_ticket row will ever carry it -- see the
# module docstring.
SERIAL_NONE = 0

INGREDIENT_MIN = 1
INGREDIENT_MAX = 24

TYPE_PERCENTAGE = "01"
TYPE_BOOLEAN = "02"
TYPE_WEIGHT = "03"                               # local extension, see above

PERCENTAGE_MAX_RAW = 1000                        # 100.0%
BOOLEAN_FALSE = "0000"
BOOLEAN_TRUE = "0001"
WEIGHT_MAX_RAW = 9999                            # grams; the 4-digit ceiling

# Numeric-mode capacity at error correction level H, per ISO/IEC 18004 and
# spec section 4.2. Used to report which symbol a payload needs.
NUMERIC_CAPACITY_LEVEL_H = {
    1: 17, 2: 34, 3: 58, 4: 82, 5: 106, 6: 139, 7: 154,
}


class ProtocolError(ValueError):
    """Raised for any payload that violates the specification."""


class Grams(int):
    """A whole-gram weight, so a value carries its own protocol type.
    With three types the type subfield can no longer be worked out from a
    bare Python number -- 120 could be 120 g or 12.0%. Wrapping the weight
    settles it at the call site, where the author knows which they meant,
    instead of leaving encode() to guess. It still behaves as an int
    everywhere else: Grams(120) == 120.
    """

    def __repr__(self) -> str:
        return f"Grams({int(self)})"


class Percent(float):
    """A percentage, 0.0-100.0. The explicit counterpart to Grams.
    A plain float is still read as a percentage, which keeps the
    specification's own worked examples working unchanged, but saying
    Percent(25.0) makes the intent visible next to a Grams(120).
    """

    def __repr__(self) -> str:
        return f"Percent({float(self)})"


def crc16_ccitt(data: bytes) -> int:
    """CRC-16/CCITT-FALSE over raw bytes. Returns a 16-bit integer.
    Polynomial 0x1021, initial value 0xFFFF, no input or output
    reflection, no final XOR (spec section 5.1).
    """
    crc = 0xFFFF

    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF

    return crc


def compute_crc(body: str) -> str:
    """Return the 5-digit decimal checksum for a payload body.
    The CRC is taken over the ASCII bytes of the digit string itself, not
    over a binary packing of the field values, so anyone holding the
    printed digits can verify it by hand. Rendered as decimal rather than
    hex because A-F would force the QR encoder out of Numeric mode.
    """
    return f"{crc16_ccitt(body.encode('ascii')):05d}"


@dataclass(frozen=True)
class Instruction:
    """One opcode/data pair.
    ingredient : 1-24, the database ingredient identifier
    value      : Grams for a weight, bool for a flag, or a float (or
                 Percent) for a percentage
    """

    ingredient: int
    value: float | bool | Grams | Percent

    @property
    def type_code(self) -> str:
        """The two-digit type subfield implied by the value's Python type.

        Order matters twice over. bool subclasses int, so True would
        otherwise be taken for a number; and Grams subclasses int too, so
        it has to be recognised before the plain-number fallback.
        """
        if isinstance(self.value, bool):
            return TYPE_BOOLEAN
        if isinstance(self.value, Grams):
            return TYPE_WEIGHT
        return TYPE_PERCENTAGE

    def encode(self) -> str:
        """Render this pair as its 8 digits: ingredient, type, then data."""
        if not INGREDIENT_MIN <= self.ingredient <= INGREDIENT_MAX:
            raise ProtocolError(
                f"ingredient {self.ingredient} outside range "
                f"{INGREDIENT_MIN}-{INGREDIENT_MAX}"
            )

        opcode = f"{self.ingredient:02d}{self.type_code}"

        if isinstance(self.value, bool):
            return opcode + (BOOLEAN_TRUE if self.value else BOOLEAN_FALSE)

        if isinstance(self.value, Grams):
            raw = int(self.value)
            if not 0 <= raw <= WEIGHT_MAX_RAW:
                raise ProtocolError(
                    f"weight {raw} g outside range 0-{WEIGHT_MAX_RAW} g"
                )
            return opcode + f"{raw:04d}"

        raw = round(self.value * 10)

        if not 0 <= raw <= PERCENTAGE_MAX_RAW:
            raise ProtocolError(
                f"percentage {self.value} outside range 0.0-100.0"
            )

        return opcode + f"{raw:04d}"


def encode(sku: int, serial: int, instructions: list[Instruction]) -> str:
    """Build a complete payload from a SKU, a serial and its instructions.

    `serial` has no default on purpose. It is the difference between a
    label that can buy a drink and one that cannot, so every caller has to
    say which it is making -- pass SERIAL_NONE for a menu or test label.

    Duplicates are rejected here as well as in decode(), so a payload that
    would fail validation is never printed onto a label in the first place.
    """
    if not SKU_MIN <= sku <= SKU_MAX:
        raise ProtocolError(
            f"SKU {sku} outside range {SKU_MIN:04d}-{SKU_MAX}"
        )

    if not SERIAL_MIN <= serial <= SERIAL_MAX:
        raise ProtocolError(
            f"serial {serial} outside range {SERIAL_MIN:06d}-{SERIAL_MAX}"
        )

    if len(instructions) > MAX_PAIRS:
        raise ProtocolError(
            f"{len(instructions)} instructions exceeds maximum {MAX_PAIRS}"
        )

    seen: set[int] = set()

    for instruction in instructions:
        if instruction.ingredient in seen:
            raise ProtocolError(
                f"duplicate ingredient {instruction.ingredient:02d}"
            )
        seen.add(instruction.ingredient)

    body = f"{sku:04d}{serial:06d}{len(instructions):02d}"
    body += "".join(item.encode() for item in instructions)

    return body + compute_crc(body)


def decode(payload: str, registry: set[int] | None = None) -> dict:
    """Parse and fully validate a payload.

    Raises ProtocolError on the first violation found, in the order the
    specification mandates: structure, then checksum, then semantics.
    Pass a set of valid ingredient numbers as `registry` to also enforce
    the registry check from section 7.3.
    """
    # --- stage 1: structure, before any offset arithmetic ------------------
    if not MIN_LENGTH <= len(payload) <= MAX_LENGTH:
        raise ProtocolError(
            f"length {len(payload)} outside valid range "
            f"{MIN_LENGTH}-{MAX_LENGTH}"
        )

    if not payload.isdigit():
        raise ProtocolError("payload must contain digits only")

    count = int(payload[COUNT_OFFSET:HEADER_DIGITS])

    if count > MAX_PAIRS:
        raise ProtocolError(f"count {count:02d} exceeds maximum {MAX_PAIRS}")

    expected_length = MIN_LENGTH + PAIR_DIGITS * count

    if len(payload) != expected_length:
        raise ProtocolError(
            f"count {count:02d} implies {expected_length} digits, "
            f"got {len(payload)}"
        )

    # --- stage 2: checksum, its boundary taken from the count -------------
    split = HEADER_DIGITS + PAIR_DIGITS * count
    body, checksum = payload[:split], payload[split:]
    expected_crc = compute_crc(body)

    if checksum != expected_crc:
        raise ProtocolError(
            f"CRC mismatch: got {checksum}, expected {expected_crc}"
        )

    # --- stage 3: semantics, one pair at a time ---------------------------
    instructions: list[Instruction] = []
    seen: set[int] = set()

    for index in range(count):
        base = HEADER_DIGITS + index * PAIR_DIGITS
        ingredient_text = body[base:base + 2]
        type_code = body[base + 2:base + 4]
        data = body[base + 4:base + 8]
        pair = index + 1

        ingredient = int(ingredient_text)

        if not INGREDIENT_MIN <= ingredient <= INGREDIENT_MAX:
            raise ProtocolError(
                f"pair {pair}: ingredient {ingredient_text} outside range "
                f"{INGREDIENT_MIN:02d}-{INGREDIENT_MAX:02d}"
            )

        if registry is not None and ingredient not in registry:
            raise ProtocolError(
                f"pair {pair}: ingredient {ingredient_text} not in registry"
            )

        if ingredient in seen:
            raise ProtocolError(
                f"pair {pair}: duplicate ingredient {ingredient_text}"
            )

        seen.add(ingredient)

        if type_code == TYPE_PERCENTAGE:
            raw = int(data)
            if raw > PERCENTAGE_MAX_RAW:
                raise ProtocolError(
                    f"pair {pair}: percentage {data} exceeds "
                    f"{PERCENTAGE_MAX_RAW}"
                )
            value: float | bool | Grams = Percent(raw / 10.0)
        elif type_code == TYPE_WEIGHT:
            # Every 4-digit value is a legal weight, so there is no upper
            # bound to check here -- 9999 is the field's own ceiling.
            value = Grams(int(data))
        elif type_code == TYPE_BOOLEAN:
            if data not in (BOOLEAN_FALSE, BOOLEAN_TRUE):
                raise ProtocolError(
                    f"pair {pair}: boolean must be {BOOLEAN_FALSE} or "
                    f"{BOOLEAN_TRUE}, got {data}"
                )
            value = data == BOOLEAN_TRUE
        else:
            raise ProtocolError(f"pair {pair}: unknown type {type_code}")

        instructions.append(Instruction(ingredient=ingredient, value=value))

    return {
        "sku": int(body[:SKU_DIGITS]),
        "serial": int(body[SKU_DIGITS:COUNT_OFFSET]),
        "count": count,
        "instructions": instructions,
    }


def peek_serial(payload: str) -> int | None:
    """Read the serial out of a payload without validating the rest.

    Returns None if the digits are not there to read.

    decode() is the right way to read a payload and this is not a
    substitute for it -- nothing may act on this value. It exists for
    logging a payload that decode() REFUSED: at that moment the serial is
    the one thing that identifies which label the customer is holding, and
    demanding a valid CRC before recording it would mean the codes most
    worth investigating are the ones logged with nothing to identify them.
    """
    if not isinstance(payload, str):
        return None

    field = payload[SKU_DIGITS:COUNT_OFFSET]

    if len(field) != SERIAL_DIGITS or not field.isdigit():
        return None

    return int(field)


def minimum_version(payload: str) -> int:
    """Smallest QR symbol version holding this payload at level H.

    Assumes the encoder picks Numeric mode, which it will for an all-digit
    payload. An encoder that chose Byte mode would need a larger symbol
    than this reports.
    """
    for version, capacity in sorted(NUMERIC_CAPACITY_LEVEL_H.items()):
        if len(payload) <= capacity:
            return version

    raise ProtocolError(f"payload of {len(payload)} digits exceeds the table")


def symbol_dimensions(version: int, module_size_mm: float = 0.5) -> dict:
    """Printed size of a symbol version, including the 4-module quiet zone."""
    modules = 4 * version + 17

    return {
        "version": version,
        "modules": modules,
        "symbol_mm": modules * module_size_mm,
        "footprint_mm": (modules + 8) * module_size_mm,
    }


def self_test() -> int:
    """Check this implementation against the specification. Returns 0 if ok.

    Covers the three CRC test vectors in section 5.5, both worked examples
    in section 8, the local type-03 extension, and one rejection per rule
    in section 7.3.
    """
    failures: list[str] = []

    def check(label: str, got, want) -> None:
        if got == want:
            print(f"  ok    {label}")
        else:
            print(f"  FAIL  {label}: got {got!r}, want {want!r}")
            failures.append(label)

    def rejects(label: str, payload: str) -> None:
        try:
            decode(payload)
        except ProtocolError as error:
            print(f"  ok    {label}  -> {error}")
        else:
            print(f"  FAIL  {label}: accepted, should have been rejected")
            failures.append(label)

    print("Section 5.5 -- CRC test vectors")
    # These check the CRC function itself against the published vectors.
    # They are strings, not payloads, so they stay valid even though the
    # body they were taken from is no longer a shape encode() produces.
    check("empty payload  crc", compute_crc("004200"), "21353")
    check("two pairs      crc",
          compute_crc("0042020701025012020001"), "47961")

    full_body = "004212" + "".join(
        f"{i:02d}01{i * 10:04d}" for i in range(1, 13)
    )
    check("full payload   crc", compute_crc(full_body), "10455")

    print("\nThe serial field")
    a = encode(42, 1, [Instruction(7, 25.0)])
    b = encode(42, 2, [Instruction(7, 25.0)])
    check("same order, different serial -> different payload", a != b, True)
    check("serial is at digits 4-9", a[4:10], "000001")
    check("serial survives round trip", decode(b)["serial"], 2)
    check("serial 999999 at the boundary",
          decode(encode(42, 999999, []))["serial"], 999999)
    check("SERIAL_NONE decodes as 0",
          decode(encode(42, SERIAL_NONE, []))["serial"], 0)
    check("sku still reads correctly past the serial", decode(a)["sku"], 42)

    for bad in (-1, 1000000):
        try:
            encode(42, bad, [])
        except ProtocolError as error:
            print(f"  ok    serial {bad} refused  -> {error}")
        else:
            check(f"serial {bad} refused", "accepted", "refused")

    print("\nOld v1.3 labels cannot be mistaken for new ones")
    # The whole point of 17+8n: no v1.3 length is ever a valid length here,
    # so a pre-serial label is refused before a single field is read.
    old_lengths = {11 + 8 * m for m in range(MAX_PAIRS + 1)}
    new_lengths = {MIN_LENGTH + 8 * n for n in range(MAX_PAIRS + 1)}
    check("the two length sets never overlap",
          sorted(old_lengths & new_lengths), [])
    rejects("v1.3 section 8.1 label", "004202070102501202000147961")
    rejects("v1.3 section 8.2 label", "00420021353")

    print("\nRound trip for every count 0-12")
    for count in range(MAX_PAIRS + 1):
        payload = encode(42, 7, [
            Instruction(ingredient=i, value=float(i))
            for i in range(1, count + 1)
        ])
        expected = MIN_LENGTH + PAIR_DIGITS * count
        parsed = decode(payload)
        if (len(payload) != expected or parsed["count"] != count
                or parsed["serial"] != 7):
            check(f"count {count:02d}", len(payload), expected)
    full = encode(42, 999999, [
        Instruction(ingredient=i, value=float(i)) for i in range(1, 13)
    ])
    check("count 12 is max length", len(full), MAX_LENGTH)
    check("count 12 needs version 6", minimum_version(full), 6)

    print("\nSymbol size the label printer will use")
    # Three options is what the busiest drink on the menu has, and 29x29 is
    # the symbol the current label size was chosen around. If this starts
    # failing, the printed code has outgrown the sticker.
    three = encode(9999, 999999, [
        Instruction(1, Grams(999)), Instruction(2, True), Instruction(3, 50.0),
    ])
    check("3 options, worst case", len(three), 41)
    check("3 options stay at version 3", minimum_version(three), 3)
    check("version 3 is 29x29", symbol_dimensions(3)["modules"], 29)
    check("5 options still fit version 3",
          minimum_version(encode(9999, 999999, [
              Instruction(i, Grams(999)) for i in range(1, 6)
          ])), 3)

    print("\nValue fidelity")

    def first(value) -> object:
        """Encode one instruction, decode it, and return the value back."""
        return decode(encode(1, 1, [Instruction(1, value)]))["instructions"][0].value

    check("33.3% survives round trip", first(33.3), 33.3)
    check("0.0% at the boundary", first(0.0), 0.0)
    check("100.0% at the boundary", first(100.0), 100.0)
    check("booleans decode as bool, not float",
          isinstance(first(True), bool), True)

    print("\nType 03 -- weight in whole grams")
    check("120 g renders as 0120",
          Instruction(1, Grams(120)).encode(), "01030120")
    check("a plain float is still a percentage",
          Instruction(1, 12.0).encode(), "01010120")
    check("Grams and float differ in the type subfield",
          Instruction(1, Grams(120)).encode()[2:4]
          != Instruction(1, 12.0).encode()[2:4],
          True)
    check("120 g survives round trip", first(Grams(120)), 120)
    check("weight decodes as Grams, not a percentage",
          isinstance(first(Grams(120)), Grams), True)
    check("0 g at the boundary", first(Grams(0)), 0)
    check("9999 g at the boundary", first(Grams(9999)), 9999)
    check("True is a boolean, never a weight",
          Instruction(1, True).encode()[2:4], TYPE_BOOLEAN)

    mixed = encode(42, 314159, [
        Instruction(1, Grams(120)),
        Instruction(7, Percent(25.0)),
        Instruction(12, True),
    ])
    parsed = decode(mixed)
    check("all three types in one payload",
          [i.value for i in parsed["instructions"]], [120, 25.0, True])
    check("serial reads back beside them", parsed["serial"], 314159)
    check("mixed payload length", len(mixed), MIN_LENGTH + 8 * 3)

    print("\nSection 7 -- rejections")

    def sealed(body: str) -> str:
        """Append the correct CRC, so only the flaw under test is wrong."""
        return body + compute_crc(body)

    one_pair = "0042" + "000001" + "01"          # sku, serial, count=1

    rejects("length below 17", "0042000001000")
    rejects("non-digit input", sealed("0042000001" + "00")[:-1] + "X")
    rejects("count above 12", "0042000001" + "13" + "0" * 96 + "00000")
    rejects("count disagrees with length", "0042000001" + "03" + "0701025000001")
    rejects("CRC mismatch", sealed("004200000100")[:-1] + "9")

    rejects("ingredient 00", sealed(one_pair + "0001" + "0100"))
    rejects("ingredient 25", sealed(one_pair + "2501" + "0100"))
    rejects("unknown type 04", sealed(one_pair + "0704" + "0100"))
    rejects("percentage 1001", sealed(one_pair + "0701" + "1001"))
    rejects("boolean 0007", sealed(one_pair + "0702" + "0007"))
    rejects("duplicate ingredient",
            sealed("0042" + "000001" + "02" + "07010100" + "07010200"))

    print()

    if failures:
        print(f"{len(failures)} CHECK(S) FAILED: {', '.join(failures)}")
        return 1

    print("All checks passed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for --self-test and --decode."""
    parser = argparse.ArgumentParser(
        description="QR Code Payload Protocol v1.3 encoder/decoder.",
    )
    parser.add_argument(
        "--self-test", action="store_true",
        help="Check this implementation against the specification.",
    )
    parser.add_argument(
        "--decode", metavar="PAYLOAD",
        help="Decode one payload and print what it contains.",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    if args.decode:
        try:
            parsed = decode(args.decode)
        except ProtocolError as error:
            print(f"REJECTED: {error}", file=sys.stderr)
            return 1

        version = minimum_version(args.decode)
        serial = parsed["serial"]
        print(f"sku      {parsed['sku']:04d}")
        print(f"serial   {serial:06d}"
              + ("   (SERIAL_NONE - not a ticket)" if serial == SERIAL_NONE
                 else ""))
        print(f"count    {parsed['count']:02d}")
        print(f"digits   {len(args.decode)}  (QR version {version} at level H)")
        for item in parsed["instructions"]:
            if isinstance(item.value, bool):
                kind, shown = "boolean   ", "yes" if item.value else "no"
            elif isinstance(item.value, Grams):
                kind, shown = "weight    ", f"{int(item.value)} g"
            else:
                kind, shown = "percentage", f"{float(item.value)}%"
            print(f"  ingredient {item.ingredient:02d}  {kind}  {shown}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
