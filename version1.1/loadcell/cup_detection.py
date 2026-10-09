"""Decide whether a cup is on the scale, and how much it weighs.

WHAT THIS FILE IS
    The layer between the raw HX711 driver (loadcell/loadcell.py) and the
    machine. order/process_runner.py calls in here twice per drink: once
    to weigh the empty glass before pouring, and again at a detect step
    to confirm the cup came back after toppings.

TWO WAYS TO READ THE SCALE
    absolute (auto_zero=False, the default)
        gram = (raw - OFFSET) / SCALE, using the saved calibration. Sees
        a cup that is already sitting on the scale, which is what the
        machine needs, but is only as good as the stored OFFSET -- re-tare
        with loadcell/tare.py if an empty scale does not read near zero.

    relative (auto_zero=True)
        Snapshots whatever is on the scale right now as the zero point
        and waits for the weight to rise above it. Needs no calibration,
        but a cup placed before the snapshot is invisible, because it was
        baked into the zero.

HOW A DETECTION IS CONFIRMED
    A single reading is never enough: vibration and a stray sample both
    look like a cup. _detect_cup() polls every POLL_INTERVAL_SECONDS and
    keeps the last STABILITY_SECONDS worth of answers. The cup counts as
    present once MIN_PRESENT_RATIO of that window agrees, so one bad
    sample nudges the ratio instead of resetting the whole timer.

    check_cup()        one bounded attempt, returns True or False.
    read_current_gram() the weight right now, no threshold, no waiting.
    wait_for_cup()     blocks until a cup appears. NOTE: its body is
                       commented out and it currently returns True at
                       once, so callers use check_cup() in a loop.

WHO CHOOSES THE THRESHOLD
    min_gram is passed in by the caller, not fixed here. The machine
    weighs the empty glass at the start of a run and then asks for that
    weight back, so a detect step recognises the glass actually in use
    instead of trusting the number written into the recipe.
"""

from __future__ import annotations

import collections
import importlib
import math
import statistics
import sys
import time
from collections.abc import Callable
from pathlib import Path
from types import ModuleType


if __package__ in {None, ""}:
    project_dir = str(
        Path(__file__).resolve().parent.parent
    )

    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)


# Đặt SAU đoạn chèn sys.path ở trên, vì file này còn chạy trực tiếp được.
from flexmix_debug import trace          # noqa: E402


CUP_MIN_WEIGHT_GRAM = 80.0
STABILITY_SECONDS = 1.0
POLL_INTERVAL_SECONDS = 0.05

# A single noisy sample (vibration, a stray reading) must not throw away
# the whole stability window -- only treat the cup as "gone" once enough
# consecutive-in-time samples agree it's actually gone. Expressed as a
# fraction of the samples inside one STABILITY_SECONDS window so it scales
# automatically if POLL_INTERVAL_SECONDS or STABILITY_SECONDS change.
MIN_PRESENT_RATIO = 0.8

# check_cup()'s default timeout must comfortably exceed STABILITY_SECONDS,
# otherwise a stable reading can never be confirmed before time runs out.
DEFAULT_CHECK_TIMEOUT_SECONDS = 5.0

# Samples used to capture an instant local baseline (see auto_zero below).
# Small and fast on purpose -- this is a "what's on the scale right now"
# snapshot, not a real tare, so it stays quick even called every time.
AUTO_ZERO_SAMPLES = 5

# --- read_current_gram()'s estimator ---------------------------------------
# This function weighs a scale that is STANDING STILL: the pumps stopped
# and WEIGHT_SETTLE_SECONDS has already passed. That means it can use the
# sturdiest estimator available -- sample plenty, throw away whatever
# disagrees with the crowd, and take the median of the survivors.
#
# It used to fill a fresh eight-deep deque through read_weight_smooth()
# and return the LAST value, which lost drinks in two ways:
#   * the deque started EMPTY, and read_weight_smooth()'s spike gate only
#     arms itself at `len(window) >= 4`. The first four samples therefore
#     went in unchecked, so one corrupt frame among them poisoned the
#     median for the whole call.
#   * returning the last sample made the answer hostage to one reading.
# Measured under CPU load, that shape returned 16.76 g for a 159.07 g
# glass once every ~120 calls. The estimator below returned no reading
# worse than 0.2 g off across the same test.
STATIC_READ_SAMPLES = 10        # raw reads to gather
STATIC_READ_EXTRA_TRIES = 4     # extra attempts allowed for None answers
STATIC_READ_MIN_KEEP = 6        # survivors needed before we answer at all

# How far a sample may sit from the median and still be believed. Well
# under read_weight_smooth()'s 15 g spike threshold because nothing is
# supposed to be moving here: a settled scale on this machine repeats to
# about 0.05 g, so 3 g is already enormous, while every corrupt frame
# observed landed tens or hundreds of grams away.
STATIC_READ_TOLERANCE_GRAM = 3.0


def _capture_baseline(loadcell_module: ModuleType, samples: int) -> float:
    """Snapshot 'whatever is on the scale right now' as the zero point.

    Unlike tare(), this does not ask anyone to empty the scale first --
    it just averages a handful of raw reads taken on the spot. Cup
    detection then looks for a *rise* above this snapshot, so it works
    immediately without a fresh calibration run, at the cost of only
    detecting a cup placed *after* this call -- a cup already sitting on
    the scale when it's captured is invisible (it's baked into zero).
    """
    readings = [
        raw
        for raw in (loadcell_module.read_hx711() for _ in range(samples))
        if raw is not None
    ]
    if not readings:
        raise RuntimeError(
            "Không đọc được loadcell để lấy baseline (HX711 không phản hồi)."
        )
    return statistics.median(readings)


def _make_weight_reader(
    loadcell_module: ModuleType,
    *,
    auto_zero: bool,
) -> Callable[[], float | None]:
    """Build a zero-arg 'read current gram' function.

    auto_zero=True:  instant relative mode -- baseline captured right now,
                      no calibration file OFFSET involved, only SCALE.
    auto_zero=False: original absolute mode -- uses load_calibration()'s
                      saved OFFSET/SCALE and the module's own spike-gated
                      read_weight_smooth().
    """
    if not auto_zero:
        smoothing_window = collections.deque(
            maxlen=loadcell_module.WINDOW_SIZE,
        )

        def read_absolute() -> float | None:
            """Grams against the saved calibration, spike filtered."""
            return loadcell_module.read_weight_smooth(smoothing_window)

        return read_absolute

    baseline_raw = _capture_baseline(loadcell_module, AUTO_ZERO_SAMPLES)
    raw_window: collections.deque[float] = collections.deque(
        maxlen=loadcell_module.WINDOW_SIZE,
    )

    def read_relative() -> float | None:
        """Grams above the baseline captured a moment ago."""
        raw = loadcell_module.read_hx711()
        if raw is None:
            return None
        raw_window.append(raw)
        smoothed_raw = statistics.median(raw_window)
        return (smoothed_raw - baseline_raw) / loadcell_module.SCALE

    return read_relative


def _detect_cup(
    loadcell_module: ModuleType,
    *,
    auto_zero: bool,
    timeout_seconds: float | None,
    monotonic: Callable[[], float],
    sleep: Callable[[float], None],
    min_gram: float = CUP_MIN_WEIGHT_GRAM,
) -> bool:
    """Poll the scale until a stable cup is seen, or the timeout ends.

    Presence must hold across most of a STABILITY_SECONDS window, so a
    single noisy sample cannot start or stop a step on its own.
    """
    read_weight = _make_weight_reader(loadcell_module, auto_zero=auto_zero)

    # How many of the last STABILITY_SECONDS worth of samples were above
    # the threshold. A stray low reading only nudges this ratio down
    # instead of wiping out the whole stability timer.
    stability_samples = max(
        1,
        round(STABILITY_SECONDS / POLL_INTERVAL_SECONDS),
    )
    presence_window: collections.deque[bool] = collections.deque(
        maxlen=stability_samples,
    )

    started_at = monotonic()

    while True:
        weight = read_weight()
        now = monotonic()

        present = weight is not None and weight > min_gram
        presence_window.append(present)

        if (
            len(presence_window) == stability_samples
            and sum(presence_window) / stability_samples >= MIN_PRESENT_RATIO
        ):
            return True

        if (
            timeout_seconds is not None
            and now - started_at >= timeout_seconds
        ):
            return False

        sleep_seconds = POLL_INTERVAL_SECONDS

        if timeout_seconds is not None:
            remaining = timeout_seconds - (now - started_at)
            sleep_seconds = min(
                sleep_seconds,
                max(0.0, remaining),
            )

        sleep(sleep_seconds)


def _wait_for_cup(
    loadcell_module: ModuleType,
    *,
    auto_zero: bool,
    monotonic: Callable[[], float],
    sleep: Callable[[float], None],
) -> bool:
    """Wait without a deadline until the cup is there."""
    return _detect_cup(
        loadcell_module,
        auto_zero=auto_zero,
        timeout_seconds=None,
        monotonic=monotonic,
        sleep=sleep,
    )


def _load_calibrated_loadcell() -> ModuleType:
    """Import the driver and load OFFSET and SCALE into it."""
    loadcell_module = importlib.import_module(
        "loadcell.loadcell",
    )
    loadcell_module.load_calibration()
    return loadcell_module


def wait_for_cup(auto_zero: bool = True) -> bool:
    """Block until a cup is detected.

    auto_zero=True (default): no tare/calibration walkthrough needed --
    captures an instant local baseline and waits for weight to rise
    above it. Set False to fall back to the original behavior (absolute
    weight against the saved calibration OFFSET).
    """
    loadcell_module = _load_calibrated_loadcell()
    # return _wait_for_cup(
    #     loadcell_module,
    #     auto_zero=auto_zero,
    #     monotonic=time.monotonic,
    #     sleep=time.sleep,
    # )
    return True

@trace
def read_current_gram() -> float | None:
    """Return the weight on the scale right now, in absolute grams.

    Uses the saved OFFSET and SCALE from calib_loadcell.json. Nothing is
    tared: the value is what the scale reads, so an empty platform must
    sit near zero for the reading to mean anything.
    """
    loadcell_module = _load_calibrated_loadcell()

    # Gather raw counts, not grams: read_hx711() already refuses the
    # frames it can prove are broken (open data line, saturated ADC,
    # stretched clock, chip out of step) by answering None.
    raw_samples: list[float] = []

    for _ in range(STATIC_READ_SAMPLES + STATIC_READ_EXTRA_TRIES):
        raw = loadcell_module.read_hx711()

        if raw is not None:
            raw_samples.append(raw)

        if len(raw_samples) >= STATIC_READ_SAMPLES:
            break

    if len(raw_samples) < STATIC_READ_MIN_KEEP:
        return None

    scale = loadcell_module.SCALE

    if scale == 0:
        return 0.0

    offset = loadcell_module.OFFSET
    grams = [(raw - offset) / scale for raw in raw_samples]

    # Median first, then drop whatever disagrees with it. Taken in this
    # order the median is computed BEFORE any outlier is removed, so a
    # corrupt sample cannot drag the reference it is judged against --
    # it would have to outnumber the good samples to survive.
    middle = statistics.median(grams)
    agreed = [
        gram
        for gram in grams
        if abs(gram - middle) <= STATIC_READ_TOLERANCE_GRAM
    ]

    # Too much disagreement is not a weight, it is a scale nobody should
    # trust: say so rather than average the confusion into a number.
    if len(agreed) < STATIC_READ_MIN_KEEP:
        return None

    return statistics.median(agreed)


@trace
def check_cup(
    timeout_seconds: float = DEFAULT_CHECK_TIMEOUT_SECONDS,
    auto_zero: bool = False,
    min_gram: float = CUP_MIN_WEIGHT_GRAM,
) -> bool:
    """Return whether a stable cup is detected before the timeout.

    The default compares the absolute weight on the scale against
    min_gram. No tare and no baseline snapshot is taken, so a cup
    already sitting on the scale is seen immediately. Pass
    auto_zero=True for the old relative mode, which only notices a cup
    placed after the call.
    """
    timeout = float(timeout_seconds)

    if not math.isfinite(timeout) or timeout <= STABILITY_SECONDS:
        raise ValueError(
            "timeout_seconds must be finite and greater than "
            f"STABILITY_SECONDS ({STABILITY_SECONDS}s)"
        )

    loadcell_module = _load_calibrated_loadcell()
    return _detect_cup(
        loadcell_module,
        auto_zero=auto_zero,
        timeout_seconds=timeout,
        monotonic=time.monotonic,
        sleep=time.sleep,
        min_gram=float(min_gram),
    )


def main() -> int:
    """Run one finite cup check and return a shell-friendly exit code."""
    try:
        cup_present = check_cup()
    except Exception as error:
        print(
            f"LỖI KIỂM TRA LY: {error}",
            file=sys.stderr,
        )
        return 2

    print(
        "CÓ LY"
        if cup_present
        else "KHÔNG CÓ LY"
    )
    return 0 if cup_present else 1


if __name__ == "__main__":
    raise SystemExit(main())