"""Prime every pump line, and report which ones did not deliver.

WHAT PRIMING IS FOR
    A tube that has stood overnight is full of air. The first order of the
    day would pour that air, come up short, and fail its weight check --
    with a customer waiting. Running each pump until liquid actually
    arrives moves that discovery to before opening, into a test cup.

HOW IT KNOWS A LINE IS PRIMED
    By weight, not by time. The cup sits on the load cell; the pump runs
    until the reading has risen PRIME_TARGET_GRAM above where it started.
    Weight is the only thing that distinguishes "the pump ran" from "the
    liquid arrived" -- a stalled pump, an empty container and a blocked
    line all look identical to a timer.

WHY EVERY PUMP HAS A DEADLINE
    Priming is exactly the case where the weight legitimately does not
    move: the tube is full of air and nothing lands for the first second
    or two. So "no change yet" cannot be treated as a fault, and a naive
    loop that waits for the weight to rise will wait for ever on a dry
    line -- with the pump running. At ~10 g/s that is a floor covered in
    syrup in under a minute.

    Every pump therefore gets a hard deadline worked out from its own
    calibration, plus an allowance for pushing the air out. Whichever
    comes first -- the target weight or the deadline -- stops the pump.

WHY A FAILED LINE DOES NOT STOP THE RUN
    The point of the exercise is to find out which lines are bad. Aborting
    on the first one tells you about that one and leaves the rest unknown,
    which is the least useful possible answer at the start of a day. Each
    pump is reported and the run continues.

WHAT IT REFUSES TO DO
    Run at all if the scale is not trustworthy. Every decision here rests
    on the load cell, so it is checked first: if the readings will not sit
    still, priming by weight is meaningless and a deadline is the only
    thing standing between a dry line and a flood. Better to say so than
    to pour ten pumps blind.

RUNNING IT
    python3 -m pump_control.prime_all           # every assigned line
    python3 -m pump_control.prime_all --pumps 1,4,5
    python3 -m pump_control.prime_all --check   # test the scale, pump nothing
    python3 -m pump_control.prime_all --gram 12 # a longer prime per line
"""

from __future__ import annotations

import argparse
import collections
import statistics
import sys
import time
from pathlib import Path
from typing import Any


if __package__ in {None, ""}:
    project_dir = str(Path(__file__).resolve().parent.parent)

    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

from gpiozero import PWMLED

from pump_control.gpio_lines import free_gpio_line

import loadcell.loadcell as lc
from loadcell.loadcell import WINDOW_SIZE, load_calibration, tare
from loadcell.loadcell_robust import read_weight_robust


# How much liquid must arrive before a line counts as primed. Enough to be
# unmistakable against a scale that is good to a fraction of a gram, small
# enough that ten lines fit in one cup with room to spare.
PRIME_TARGET_GRAM = 8.0

# The pump runs at full duty, as it does during an order -- priming at a
# different speed would prime a line the machine never uses.
PUMP_FREQUENCY_HZ = 1000

# --- the deadline, and why it has three parts -----------------------------
# expected = target / the pump's own calibrated flow rate
# margin   = room for a line that is slow but working
# air      = the head start a dry tube needs before anything lands at all
#
# A line that beats the target stops early; one that never delivers stops
# here. Nothing runs a pump without one of the two.
DEADLINE_MARGIN = 3.0
AIR_ALLOWANCE_SECONDS = 6.0
MAX_PUMP_SECONDS = 25.0

# Let the last of it land before the final reading, as a pump step does.
SETTLE_SECONDS = 1.5

# --- refusing to run on a scale that cannot be believed -------------------
# Sampled before anything is switched on. The threshold is deliberately
# loose: this is not asking for a precise scale, only for one whose
# readings sit still enough that "the weight went up by 8 g" means
# something.
SCALE_CHECK_SAMPLES = 20
SCALE_MAX_STDEV_GRAM = 1.0
SCALE_MAX_SPREAD_GRAM = 5.0

POLL_SECONDS = 0.05

# The live progress line rewrites itself with \r, which only works on a
# terminal. Piped to a file or a log it produces one line per poll -- 170
# lines for a single dry pump -- so it is written only when someone is
# watching, and no more than a few times a second even then.
PROGRESS_INTERVAL_SECONDS = 0.2

# Outcomes, in the order they are worth worrying about.
RESULT_PRIMED = "PRIMED"
RESULT_PARTIAL = "PARTIAL"
RESULT_NO_FLOW = "NO FLOW"
RESULT_SKIPPED = "SKIPPED"


def pump_lines(assigned_only: bool = False) -> list[dict[str, Any]]:
    """Every pump line on the machine, named where the database knows it.

    ALL TEN BY DEFAULT
        The machine has ten pumps and ten tubes, and every one of them
        holds air overnight. A pump with no ingredient assigned yet still
        needs priming before it is used, and priming it is also how you
        find out whether that line works at all -- so the default is the
        hardware, not the menu.

        --assigned narrows it to the lines that currently carry an
        ingredient, for a quick check before a shift.

    GPIO_TO_PUMP is the mapping the recipe builder uses, so a pump number
    here means the same thing it means in a recipe and in pump_calib.json.
    """
    from database.db_core import (close_database_resources,
                                  connect_database, gpio_number)
    from database.export_data import GPIO_TO_PUMP

    names: dict[int, dict[str, Any]] = {}

    try:
        conn = None
        cursor = None

        try:
            conn = connect_database()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT ingredient_id, ingredient_name, gpio, in_stock "
                "FROM ingredient "
                "WHERE type = 'PUMP' AND gpio IS NOT NULL"
            )
            for row in cursor.fetchall():
                names[gpio_number(row["gpio"])] = row
        finally:
            close_database_resources(cursor, conn)
    except Exception as error:      # noqa: BLE001 - names are a nicety
        # Priming is a hardware job. Losing the database costs the
        # ingredient names in the report, not the ability to prime.
        print(f"  (khong doc duoc ten nguyen lieu tu database: {error})")

    lines: list[dict[str, Any]] = []

    for gpio, pump_number in GPIO_TO_PUMP.items():
        row = names.get(gpio)

        if row is None and assigned_only:
            continue

        lines.append({
            "pump": pump_number,
            "gpio": gpio,
            "ingredient_id": int(row["ingredient_id"]) if row else None,
            "name": str(row["ingredient_name"]) if row else "(chua gan)",
            "in_stock": bool(row["in_stock"]) if row else True,
            "assigned": row is not None,
        })

    lines.sort(key=lambda line: line["pump"])
    return lines


def pump_deadline(pump_number: int, target_gram: float,
                  calibration: dict[str, Any]) -> float:
    """How long this pump may run before it is called a failure.

    Derived from the pump's own measured flow rate so a slow line is
    judged against itself. Falls back to the cap when a pump has never
    been calibrated -- an uncalibrated line still gets a deadline.
    """
    entry = calibration.get(f"pump_{pump_number}") or {}

    try:
        rate = float(entry.get("gram_per_sec") or 0.0)
    except (TypeError, ValueError):
        rate = 0.0

    if rate <= 0:
        return MAX_PUMP_SECONDS

    expected = target_gram / rate
    return min(expected * DEADLINE_MARGIN + AIR_ALLOWANCE_SECONDS,
               MAX_PUMP_SECONDS)


def steady_read(window: collections.deque, samples: int = 6) -> float | None:
    """Read the scale a few times and take the median of what came back."""
    values = []

    for _ in range(samples):
        value = read_weight_robust(window)

        if value is not None:
            values.append(value)

        time.sleep(POLL_SECONDS)

    return statistics.median(values) if values else None


def check_scale(window: collections.deque) -> tuple[bool, str]:
    """Is the load cell steady enough to prime by weight? (ok, message)

    Run before a single pump is switched on. Everything below depends on
    the scale: the stop condition, the pass/fail verdict, and the safety
    of running a pump at all. A scale that swings by kilograms will either
    stop a pump instantly or never stop it, and neither is visible in the
    output afterwards.
    """
    readings: list[float] = []
    misses = 0

    for _ in range(SCALE_CHECK_SAMPLES):
        value = read_weight_robust(window)

        if value is None:
            misses += 1
        else:
            readings.append(value)

        time.sleep(POLL_SECONDS)

    if len(readings) < SCALE_CHECK_SAMPLES // 2:
        return False, (f"can khong tra ve du lieu ({misses} lan khong doc "
                       f"duoc / {SCALE_CHECK_SAMPLES}). Kiem tra day HX711.")

    spread = max(readings) - min(readings)
    deviation = statistics.stdev(readings) if len(readings) > 1 else 0.0

    if deviation > SCALE_MAX_STDEV_GRAM or spread > SCALE_MAX_SPREAD_GRAM:
        return False, (f"can khong on dinh: lech chuan {deviation:.2f} g, "
                       f"bien do {spread:.2f} g "
                       f"(cho phep {SCALE_MAX_STDEV_GRAM:g} / "
                       f"{SCALE_MAX_SPREAD_GRAM:g} g).")

    return True, (f"can on dinh: lech chuan {deviation:.3f} g, "
                  f"bien do {spread:.3f} g.")


def prime_one(line: dict[str, Any], window: collections.deque,
              target_gram: float, calibration: dict[str, Any],
              dry_run: bool) -> dict[str, Any]:
    """Prime one line. Returns the result; never raises for a bad line.

    The pump is switched off in a finally, so an exception, a Ctrl+C or a
    deadline all leave it off. That guarantee is the whole reason this
    function owns the device rather than the caller.
    """
    pump_number = line["pump"]
    deadline_seconds = pump_deadline(pump_number, target_gram, calibration)

    baseline = steady_read(window)

    if baseline is None:
        return {**line, "result": RESULT_SKIPPED, "gram": 0.0,
                "seconds": 0.0, "note": "khong doc duoc can truoc khi bom"}

    print(f"  Bom {pump_number:>2}  {line['name']:<20} "
          f"nen {baseline:7.1f} g   toi da {deadline_seconds:4.1f}s")

    if dry_run:
        return {**line, "result": RESULT_SKIPPED, "gram": 0.0,
                "seconds": 0.0, "note": "--check, khong bom"}

    pwm = None
    delivered = 0.0
    started = time.monotonic()
    show_progress = sys.stdout.isatty()
    last_drawn = -PROGRESS_INTERVAL_SECONDS

    try:
        pwm = PWMLED(line["gpio"], frequency=PUMP_FREQUENCY_HZ)
        pwm.value = 1.0

        while True:
            elapsed = time.monotonic() - started
            current = read_weight_robust(window)

            if current is not None:
                delivered = max(0.0, current - baseline)

                if show_progress and elapsed - last_drawn >= PROGRESS_INTERVAL_SECONDS:
                    last_drawn = elapsed
                    bar = "#" * min(int(delivered / target_gram * 24), 24)
                    print(f"\r    {elapsed:5.1f}s  {delivered:6.1f} / "
                          f"{target_gram:g} g  [{bar:<24}]", end="", flush=True)

                if delivered >= target_gram:
                    break

            # Checked every pass, whatever the scale said -- including when
            # it said nothing. This is the guarantee that a pump stops.
            if elapsed >= deadline_seconds:
                break

            time.sleep(POLL_SECONDS)
    finally:
        if pwm is not None:
            # off, close, FREE -- all three, in that order, each in its own
            # finally so a failure in one still runs the next.
            #
            # close() used to stand here alone under a comment saying it
            # released the pin. It does not. On the lgpio backend close()
            # only re-claims the line as a pull-less input; the line stays
            # claimed by THIS process, `gpioinfo` still reports it "[used]",
            # and order/process_runner.py -- a fresh process for every drink
            # -- dies with 'GPIO busy' on that pump.
            #
            # pump_ml_parallel.py has always done all three. Priming was the
            # one pump path that stopped at close(), so a pump run from the
            # test screen broke every order after it until the service was
            # restarted. See pump_control/gpio_lines.py.
            try:
                pwm.off()
            finally:
                try:
                    pwm.close()
                finally:
                    free_gpio_line(line["gpio"])

    seconds = time.monotonic() - started

    if show_progress:
        print()

    time.sleep(SETTLE_SECONDS)
    settled = steady_read(window)

    if settled is not None:
        delivered = max(0.0, settled - baseline)

    if delivered >= target_gram:
        result, note = RESULT_PRIMED, ""
    elif delivered >= target_gram * 0.25:
        result, note = RESULT_PARTIAL, "chay cham -- kiem tra ong va bom"
    else:
        result, note = RESULT_NO_FLOW, "khong co nuoc -- het nguyen lieu?"

    return {**line, "result": result, "gram": delivered,
            "seconds": seconds, "note": note}


def report(results: list[dict[str, Any]], target_gram: float) -> int:
    """Print the summary. Returns a shell exit code."""
    print()
    print("=" * 68)
    print("  KET QUA MOI NUOC")
    print("=" * 68)
    print(f"  {'BOM':<5}{'NGUYEN LIEU':<22}{'KET QUA':<10}"
          f"{'GRAM':>8}{'GIAY':>8}  GHI CHU")
    print("  " + "-" * 64)

    for item in results:
        print(f"  {item['pump']:<5}{item['name'][:21]:<22}"
              f"{item['result']:<10}{item['gram']:>8.1f}{item['seconds']:>8.1f}"
              f"  {item['note']}")

    bad = [r for r in results
           if r["result"] in (RESULT_NO_FLOW, RESULT_PARTIAL)]
    primed = [r for r in results if r["result"] == RESULT_PRIMED]

    print("=" * 68)
    print(f"  {len(primed)} duong on, {len(bad)} duong co van de, "
          f"tong {sum(r['gram'] for r in results):.0f} g vao ly.")

    if bad:
        print()
        print("  CAN KIEM TRA:")
        for item in bad:
            print(f"    - Bom {item['pump']} ({item['name']}): "
                  f"{item['result']}, chi co {item['gram']:.1f} g "
                  f"sau {item['seconds']:.1f}s")

    print()
    return 1 if bad else 0


def record_failures(results: list[dict[str, Any]]) -> None:
    """Put lines that did not deliver in the error log. Best effort.

    A dry line found at priming is the same fault the weight check would
    have found mid-order, so it belongs in the same table -- that is what
    makes "pump 5 keeps failing" answerable from the data instead of from
    memory.
    """
    # Only lines that carry an ingredient. A pump with nothing assigned may
    # have its tube in a jug of water or in nothing at all, so NO FLOW there
    # is expected and logging it daily would bury the failures that matter.
    bad = [r for r in results
           if r["result"] in (RESULT_NO_FLOW, RESULT_PARTIAL)
           and r.get("assigned")]

    if not bad:
        return

    try:
        from database import error_log

        for item in bad:
            # GPIO and ingredient_id used to ride along in a `detail`
            # JSON column; that column is gone, so the pin goes in the
            # sentence -- it is the one number a person priming pumps
            # actually acts on.
            error_log.log_error(
                f"Moi nuoc: bom {item['pump']} ({item['name']}, "
                f"GPIO {item['gpio']}) {item['result']} -- "
                f"{item['gram']:.1f} g sau {item['seconds']:.1f}s",
                severity=error_log.SEVERITY_WARNING,
            )
    except Exception as error:      # noqa: BLE001 - reporting is not the job
        print(f"  (khong ghi duoc vao error_log: {error})")


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Mồi nước cho tất cả các bơm, dùng loadcell để xác nhận.",
    )
    parser.add_argument("--pumps", help="Chỉ mồi các bơm này, ví dụ 1,4,5.")
    parser.add_argument("--assigned", action="store_true",
                        help="Chỉ mồi các đường đã gán nguyên liệu "
                             "(mặc định: mồi cả 10 bơm).")
    parser.add_argument("--gram", type=float, default=PRIME_TARGET_GRAM,
                        help=f"Lượng cần bơm mỗi đường "
                             f"(mặc định {PRIME_TARGET_GRAM:g} g).")
    parser.add_argument("--check", action="store_true",
                        help="Chỉ kiểm tra cân, không chạy bơm.")
    parser.add_argument("--yes", action="store_true",
                        help="Không hỏi, chạy luôn.")
    args = parser.parse_args(argv)

    print("=" * 68)
    print("  MOI NUOC TAT CA CAC BOM  (xac nhan bang loadcell)")
    print("=" * 68)

    try:
        from configuration.configuration import PUMP_CALIB_FILE
        import json

        load_calibration()

        try:
            with open(PUMP_CALIB_FILE) as handle:
                calibration = json.load(handle)
        except (OSError, ValueError):
            calibration = {}
            print("  Chua co hieu chuan bom -- dung thoi gian toi da cho "
                  "moi duong.")

        lines = pump_lines(assigned_only=args.assigned)
    except Exception as error:      # noqa: BLE001 - reported, not raised
        print(f"  LOI: {error}")
        return 1

    if args.pumps:
        wanted = {int(t) for t in args.pumps.split(",") if t.strip().isdigit()}
        lines = [line for line in lines if line["pump"] in wanted]

    if not lines:
        print("  Khong co duong bom nao de moi.")
        return 1

    print(f"\n  {len(lines)} duong se duoc moi, {args.gram:g} g moi duong "
          f"(tong ~{len(lines) * args.gram:.0f} g):")
    for line in lines:
        if not line["assigned"]:
            note = ""            # the name already says "(chua gan)"
        elif not line["in_stock"]:
            note = "   (het hang trong database)"
        else:
            note = ""

        print(f"    Bom {line['pump']:>2}  GPIO {line['gpio']:>2}  "
              f"{line['name']}{note}")

    if not args.yes and not args.check:
        print("\n  Dat mot ly RONG len can, va dat tat ca voi bom vao ly.")
        try:
            input("  → Enter de bat dau, Ctrl+C de thoat...")
        except KeyboardInterrupt:
            print("\n  Da huy.")
            return 0

    window: collections.deque = collections.deque(maxlen=WINDOW_SIZE)

    # Fill the filter before anything is judged by it.
    for _ in range(WINDOW_SIZE * 2):
        read_weight_robust(window)
        time.sleep(0.02)

    print("\n  Kiem tra can...", flush=True)
    healthy, message = check_scale(window)
    print(f"  {message}")

    if not healthy:
        print()
        print("  DUNG LAI: khong moi nuoc khi can chua tin duoc.")
        print("  Moi nuoc dua hoan toan vao can de biet khi nao du va khi")
        print("  nao dung bom. Voi mot can nhu the nay, bom co the dung")
        print("  ngay lap tuc hoac khong bao gio dung.")
        print("  Kiem tra day HX711 roi chay lai: "
              "python3 -m pump_control.prime_all --check")
        return 2

    if args.check:
        print("\n  --check: can dat yeu cau, khong bom gi.")
        return 0

    print("  Tru bi ly...", end=" ", flush=True)
    tare(30)
    window.clear()
    for _ in range(WINDOW_SIZE * 2):
        read_weight_robust(window)
        time.sleep(0.02)
    print("xong.\n")

    results: list[dict[str, Any]] = []

    try:
        for line in lines:
            results.append(prime_one(line, window, args.gram,
                                     calibration, dry_run=False))
    except KeyboardInterrupt:
        # prime_one's own finally has already stopped the running pump.
        print("\n\n  Da dung theo yeu cau. Ket qua toi thoi diem nay:")

    code = report(results, args.gram)
    record_failures(results)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
