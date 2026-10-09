#!/usr/bin/env python3
"""HX711 fault classifier — tells hardware faults apart from software timing.

RUN WITH THE SERVICE STOPPED, it needs GPIO 4 and 18:
    sudo systemctl stop flexmix-backend
    ./.venv/bin/python hx711_diag.py            # 60s idle baseline
    ./.venv/bin/python hx711_diag.py --wiggle   # then flex the jack/cable
    ./.venv/bin/python hx711_diag.py --pump 1   # while pump 1 runs
    sudo systemctl start flexmix-backend

WHAT IT LOOKS FOR
    Each raw HX711 word is classified. The interesting buckets are not
    "noisy" -- they are exact fingerprints:

      raw == 0          DT line never went high while clocking. With
                        DigitalInputDevice(18) the internal PULL-DOWN is
                        on, so an OPEN data wire reads a clean 0 --
                        which the calibration turns into a large negative
                        weight, printed beside every sample rather than
                        written out here. Seeing this = broken DT contact.
      raw == -1         all ones: DT stuck high (shorted to 3V3, or the
                        chip is not driving and something pulls up).
      raw == -8388608   ADC pegged at the negative rail: the bridge input
                        is open or reversed (E+/E-/A+/A- contact lost).
      raw == 8388607    pegged positive: same class of fault, other sign.
      timeout           DT never went low: chip unpowered, in power-down,
                        or SCK stuck.

    It also measures the two software-timing risks in the current driver:
      * SCK high time. The HX711 datasheet powers the chip DOWN if PD_SCK
        stays high longer than 60us. Python + gpiozero has no guarantee
        against that, and a preemption mid-frame corrupts the word.
      * whether DT is sampled on the correct clock phase (the driver
        samples AFTER SCK.off(); this reports what sampling during the
        high phase would have given instead).
"""

from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
import time

from gpiozero import OutputDevice, DigitalInputDevice

from configuration.configuration import CALIBLOADCELL_FILE

SCK_PIN, DT_PIN = 4, 18
POWER_DOWN_US = 60.0        # HX711 datasheet: PD_SCK high > 60us = power down

# READ the calibration. Never keep a second copy of it.
#
# OFFSET and SCALE were literals right here, under a comment pointing at
# calib_loadcell.json. Re-run init_loadcell.py and the two drift apart --
# silently, because nothing compares them. This tool then reports the wrong
# grams at exactly the moment somebody is trusting it to tell a hardware
# fault from a software one.
#
# Read from the JSON rather than importing loadcell.loadcell, for two
# reasons: load_calibration() assigns into that module's globals instead of
# returning anything, and -- the one that matters -- this is the tool that
# diagnoses that driver. An instrument that will not start because the
# thing it measures is broken is not an instrument.
#
# Done before the pins are claimed below, so a missing calibration exits
# without leaving GPIO 4 and 18 held.
try:
    with open(CALIBLOADCELL_FILE, encoding="utf-8") as handle:
        _calibration = json.load(handle)

    OFFSET = float(_calibration["offset"])
    SCALE = float(_calibration["scale"])
except (OSError, ValueError, KeyError) as error:
    sys.exit(f"Khong doc duoc hieu chuan tu {CALIBLOADCELL_FILE}: {error}\n"
             f"Hay chay loadcell/init_loadcell.py truoc.")

sck = OutputDevice(SCK_PIN)
dt = DigitalInputDevice(DT_PIN)
sck.off()


def read_instrumented(timeout_s: float = 0.25):
    """One HX711 word, plus timing and both clock-phase samples.

    Returns (raw_late, raw_early, max_sck_high_us, waited_s) or None on
    timeout. raw_late is what loadcell.py computes today (sampled after
    the falling edge); raw_early is the same frame sampled while SCK is
    still high. If those two disagree systematically the driver is
    latching the wrong clock phase.
    """
    t0 = time.perf_counter()
    deadline = t0 + timeout_s
    while dt.value == 1:
        if time.perf_counter() > deadline:
            return None
        time.sleep(0.0001)
    waited = time.perf_counter() - t0

    late = early = 0
    worst_high_ns = 0
    for _ in range(24):
        t_on = time.perf_counter_ns()
        sck.on()
        bit_high = 1 if dt.value else 0          # sampled during high phase
        sck.off()
        t_off = time.perf_counter_ns()
        worst_high_ns = max(worst_high_ns, t_off - t_on)
        bit_low = 1 if dt.value else 0           # sampled after falling edge
        early = (early << 1) | bit_high
        late = (late << 1) | bit_low

    sck.on()
    sck.off()

    def signed(v: int) -> int:
        return v - 0x1000000 if v & 0x800000 else v

    return signed(late), signed(early), worst_high_ns / 1000.0, waited


def classify(raw: int) -> str:
    if raw == 0:
        return "ZERO (DT open -> pull-down; = -399.4 g)"
    if raw == -1:
        return "ALL-ONES (DT stuck high)"
    if raw == -0x800000:
        return "RAIL- (bridge input open/reversed)"
    if raw == 0x7FFFFF:
        return "RAIL+ (bridge input open/reversed)"
    if abs(raw) > 4_000_000:
        return "NEAR-RAIL (input way out of range)"
    return "ok"


def undervoltage() -> str:
    """Pi's sticky-ish low-voltage flag, read straight from hwmon."""
    import glob
    for h in glob.glob("/sys/class/hwmon/hwmon*"):
        try:
            if open(f"{h}/name").read().strip() != "rpi_volt":
                continue
            return open(f"{h}/in0_lcrit_alarm").read().strip()
        except OSError:
            pass
    return "?"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--pump", type=int, help="run this pump during the test")
    ap.add_argument("--wiggle", action="store_true",
                    help="prompt you to flex the connector while sampling")
    args = ap.parse_args()

    pump = None
    if args.pump:
        from gpiozero import PWMLED
        pins = {1: 26, 2: 15, 3: 21, 4: 20, 5: 16,
                6: 12, 7: 13, 8: 6, 9: 5, 10: 14}
        pump = PWMLED(pins[args.pump], frequency=1000)

    if args.wiggle:
        print("Flex the load-cell jack, the GPIO header end, and each of the\n"
              "four bridge wires in turn while this runs.\n")
        input("Enter to start... ")

    print(f"undervoltage flag at start: {undervoltage()}")
    if pump:
        print(f"pump {args.pump} ON")
        pump.value = 1.0

    buckets: collections.Counter[str] = collections.Counter()
    grams: list[float] = []
    high_us: list[float] = []
    phase_disagree = 0
    bit0_eq_bit1 = 0
    total = 0
    worst_negative = 0.0
    end = time.time() + args.seconds

    try:
        while time.time() < end:
            r = read_instrumented()
            total += 1
            if r is None:
                buckets["TIMEOUT (no DATA-READY: unpowered/power-down)"] += 1
                continue
            late, early, hi_us, _ = r
            high_us.append(hi_us)
            kind = classify(late)
            buckets[kind] += 1
            if late != early:
                phase_disagree += 1
            if (late & 1) == ((late >> 1) & 1):
                bit0_eq_bit1 += 1
            g = (late - OFFSET) / SCALE
            grams.append(g)
            worst_negative = min(worst_negative, g)
            print(f"\r  raw={late:>9d}  {g:9.2f} g   SCKhigh={hi_us:6.1f}us  "
                  f"{kind:<44s}", end="", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        if pump:
            pump.off()

    print("\n\n" + "=" * 68)
    print(f"samples: {total}    undervoltage flag now: {undervoltage()}")
    print("-" * 68)
    for kind, n in buckets.most_common():
        print(f"  {n:6d}  {100*n/max(total,1):5.1f}%  {kind}")

    if grams:
        print("-" * 68)
        print(f"  grams  median {statistics.median(grams):8.2f}   "
              f"min {min(grams):8.2f}   max {max(grams):8.2f}")
        if len(grams) > 1:
            print(f"  stdev  {statistics.pstdev(grams):.3f} g "
                  f"(healthy settled scale: well under 1 g)")
        if worst_negative < -50:
            print(f"  !! saw {worst_negative:.1f} g -- not sensor noise, "
                  f"that is a lost signal path")

    if high_us:
        over = sum(1 for h in high_us if h > POWER_DOWN_US)
        print("-" * 68)
        print(f"  SCK high time: median {statistics.median(high_us):.1f}us  "
              f"max {max(high_us):.1f}us")
        print(f"  pulses over the {POWER_DOWN_US:.0f}us power-down limit: "
              f"{over} of {len(high_us)} frames"
              + ("   <-- chip is being reset mid-read" if over else "   (ok)"))

    if total:
        print("-" * 68)
        print(f"  clock-phase check: {phase_disagree}/{total} frames differ "
              f"between high-phase and post-falling-edge sampling")
        print(f"  bit0==bit1 in {bit0_eq_bit1}/{len(grams)} frames "
              f"(~50% is normal; ~100% means the driver is off by one bit)")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())
