"""End-to-end flow test: one realistic order walking through the whole
qrproto pipeline in the same order it happens for real -- the store
builds the order, the server creates the payload, the label is
rendered as a QR image, a scanner reads it back, and the decoded
instructions are checked against what the customer actually ordered.
Then the same label is replayed against three things that should
reject it: the wrong machine, an expired scan, and a scratched label.

WHY THIS FILE IS SEPARATE FROM test_qrproto.py
    test_qrproto.py checks one protocol rule at a time, with
    hand-crafted inputs -- it is deliberately narrow so a failure
    points at exactly one thing. This file instead tells one
    continuous story, step by step, the way an operator would
    describe it: "the customer orders, the label prints, the scanner
    reads it, the machine pours." Each step is still its own test
    function -- so `pytest -k` and individual node ids still work --
    but the steps share state through class attributes, and pytest
    runs methods inside a class in the order they are defined, so
    running the whole class reproduces the flow start to finish.

RUNNING IT

    Whole flow, in order, with every print() visible:

        ./.venv/bin/python3 -m pytest qrproto/tests/test_flow.py -v -s

    One step alone (later steps will fail/error if run without the
    earlier ones, since they depend on state those steps set):

        ./.venv/bin/python3 -m pytest \\
            "qrproto/tests/test_flow.py::TestOrderFlow::test_04_label_prints_as_qr" -v -s
"""

import tempfile
import time
from pathlib import Path

import pytest

from qrproto import create, verify
from qrproto.errors import ChecksumError, ExpiredError, MachineMismatchError
from qrproto.inner import Grams, Instruction
from qrproto.qr import make_qr, minimum_version

# The shared deployment key. A real deployment loads this from
# keys.load_key_from_env/_file; the flow test pins it so the story is
# reproducible.
DEPLOYMENT_KEY = bytes(range(32))

# The machine this label is printed for: line 1.
LINE_1_MACHINE_ID = 1
LINE_2_MACHINE_ID = 2

# SKU 15: "Tra sua tran chau" (milk tea with tapioca pearls).
DRINK_SKU = 15

# The instant the customer's order is placed, fixed so the story is
# reproducible instead of depending on the wall clock.
ORDER_PLACED_AT = 1_700_000_000


class TestOrderFlow:
    """One customer order, told as a sequence of steps."""

    # ------------------------------------------------------------------
    def test_01_store_builds_the_order(self):
        """STEP 1 -- the customer's choices become opcode/data pairs.

        Mirrors store_gui/drinks-pos.js: the sugar dial is a UI concept
        (the customer picked 25%), converted to a final weight in grams
        client-side BEFORE it becomes a pair -- the protocol never sees
        a percentage. The topping is sent as a plain yes/no.
        """
        sugar_baseline_g = 50
        customer_sugar_percent = 20
        sugar_grams = round(sugar_baseline_g * customer_sugar_percent / 100)

        order_instructions = [
            Instruction(ingredient=7, value=Grams(sugar_grams)),   # sugar: 10 g
            Instruction(ingredient=12, value=True),                # tapioca: yes
        ]

        print(f"\n[STEP 1] Customer ordered SKU {DRINK_SKU}: "
              f"sugar {customer_sugar_percent}% of {sugar_baseline_g}g "
              f"-> {sugar_grams}g, tapioca pearls: yes")

        assert sugar_grams == 10
        type(self).order_instructions = order_instructions

    # ------------------------------------------------------------------
    def test_02_server_creates_the_payload(self):
        """STEP 2 -- the server turns the order into an encrypted,
        signed, machine-bound QR payload, addressed to line 1."""
        payload = create(
            sku=DRINK_SKU,
            instructions=self.order_instructions,
            machine_id=LINE_1_MACHINE_ID,
            key=DEPLOYMENT_KEY,
            now=ORDER_PLACED_AT,
        )

        print(f"[STEP 2] Payload created for machine {LINE_1_MACHINE_ID:06d}: "
              f"{payload}\n         ({len(payload)} digits)")

        type(self).payload = payload

    # ------------------------------------------------------------------
    def test_03_payload_shape_is_valid(self):
        """STEP 3 -- sanity-check the printed string before it goes
        anywhere near a printer: right version marker, a length the QR
        version table actually accounts for."""
        payload = self.payload

        assert payload[:2] == "14", "VER marker must be present"
        version = minimum_version(payload)

        print(f"[STEP 3] Payload starts with VER=14, needs QR version {version}")

        type(self).qr_version = version

    # ------------------------------------------------------------------
    def test_04_label_prints_as_qr(self):
        """STEP 4 -- render the payload as an actual QR image, as the
        label printer would. Confirms make_qr() accepts this exact
        payload without complaint."""
        image = make_qr(self.payload)
        out_path = Path(tempfile.gettempdir()) / "qrproto_flow_label.png"
        image.save(out_path)

        print(f"[STEP 4] Label rendered: {image.size[0]}x{image.size[1]} px, "
              f"saved to {out_path}")

        assert out_path.exists()

    # ------------------------------------------------------------------
    def test_05_scanner_reads_and_verifies_at_line_1(self):
        """STEP 5 -- the customer walks the label to line 1 a minute
        later. The scanner (configured with machine_id=1) reads the
        digits straight off the symbol -- no camera/decoder needed
        here, since a real barcode scanner emits the ASCII digits
        directly, the same string that went into the QR -- and
        verifies it."""
        scanned_at = ORDER_PLACED_AT + 60          # a minute later

        result = verify(
            self.payload,
            key=DEPLOYMENT_KEY,
            machine_id=LINE_1_MACHINE_ID,
            now=scanned_at,
        )

        print(f"[STEP 5] Line 1 scanned the label {scanned_at - ORDER_PLACED_AT}s "
              f"after printing -> ACCEPTED")

        type(self).verified_result = result

    # ------------------------------------------------------------------
    def test_06_pour_instructions_match_the_order(self):
        """STEP 6 -- what the machine is about to pour must be exactly
        what the customer ordered in step 1, no more, no less."""
        poured = [(i.ingredient, i.value) for i in self.verified_result["instructions"]]
        ordered = [(i.ingredient, i.value) for i in self.order_instructions]

        print(f"[STEP 6] Ordered: {ordered}")
        print(f"         Poured:  {poured}")

        assert poured == ordered
        assert self.verified_result["sku"] == DRINK_SKU

    # ------------------------------------------------------------------
    def test_07_same_label_rejected_at_line_2(self):
        """STEP 7 -- the same physical label, shown to the WRONG
        machine. MID must stop this even though the label itself is
        perfectly valid."""
        with pytest.raises(MachineMismatchError) as excinfo:
            verify(
                self.payload,
                key=DEPLOYMENT_KEY,
                machine_id=LINE_2_MACHINE_ID,
                now=ORDER_PLACED_AT + 60,
            )

        print(f"[STEP 7] Line 2 scanned the same label -> REJECTED: {excinfo.value}")

    # ------------------------------------------------------------------
    def test_08_same_label_rejected_after_closing(self):
        """STEP 8 -- the same label, found on the floor and scanned
        the next morning (well past the 600s default freshness
        window). TS must stop this."""
        next_morning = ORDER_PLACED_AT + 12 * 3600  # 12 hours later

        with pytest.raises(ExpiredError) as excinfo:
            verify(
                self.payload,
                key=DEPLOYMENT_KEY,
                machine_id=LINE_1_MACHINE_ID,
                now=next_morning,
            )

        print(f"[STEP 8] Label rescanned {next_morning - ORDER_PLACED_AT}s later "
              f"-> REJECTED: {excinfo.value}")

    # ------------------------------------------------------------------
    def test_09_scratched_label_reported_as_damage_not_forgery(self):
        """STEP 9 -- the label got scuffed in a pocket: one printed
        digit misread. This must fail the OUTER CRC (label damage,
        "reprint it"), not reach decryption and fail as a crypto error
        (which would read as "someone tampered with this")."""
        scuffed = self.payload[:-1] + ("0" if self.payload[-1] != "0" else "1")

        with pytest.raises(ChecksumError) as excinfo:
            verify(scuffed, key=DEPLOYMENT_KEY, machine_id=LINE_1_MACHINE_ID,
                   now=ORDER_PLACED_AT + 60)

        print(f"[STEP 9] Scuffed label -> REJECTED as damage (not forgery): "
              f"{excinfo.value}")
