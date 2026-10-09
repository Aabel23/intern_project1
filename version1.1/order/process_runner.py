"""Make one drink: read a recipe file, drive the machine, record progress.

WHAT THIS FILE IS
    The executor. It is the only thing that touches the pumps, the button
    panel and the load cell during a drink. Everything else either writes
    the recipe file it reads (database/export_data.py) or reads the
    progress it writes (bartender_gui/).

THE FILE IT READS AND WRITES
    order/current_recipe.json, in the process format documented by
    bartender_gui/PROCESS_SCHEMA.md:

        {"schema": "flexmix.process/1", "steps": [...]}

    The same file is the input, the progress log and the machine/screen
    bridge. Every state change is written straight back to it, s;b o the
    bartender screen sees the machine move by polling one file, and an
    interrupted run resumes by skipping the steps already marked done.

    Step statuses, and the only vocabulary the screen understands:

        pending -> waiting -> running -> done
                                  \\--> failed

THE FLOW OF ONE RUN
    1.  main() loads the recipe, optionally starts the HTTP server that
        serves the bartender screen, and starts the panel thread if any
        step needs physical buttons.
    2.  run_process() prepends the place-the-glass gate, stamps an
        order_id, then walks the steps in `order`.
    3.  For each step: mark it waiting, hold the settle delay, mark it
        running, run it, mark it done. A failure marks it failed, records
        the error and stops the run.
            start   - hold until the customer presses BAT DAU on screen,
                      then weigh the empty glass and keep the weight for
                      this run only.
            pump    - every pump in the step runs at the same time, each
                      for its own duration_sec taken literally from the
                      file, never recomputed from grams.
            manual  - light one panel lamp per ingredient and wait until
                      all are acknowledged, from the panel or the screen.
            detect  - wait for the screen's check button, then read the
                      load cell once and compare against the weighed
                      glass rather than a fixed threshold.
    4.  When every step is done, deduct from MySQL only the ingredients
        this run actually poured.

WHERE INPUT COMES FROM
    Physical panel buttons arrive through panel_control/panel.py on a
    queue. Screen taps arrive through GuiBridge, filled by the HTTP
    handler. Both feed the same waiting set, so either can finish a step.
    All hardware access stays on the runner thread: the HTTP handler
    never reads a device itself, or two readers would interleave on the
    HX711 and corrupt each other's bits.

RUNNING IT
    python3 -m order.process_runner                 screen on :8000
    python3 -m order.process_runner --no-serve      headless, gates auto
    python3 -m order.process_runner --dry-run       print the plan only
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import threading
from datetime import datetime
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from time import monotonic, sleep
from typing import Any
from uuid import uuid4

from configuration import served_paths
from configuration import machine
from pump_control.pump_ml_parallel import PUMP_GPIO
# Bật/tắt bằng FLEXMIX_DEBUG_ON trong flexmix_debug.py, hoặc bằng biến môi
# trường FLEXMIX_DEBUG=0/1. Khi tắt, trace() trả về đúng hàm gốc nên không
# tốn gì cả.
from flexmix_debug import debug, trace


PROCESS_SCHEMA = "flexmix.process/1"
DEFAULT_RECIPE_PATH = (
    Path(__file__).resolve().parent / "current_recipe.json"
)

STEP_TYPE_PUMP = "pump"
STEP_TYPE_MANUAL = "manual"
STEP_TYPE_DETECT = "detect"
# The operator does something the machine cannot -- shake, stir, torch a
# peel, garnish -- while a short clip loops on screen showing how. It ends
# with one press of the on-screen confirm, exactly like the start gate.
#
# NOT a manual step, even though both wait for a human. "manual" means
# "this step needs the physical LED button panel": has_manual_step() below
# is what arms link_panel_failure(), so typing an action step as manual
# would let a panel fault cancel an order that never touched the panel.
STEP_TYPE_ACTION = "action"
SUPPORTED_STEP_TYPES = frozenset(
    {
        STEP_TYPE_PUMP,
        STEP_TYPE_MANUAL,
        STEP_TYPE_DETECT,
        STEP_TYPE_ACTION,
    }
)

# The bartender screen reads the same file and expects exactly these
# words: see bartender_gui/PROCESS_SCHEMA.md. "waiting" means the step is
# the current one but held, so the screen shows it without filling meters.
#   pending -> waiting -> running -> done
#                              \--> failed
STATUS_PENDING = "pending"
STATUS_WAITING = "waiting"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "done"
STATUS_FAILED = "failed"

PUMP_FREQUENCY_HZ = 1000
PUMP_POLL_SECONDS = 0.05
# Let the lines drain and the liquid settle before the next step starts.
STEP_DELAY_SECONDS = 2.0
PANEL_POLL_SECONDS = 0.2
CUP_CHECK_TIMEOUT_SECONDS = 5.0
# "Is a cup on the scale?" -- one bar for every time that is asked.
#
# It used to be two numbers: 10 g at the start gate, where the glass is
# empty, and 80 g for a detect step later, where the glass has drink in it.
# Two numbers for one question is two things to keep right, and the higher
# one was never really load-bearing: on a real run the detect step compares
# against the glass WEIGHED at the start gate (see run_detect_step), so 80
# was only ever reached with no weight to compare against.
#
# 15 g is above the load cell's noise and below any empty glass, which is
# all this test has to do: tell a glass from an empty scale. Deciding the
# glass is the RIGHT one is the measured weight's job, not this number's.
CUP_MIN_GRAM = 15.0
# How many times the start gate may re-weigh before refusing the press.
#
# The gate weighs the glass instead of running a presence check first --
# see measure_cup_weight for why. read_current_gram() returns None when the
# last of its samples times out, which is one quiet moment on the HX711
# rather than an empty scale, so the press is worth repeating before it is
# refused. Each attempt costs about 0.7s, and attempts after the first only
# happen when the chip has already missed a sample.
CUP_WEIGH_ATTEMPTS = 3
# How long the start gate keeps watching the scale after a press that found
# no glass.
#
# A press used to buy exactly one look at the scale: press START with an
# empty scale, put the glass on a second later, and nothing happened -- the
# reading was already taken and the gate was back to waiting for another
# press. Everyone does it in that order at least once, because the screen
# is what tells them a glass is wanted.
#
# So a refused press leaves the scale under watch instead of dropping it.
# The glass is accepted the moment it appears, no second press needed. When
# the window runs out the gate falls back to waiting for a press, so
# nothing is lost -- it only ever adds a way forward.
CUP_WATCH_SECONDS = 30.0
# The screen blocks on its check button, so answer well inside its
# own fetch timeout rather than leaving the operator staring at it.
GUI_DETECT_TIMEOUT_SECONDS = 10.0

# Prepended to every recipe at run time, so the screen can show the customer
# where to put the glass and hold the machine until they press BAT DAU. It
# carries no buttons and no sensor, which is what makes the bartender screen
# render it as an on-screen confirm gate.
START_STEP_ID = "0"
START_STEP = {
    "step": START_STEP_ID,
    "order": 0,
    "type": STEP_TYPE_MANUAL,
    "owner": "gui",
    "status": STATUS_PENDING,
    "start": True,
    "icon": "cup",
    "title": {
        "vi": "Đặt ly lên máy",
        "en": "Place the cup on the machine",
    },
    "detail": {
        "vi": (
            "Đặt ly rỗng lên bàn cân, rồi bấm BẮT ĐẦU. "
            "Máy sẽ cân ly rồi tự bơm cho đến khi cần bạn."
        ),
        "en": (
            "Put the empty cup on the scale, then press START. The machine "
            "weighs it and pours on its own until it needs you."
        ),
    },
    "confirm": {
        "vi": "BẮT ĐẦU",
        "en": "START",
    },
}
# Load cell noise measured on this machine is well under a gram; the
# margin only stops that noise from rejecting a cup that is really back.
CUP_RETURN_TOLERANCE_GRAM = 2.0

# How long to keep serving after writing a failure, so the bartender screen
# can read it. That screen polls every 120 ms, so this is several chances --
# and it does NOT delay the customer: the browser leaves as soon as it sees
# the error, while this process is still finishing up behind it.
GUI_ERROR_LINGER_SECONDS = 1.0

# --- weighing each pump step -----------------------------------------------
# The pumps are driven by TIME: grams divided by the calibrated flow rate in
# configuration/pump_calib.json. That is accurate while nothing is wrong
# (r-squared above 0.9999) but it is open-loop -- a pump that stalls, a line
# with air in it, or a container that ran dry all take exactly as long as a
# healthy pour and produce a drink nobody notices is wrong.
#
# So the scale is asked afterwards. Measured on this machine, a settled
# reading is repeatable to about 0.05 g, which makes a missing 10 g of syrup
# enormous by comparison. What the tolerance really covers is the liquid --
# drips still in the air, foam on a syrup, the meniscus -- not the sensor.
WEIGHT_TOLERANCE_GRAM = 20.0

# How long to wait after the pumps stop before asking the scale.
#
# The reading has to be taken when the liquid has finished arriving, not
# when the pumps stopped driving it. A tube still draining, a drip on its
# way down and a cup rocking on the load cell all read as a shortfall that
# is real at that instant and gone a second later -- and a false failure
# throws away a drink that was fine.
#
# Two seconds is the cost of being sure. It is paid on every pump step, and
# on a failing step it is most of the time between the pour stopping and
# the customer being told -- so it trades promptness for not crying wolf,
# deliberately in that direction.
WEIGHT_SETTLE_SECONDS = 2.0

# read_current_gram() already averages eight samples internally, which after
# the settle above is enough. Raise it to two if a machine ever reads short
# on the first call -- it costs another 0.75 s on every pump step.
WEIGHT_READ_ATTEMPTS = 1

# Extra tries allowed ONLY when a read comes back None, which is not a light
# reading -- it is no reading at all. read_current_gram() takes eight samples
# and hands back the last one's result, so a single sample that misses its
# 0.25 s window at the end discards the seven good ones before it and fails
# the order with "check the load cell wire".
#
# weigh_the_glass() has guarded against exactly this since it was written
# (see CUP_WEIGH_ATTEMPTS). This path had no such guard, and it is the one
# that runs in the worse conditions: the pre-pour weigh happens on a quiet
# machine, this one happens seconds after ten seconds of pump motors. The
# unprotected read was the one most likely to need protecting.
#
# Costs nothing when the chip answers: a good read breaks out immediately.
WEIGHT_NONE_RETRIES = 3

# A short pour gets pumped again rather than throwing the drink away: a
# partly blocked line usually delivers, just slowly. Only ever attempted
# where ONE pump owns the step -- see verify_pump_step for why a step with
# two pumps running together cannot be topped up honestly.
TOPUP_MAX_ATTEMPTS = 2

# Below this a top-up is not worth a second of pumping and a second of
# settling; it is inside the tolerance anyway.
TOPUP_MIN_GRAM = 2.0

# How much LIGHTER than the cup's last known weight the scale may read
# before the reading is treated as a lost cup rather than a short pour.
#
# WHY THERE IS A LIMIT AT ALL
#     A pour only ever ADDS weight. It cannot take any away, so a scale
#     reading less than it did before the pump ran is not reporting a
#     shortfall -- the cup has been lifted off, knocked so it no longer
#     sits squarely on the platform, or the load cell has come loose.
#
#     Without this the arithmetic ran anyway, and it ran the wrong way:
#     lifting a 250 g cup during a 100 g pour makes `poured` come out at
#     -250 g and the shortfall at 350 g, which is short, and single-pump,
#     and above TOPUP_MIN_GRAM -- so the top-up dutifully asked the pump
#     for 350 g. At ~9.5 g/s that is thirty-six seconds of continuous
#     pouring into a cup that is not there, then a re-weigh that finds
#     the same impossible number and does it AGAIN. What should have been
#     an immediate weight-mismatch failure was over a minute of pumping.
#
# WHY 10 g
#     Well clear of anything innocent, and nowhere near a lifted cup. A
#     settled reading repeats to about 0.05 g, and the worst a real pour
#     does is throw a gram or two of foam over the rim. A cup weighs
#     hundreds. Nothing legitimate lives in between.
WEIGHT_LOSS_LIMIT_GRAM = 10.0
# The screen is the normal way to run, so serving is the default.
DEFAULT_GUI_PORT = machine.RUNNER_PORT
PANEL_COMMAND_QUEUE_SIZE = 32
BUTTON_EVENT_QUEUE_SIZE = 32


class ProcessError(RuntimeError):
    """Represent invalid recipe data or a failed machine action."""


class GuiBridge:
    """Everything the bartender screen may ask the machine to do.

    The screen never touches hardware. It leaves a request here and the
    runner thread, which owns the pumps, the panel and the load cell,
    picks it up. Keeping every device in one thread is what stops a
    screen tap and a panel press from reading the HX711 at the same
    moment and interleaving each other's bits.
    """

    def __init__(self) -> None:
        """Create the empty request slots the screen fills in."""
        # The place-the-glass gate.
        self.confirm_event = threading.Event()

        # Screen taps on a manual step's buttons, as (step label, panel).
        self.button_queue: queue.Queue[tuple[str, int]] = queue.Queue(
            maxsize=BUTTON_EVENT_QUEUE_SIZE,
        )

        # One cup check: the screen asks, the runner answers. Only a step
        # carrying a `sensor` block reaches this now -- see
        # run_detect_step -- but the answer still has to say what the
        # scale read and what it wanted, or a refusal explains nothing.
        self.detect_request = threading.Event()
        self.detect_done = threading.Event()
        self.detected = False
        self.detect_sensor: dict[str, Any] | None = None

        # Staff asking the machine to stop. Requested at any moment, but
        # honoured at the END of the current step: stopping a pump halfway
        # leaves a cup holding an amount nobody asked for, and the step is
        # the smallest unit the recipe is written in. So the machine
        # finishes what it started and then holds.
        self.pause_event = threading.Event()
        self.paused_now = threading.Event()      # runner -> screen
        self.resume_event = threading.Event()

        # A cancel from the paused screen, with the reason somebody typed.
        # The reason is the whole point: "cancelled" on its own tells you
        # nothing later, while "wrong drink" and "machine leaking" lead to
        # completely different actions.
        self.cancel_event = threading.Event()
        self.cancel_lock = threading.Lock()
        self.cancel_reason = ""
        self.cancel_note = ""


# ============================================================
# 1. FILE ACCESS
# ============================================================

def atomic_write_json(path: Path, data: object) -> None:
    """Write the recipe state without leaving a partial JSON file."""
    temporary_path = path.with_suffix(
        path.suffix + ".tmp"
    )

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )
        file.flush()
        os.fsync(file.fileno())

    os.replace(
        temporary_path,
        path,
    )


def load_process(path: Path) -> dict[str, Any]:
    """Load one process document and validate its root value."""
    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            document = json.load(file)
    except FileNotFoundError as error:
        raise ProcessError(
            f"Recipe not found: {path}"
        ) from error
    except json.JSONDecodeError as error:
        raise ProcessError(
            f"Invalid recipe JSON: {error}"
        ) from error
    except OSError as error:
        raise ProcessError(
            f"Cannot read recipe: {error}"
        ) from error

    if not isinstance(document, dict):
        raise ProcessError(
            "Recipe root must be an object."
        )

    schema = str(
        document.get("schema", "")
    )

    if schema != PROCESS_SCHEMA:
        raise ProcessError(
            f"Unsupported recipe schema {schema!r}; "
            f"expected {PROCESS_SCHEMA!r}."
        )

    return document


def now_text() -> str:
    """Return one timestamp in the format used by the process format.

    Milliseconds, with an explicit UTC offset. Whole seconds were not
    enough: the bartender screen divides by started_at to fill its pour
    meters, so truncating to a second put the bar up to a full second
    out of step with the pump. The offset removes any doubt about how a
    browser reads the string.
    """
    return datetime.now().astimezone().isoformat(
        timespec="milliseconds"
    )


def save_process(
    path: Path,
    document: dict[str, Any],
    dry_run: bool = False,
) -> None:
    """Persist the document and stamp the moment it changed.

    A dry run must leave the file untouched. Writing progress from a
    rehearsal would mark every step completed, so the next real run
    would skip the whole recipe.
    """
    if dry_run:
        return

    document["updated_at"] = now_text()
    atomic_write_json(
        path,
        document,
    )


# ============================================================
# 2. VALIDATION
# ============================================================

def validated_pumps(
    step: dict[str, Any],
) -> list[tuple[int, float, int, float]]:
    """Return (pump, duration_sec, ingredient_id, gram) for one pump step."""
    pumps = step.get("pumps")

    if not isinstance(pumps, list) or not pumps:
        raise ProcessError(
            f"Step {step.get('step')} has no pumps list."
        )

    orders: list[tuple[int, float, int, float]] = []
    used_pumps: set[int] = set()

    for pump in pumps:
        if not isinstance(pump, dict):
            raise ProcessError(
                f"Step {step.get('step')} contains an invalid pump."
            )

        try:
            pump_number = int(
                pump["pump"]
            )
            duration = float(
                pump["duration_sec"]
            )
            ingredient_id = int(
                pump["ingredient_id"]
            )
            gram = float(
                pump["gram"]
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ProcessError(
                f"Step {step.get('step')} contains invalid pump data."
            ) from error

        if pump_number not in PUMP_GPIO:
            raise ProcessError(
                f"Pump {pump_number} has no GPIO assignment."
            )

        if duration <= 0:
            raise ProcessError(
                f"Step {step.get('step')} pump {pump_number} has a "
                f"non-positive duration_sec ({duration})."
            )

        # Two threads driving one GPIO pin would fight over the same pump.
        if pump_number in used_pumps:
            raise ProcessError(
                f"Step {step.get('step')} uses pump {pump_number} twice."
            )

        used_pumps.add(
            pump_number
        )
        orders.append(
            (pump_number, duration, ingredient_id, gram)
        )

    return orders


def is_start_step(step: dict[str, Any]) -> bool:
    """Report whether this is the injected place-the-glass gate."""
    return bool(step.get("start", False))


def ensure_start_step(
    document: dict[str, Any],
) -> None:
    """Put the place-the-glass gate in front of the recipe, once."""
    steps = document.get("steps")

    if not isinstance(steps, list):
        raise ProcessError(
            "Recipe has no steps to run."
        )

    if any(
        isinstance(step, dict) and is_start_step(step)
        for step in steps
    ):
        return

    steps.insert(
        0,
        json.loads(json.dumps(START_STEP)),
    )


def validated_buttons(
    step: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return the acknowledgement buttons of one manual step."""
    buttons = step.get("buttons")

    # A manual step with no buttons is a plain confirm gate, released from
    # the screen rather than from the panel.
    if buttons is None and is_start_step(step):
        return []

    if not isinstance(buttons, list) or not buttons:
        raise ProcessError(
            f"Step {step.get('step')} has no buttons list."
        )

    for button in buttons:
        if not isinstance(button, dict):
            raise ProcessError(
                f"Step {step.get('step')} contains an invalid button."
            )

        try:
            panel_id = int(
                button["panel"]
            )
            int(
                button["ingredient_id"]
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ProcessError(
                f"Step {step.get('step')} contains invalid button data."
            ) from error

        if not 0 <= panel_id <= 15:
            raise ProcessError(
                f"Panel {panel_id} is outside the supported range 0-15."
            )

    return buttons


def validated_steps(
    document: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return every step in run order after checking its own contents."""
    steps = document.get("steps")

    if not isinstance(steps, list) or not steps:
        raise ProcessError(
            "Recipe has no steps to run."
        )

    for step in steps:
        if not isinstance(step, dict):
            raise ProcessError(
                "Every step must be an object."
            )

        step_type = str(
            step.get("type", "")
        )

        if step_type not in SUPPORTED_STEP_TYPES:
            raise ProcessError(
                f"Step {step.get('step')} has unsupported "
                f"type {step_type!r}."
            )

        try:
            int(
                step["order"]
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ProcessError(
                f"Step {step.get('step')} has no integer order."
            ) from error

        if step_type == STEP_TYPE_PUMP:
            validated_pumps(step)
        elif step_type == STEP_TYPE_MANUAL:
            validated_buttons(step)
        elif step_type == STEP_TYPE_ACTION:
            validated_media(step)

        # Files written before the status words were aligned with the
        # bartender screen used "completed" for a finished step.
        if step.get("status") == "completed":
            step["status"] = STATUS_COMPLETED

        # An interrupted run left a step current but unfinished; the step
        # has to run again, so it goes back to pending.
        if step.get("status") in {STATUS_RUNNING, STATUS_WAITING}:
            step["status"] = STATUS_PENDING

    return sorted(
        steps,
        key=lambda step: int(step["order"]),
    )


def has_manual_step(
    steps: list[dict[str, Any]],
) -> bool:
    """Report whether any step needs the physical panel.

    STEP_TYPE_ACTION is deliberately NOT counted. It waits for a human
    too, but it is answered by the on-screen confirm and never lights a
    lamp, so a panel fault must not cancel an order whose only human step
    is an action. That is the whole reason it is a separate type.
    """
    return any(
        step["type"] == STEP_TYPE_MANUAL
        for step in steps
    )


# ============================================================
# 3. PUMP STEP
# ============================================================

@trace
def run_pump_for_duration(
    pump_number: int,
    duration_sec: float,
    stop_event: threading.Event,
) -> None:
    """Drive one pump for exactly the seconds written in the recipe."""
    from gpiozero import PWMLED

    pwm = PWMLED(
        PUMP_GPIO[pump_number],
        frequency=PUMP_FREQUENCY_HZ,
    )

    try:
        pwm.value = 1.0
        remaining = duration_sec

        while remaining > 0:
            if stop_event.is_set():
                raise ProcessError(
                    f"Pump {pump_number} interrupted by shutdown."
                )

            interval = min(
                PUMP_POLL_SECONDS,
                remaining,
            )
            started_at = monotonic()
            sleep(interval)
            elapsed = monotonic() - started_at

            if elapsed <= 0:
                elapsed = interval

            remaining -= min(
                elapsed,
                remaining,
            )

    finally:
        pwm.off()
        # The same pump appears in several steps, so the pin must be
        # released here instead of waiting for garbage collection.
        pwm.close()


# Set for exactly as long as pumps are turning. The panel's restart button
# is refused while it is set: a restart kills this process, and nothing
# switches the pumps off on the way out -- pump_control turns them off in a
# finally block, which a signal does not run. A machine stuck at a gate is
# what the button is for; a machine mid-pour is not.
POURING = threading.Event()


@trace
def run_pump_step(
    step: dict[str, Any],
    stop_event: threading.Event,
    dry_run: bool,
) -> None:
    """Run every pump of one step at the same time."""
    orders = validated_pumps(
        step
    )

    for pump_number, duration, _, gram in orders:
        print(
            f"  pump {pump_number}: {gram:g}g -> {duration:.3f}s"
        )

    if dry_run:
        sleep(0.05)
        return

    failures: dict[int, BaseException] = {}
    failure_lock = threading.Lock()

    def worker(
        pump_number: int,
        duration: float,
    ) -> None:
        """Run one pump in its own thread, keeping any failure."""
        try:
            run_pump_for_duration(
                pump_number,
                duration,
                stop_event,
            )
        except BaseException as error:  # noqa: BLE001
            with failure_lock:
                failures[pump_number] = error

    threads = [
        threading.Thread(
            target=worker,
            args=(pump_number, duration),
            name=f"pump-{pump_number}",
        )
        for pump_number, duration, _, _ in orders
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    if failures:
        raise ProcessError(
            "; ".join(
                f"pump {pump_number}: {error}"
                for pump_number, error in sorted(failures.items())
            )
        )


# ============================================================
# 4. MANUAL STEP
# ============================================================

@trace
def send_panel_command(
    panel_command_queue: queue.Queue[tuple[str, object]] | None,
    action: str,
    payload: object,
    stop_event: threading.Event,
) -> None:
    """Send one command to the panel worker, if a panel is running."""
    if panel_command_queue is None:
        return

    while not stop_event.is_set():
        try:
            panel_command_queue.put(
                (action, payload),
                timeout=0.5,
            )
            return
        except queue.Full:
            continue


@trace
def run_manual_step(
    step: dict[str, Any],
    recipe_path: Path,
    document: dict[str, Any],
    panel_command_queue: queue.Queue[tuple[str, object]] | None,
    button_event_queue: queue.Queue[int] | None,
    stop_event: threading.Event,
    dry_run: bool,
    bridge: GuiBridge | None = None,
) -> None:
    """Light one button per ingredient and wait for every acknowledgement.

    A lamp may be lit by the physical panel or by a tap on the bartender
    screen. Whichever source lights the last one finishes the step.
    """
    buttons = validated_buttons(
        step
    )

    for button in buttons:
        print(
            f"  panel {button['panel']}: "
            f"{button['label']['en']} ({button.get('gram', 0):g}g)"
        )

    if dry_run:
        for button in buttons:
            button["lit"] = True
        sleep(0.05)
        return

    if panel_command_queue is None or button_event_queue is None:
        raise ProcessError(
            f"Step {step.get('step')} needs the panel, "
            "but no panel worker is running."
        )

    waiting = {
        int(button["panel"]): button
        for button in buttons
        if not bool(button.get("lit", False))
    }

    for button in buttons:
        button["lit"] = bool(
            button.get("lit", False)
        )

    lit_panel_ids: set[int] | None = None

    while waiting and not stop_event.is_set() and not gate_abandoned(bridge):
        # Resend only when a press changed the set, so the panel worker is
        # not flooded with an identical command on every poll.
        if lit_panel_ids != set(waiting):
            send_panel_command(
                panel_command_queue,
                "show",
                sorted(waiting),
                stop_event,
            )
            lit_panel_ids = set(waiting)

        # A press may arrive from the physical panel or from the screen.
        # Both light the same lamp, so whichever finishes the step first
        # completes it and the other simply has nothing left to press.
        panel_id = None
        source = "panel"

        if bridge is not None:
            try:
                step_label, gui_panel = bridge.button_queue.get_nowait()
            except queue.Empty:
                pass
            else:
                bridge.button_queue.task_done()

                if step_label == str(step.get("step")):
                    panel_id = gui_panel
                    source = "screen"
                else:
                    print(
                        f"  ignored screen press for step {step_label}: "
                        f"step {step.get('step')} is the current one"
                    )

        if panel_id is None:
            try:
                panel_id = button_event_queue.get(
                    timeout=PANEL_POLL_SECONDS,
                )
            except queue.Empty:
                continue

        try:
            button = waiting.pop(
                panel_id,
                None,
            )

            if button is None:
                print(
                    f"  ignored {source} press on panel {panel_id}: "
                    "not part of this step, or already pressed"
                )
                continue

            button["lit"] = True
            save_process(
                recipe_path,
                document,
                dry_run,
            )
            print(
                f"  panel {panel_id} acknowledged from the {source}."
            )

        finally:
            # Only the panel queue tracks unfinished work; the screen's
            # was already marked done when it was drained above.
            if source == "panel":
                button_event_queue.task_done()

    send_panel_command(
        panel_command_queue,
        "clear",
        None,
        stop_event,
    )

    if waiting:
        raise ProcessError(
            f"Step {step.get('step')} was interrupted before "
            f"panel {sorted(waiting)} were acknowledged."
        )


# ============================================================
# 4B. ACTION STEP
# ============================================================


def validated_media(
    step: dict[str, Any],
) -> dict[str, Any]:
    """Return the step's media block, or raise if it cannot be shown.

    The filename is checked here rather than on the screen because this
    is the side that can still refuse the order. It becomes part of a URL
    the browser fetches, so a name carrying a slash or a parent reference
    would read a file outside recipe/media/ -- validate before it is ever
    written into current_recipe.json.
    """
    media = step.get("media")

    if not isinstance(media, dict):
        raise ProcessError(
            f"Step {step.get('step')} is an action step "
            "but has no media block."
        )

    src = str(
        media.get("src", "")
    ).strip()

    if not src:
        raise ProcessError(
            f"Step {step.get('step')} has no media.src."
        )

    if "/" in src or "\\" in src or src.startswith("."):
        raise ProcessError(
            f"Step {step.get('step')} has an unsafe media.src {src!r}: "
            "it must be a bare filename inside recipe/media/."
        )

    return media


@trace
def run_action_step(
    step: dict[str, Any],
    stop_event: threading.Event,
    dry_run: bool,
    bridge: "GuiBridge | None" = None,
) -> None:
    """Hold while the operator does it, then take one press as the answer.

    The screen loops the clip named by media.src and shows the step's own
    confirm button. Nothing here watches the scale: an action may add
    weight (a garnish), lose it (liquid left in the shaker) or leave it
    unchanged (a stir), and none of those says whether the operator is
    finished. Only the press does.

    The cup often leaves the scale during one of these. That is already
    handled without any help from this function: run_process() refreshes
    the baseline after every non-pump step, and a recipe whose action
    lifts the glass follows it with a detect step, exactly as the manual
    step at 3 is followed by 3a.
    """
    media = validated_media(step)

    print(
        f"  action: {media['src']} — waiting for the operator."
    )

    if dry_run:
        sleep(0.05)
        return

    confirm_event = (
        bridge.confirm_event
        if bridge is not None
        else None
    )

    if confirm_event is None:
        raise ProcessError(
            f"Step {step.get('step')} needs the bartender screen, "
            "but no screen is attached."
        )

    # No clear here: run_process() already dropped any stale press before
    # this step was announced, and clearing now would swallow a press made
    # while the screen was showing this gate and the machine was still in
    # its between-steps delay.
    while not stop_event.is_set() and not gate_abandoned(bridge):
        if confirm_event.wait(timeout=PANEL_POLL_SECONDS):
            confirm_event.clear()
            print("  done pressed.")
            return

    raise ProcessError(
        f"Step {step.get('step')} was interrupted before "
        "the operator confirmed it."
    )


# ============================================================
# 5. DETECT STEP
# ============================================================

@trace
def measure_cup_weight(
    step: dict[str, Any],
    recipe_path: Path,
    document: dict[str, Any],
    confirm_event: threading.Event | None,
    stop_event: threading.Event,
    dry_run: bool,
    bridge: "GuiBridge | None" = None,
) -> float | None:
    """Hold until the customer presses start, then weigh the glass.

    Each press triggers exactly one look at the scale. An empty scale is
    reported back into the step so the screen can say so, and the gate
    stays open for another press. The weight is kept only for this run: a
    later detect step compares against it instead of a fixed threshold,
    so the machine recognises the glass actually in use.
    """
    if dry_run:
        print(
            "  waiting for the start button, then weighing the glass "
            f"(threshold {CUP_MIN_GRAM:g}g)."
        )
        sleep(0.05)
        return None

    from loadcell.cup_detection import check_cup, read_current_gram

    if confirm_event is None:
        # Headless: no screen, so nothing can press the button. Fall back
        # to watching the scale and starting as soon as a glass appears.
        print(
            "  no screen attached; waiting for the glass "
            f"(above {CUP_MIN_GRAM:g}g)."
        )

        while not stop_event.is_set() and not gate_abandoned(bridge):
            if check_cup(
                timeout_seconds=CUP_CHECK_TIMEOUT_SECONDS,
                min_gram=CUP_MIN_GRAM,
            ):
                cup_gram = read_current_gram()

                if cup_gram is None:
                    raise ProcessError(
                        "The glass was detected but its weight could "
                        "not be read."
                    )

                print(f"  glass weight: {cup_gram:.1f}g.")
                return cup_gram

            current = read_current_gram()
            print(
                "  no glass yet"
                + (
                    f" (scale reads {current:.1f}g)."
                    if current is not None
                    else " (no reading from the scale)."
                )
            )

        raise ProcessError(
            "Interrupted while waiting for the glass."
        )

    print(
        "  waiting for the start button on the screen."
    )

    def weigh_the_glass() -> float | None:
        """Read the scale once, looking past a chip that missed a sample.

        Weighed once, not checked and then weighed. check_cup() answers
        only "is something there?" and cannot do it in less than a full
        STABILITY_SECONDS window -- twenty HX711 samples, which at the
        chip's ~10 SPS is 1.7-2.0s, right up against the two seconds it
        used to be given. Then read_current_gram() took eight more
        samples to get the number the gate actually needs. Two and a
        half seconds, and a race it sometimes lost: a press with the
        glass sitting on the scale came back "Chưa thấy ly trên bàn cân"
        and the customer pressed again.

        read_current_gram() answers both questions at once. It is a
        median over WINDOW_SIZE samples through the same spike filter,
        so it is no more credulous than the presence window was, and the
        decision it feeds is not a close one: an empty scale reads near
        zero and any glass is well over CUP_MIN_GRAM.
        """
        # One quiet chip must not cost the customer a press. The reading
        # comes back None when the LAST of its samples times out, even
        # though the ones before it were fine, so ask again before
        # refusing.
        cup_gram = None

        for _ in range(CUP_WEIGH_ATTEMPTS):
            cup_gram = read_current_gram()

            if cup_gram is not None:
                break

            if stop_event.is_set() or gate_abandoned(bridge):
                break

        return cup_gram

    def accept(cup_gram: float) -> float:
        """Clear any refusal still on the step and report the weight."""
        if step.pop("error", None) is not None:
            save_process(
                recipe_path,
                document,
                dry_run,
            )

        print(
            f"  glass weight: {cup_gram:.1f}g."
        )
        return cup_gram

    while not stop_event.is_set() and not gate_abandoned(bridge):
        if not confirm_event.wait(timeout=PANEL_POLL_SECONDS):
            continue

        confirm_event.clear()
        print("  start pressed; weighing the scale.")

        # A fresh press starts from a clean slate. The screen hands the
        # gate button back when it sees a refusal on the step, so leaving
        # the last one in the file would hand it back mid-press and put a
        # stale reason under a press that has not been answered yet.
        if step.pop("error", None) is not None:
            save_process(
                recipe_path,
                document,
                dry_run,
            )

        cup_gram = weigh_the_glass()

        if cup_gram is not None and cup_gram >= CUP_MIN_GRAM:
            return accept(cup_gram)

        # Reported on the step so the screen can explain the refusal
        # instead of the press appearing to do nothing.
        step["error"] = (
            "Chưa thấy ly trên bàn cân"
            + (
                f" (cân đọc {cup_gram:.1f}g)."
                if cup_gram is not None
                else " (không đọc được cân)."
            )
            + " Đặt ly lên cân, máy sẽ tự nhận."
        )
        save_process(
            recipe_path,
            document,
            dry_run,
        )
        print(f"  {step['error']}")

        # The press found nothing, so keep watching instead of throwing
        # the scale away until somebody presses again -- the glass is
        # usually on its way at this exact moment. See CUP_WATCH_SECONDS.
        watch_until = monotonic() + CUP_WATCH_SECONDS

        while (
            monotonic() < watch_until
            and not stop_event.is_set()
            and not gate_abandoned(bridge)
        ):
            cup_gram = weigh_the_glass()

            if cup_gram is not None and cup_gram >= CUP_MIN_GRAM:
                print("  glass appeared while watching the scale.")
                return accept(cup_gram)

            # weigh_the_glass() already spends most of a second on the
            # HX711; this only keeps the loop off the chip's back.
            sleep(PANEL_POLL_SECONDS)

        # A press that arrived during the watch has been answered by the
        # watch itself -- do not let it buy a second weighing right away.
        confirm_event.clear()
        print("  still no glass; waiting for the start button again.")

    raise ProcessError(
        "Interrupted while waiting for the glass."
    )


@trace
def run_detect_step(
    step: dict[str, Any],
    recipe_path: Path,
    document: dict[str, Any],
    stop_event: threading.Event,
    dry_run: bool,
    cup_gram: float | None = None,
    bridge: GuiBridge | None = None,
) -> None:
    """Hold until the cup is back on the scale, then carry on.

    THE PRESS ASKS THE QUESTION; THE SCALE ANSWERS IT
        The operator puts the cup back and presses. That press buys one
        look at the scale: something on it, and the drink continues;
        nothing on it, and the step says so and stays open for another
        press. Exactly the shape of the start gate -- see
        measure_cup_weight() -- because it is the same job, and the
        operator has already learnt it at the top of the drink.

    WHY THE THRESHOLD IS NOT THE GLASS WEIGHED AT THE START
        It was once, and that is what made this step impossible to answer:
        a cell reading a little low refused a cup that was plainly sitting
        there, and a refusal from the screen has no way round it, so the
        drink could only be cancelled. The test is now CUP_MIN_GRAM -- "is
        anything on the scale" -- which a cup with a drink in it clears by
        two orders of magnitude. A scale that does not answer at all is a
        wiring fault rather than an absent cup, and is not allowed to
        strand the drink either.

    WHAT STILL MEASURES
        Nothing downstream depends on this step's reading. run_process()
        refreshes the pour baseline after every non-pump step, from the
        scale as it is then, and keeps the previous baseline when the
        reading says the cup is not back -- so a press answered too
        generously costs a baseline, not a bad pour.

    THE SCALE IS WATCHED ON ITS OWN WHEN NOBODY CAN PRESS
        Headless, there is no screen and no press, so the loop below falls
        back to watching the scale exactly as before.
    """
    sensor = step.get("sensor")
    min_gram = float(
        sensor.get("min_gram", CUP_MIN_GRAM)
        if isinstance(sensor, dict)
        else CUP_MIN_GRAM
    )

    # The glass weighed at the start beats any figure written into the
    # recipe, because it describes the glass actually in use. It is only
    # consulted on the paths that still read the scale -- headless, and an
    # old screen asking for a check -- so the threshold is not announced
    # here: printing "needs > 163.5g" in front of a step that a press
    # releases described a rule that no longer applies.
    if cup_gram is not None:
        min_gram = max(
            0.0,
            cup_gram - CUP_RETURN_TOLERANCE_GRAM,
        )

    if dry_run:
        sleep(0.05)
        return

    from loadcell.cup_detection import check_cup, read_current_gram

    def look_at_the_scale() -> bool:
        """One bounded check, recording what the scale read."""
        found = check_cup(
            timeout_seconds=CUP_CHECK_TIMEOUT_SECONDS,
            min_gram=min_gram,
        )
        current = read_current_gram()

        if isinstance(sensor, dict) and current is not None:
            sensor["current_gram"] = round(current, 1)

        if found:
            print(
                "  cup detected"
                + (f" ({current:.1f}g)." if current is not None else ".")
            )
            return True

        print(
            "  no cup yet"
            + (
                f" (scale reads {current:.1f}g, needs > {min_gram:.1f}g)."
                if current is not None
                else " (no reading from the scale)."
            )
        )
        return False

    if bridge is None:
        # Headless: nobody can press the check button, so watch the scale
        # and continue as soon as the cup is back.
        print(
            f"  no screen attached: watching the scale instead "
            f"(needs > {min_gram:.1f}g)."
        )
        while not stop_event.is_set() and not gate_abandoned(bridge):
            if look_at_the_scale():
                return

        raise ProcessError(
            f"Step {step.get('step')} was interrupted while "
            "waiting for the cup."
        )

    print("  waiting for the confirm button on the screen.")

    def weigh_the_cup() -> float | None:
        """Read the scale once, looking past a chip that missed a sample.

        The same read the start gate uses -- see weigh_the_glass() in
        measure_cup_weight(). read_current_gram() answers "is anything
        there, and how much" in one median-filtered read; check_cup()
        needs a full stability window first and then a second read to get
        the number, which is a press the operator waits two seconds for.
        """
        for _ in range(CUP_WEIGH_ATTEMPTS):
            reading = read_current_gram()

            if reading is not None:
                return reading

            if stop_event.is_set() or gate_abandoned(bridge):
                break

        return None

    def accept(reading: float | None) -> None:
        """Clear any refusal still on the step and let the drink carry on."""
        if step.pop("error", None) is not None:
            save_process(recipe_path, document, dry_run)

        if reading is None:
            print("  carrying on: the scale never answered, so the cup "
                  "cannot be verified.")
        else:
            print(f"  cup is back on the scale ({reading:.1f}g).")

    # WHAT THE PRESS IS CHECKED AGAINST
    #     CUP_MIN_GRAM -- "is anything on the scale" -- and deliberately
    #     not the glass weighed at the start gate. That threshold is what
    #     made this step impossible to answer once: it refused a cup that
    #     was plainly sitting there whenever the cell read a little low,
    #     and the screen offers no way round a refusal. A cup with a drink
    #     in it clears 15 g by two orders of magnitude, so this test says
    #     "the cup is back" without ever being the thing that blocks it.
    #
    #     A scale that does not answer AT ALL is a wiring fault, not an
    #     absent cup, and is not allowed to strand the drink either: the
    #     press is taken at its word and the run continues.
    while not stop_event.is_set() and not gate_abandoned(bridge):
        if bridge.confirm_event.wait(timeout=PANEL_POLL_SECONDS):
            bridge.confirm_event.clear()
            print("  cup confirmed by the operator; checking the scale.")

            reading = weigh_the_cup()

            if reading is None or reading >= CUP_MIN_GRAM:
                accept(reading)
                return

            # Said on the step so the screen explains the refusal and hands
            # the button back, instead of the press appearing to do nothing.
            step["error"] = (
                f"Chưa thấy ly trên bàn cân (cân đọc {reading:.1f}g). "
                "Đặt ly lên cân rồi bấm lại."
            )
            save_process(recipe_path, document, dry_run)
            print(f"  {step['error']}")

            # The cup is usually on its way at this exact moment, so keep
            # watching rather than throwing the scale away until somebody
            # presses again -- the same reason the start gate does. See
            # CUP_WATCH_SECONDS.
            watch_until = monotonic() + CUP_WATCH_SECONDS

            while (
                monotonic() < watch_until
                and not stop_event.is_set()
                and not gate_abandoned(bridge)
            ):
                reading = weigh_the_cup()

                if reading is not None and reading >= CUP_MIN_GRAM:
                    print("  cup appeared while watching the scale.")
                    accept(reading)
                    return

                # weigh_the_cup() already spends most of a second on the
                # HX711; this only keeps the loop off the chip's back.
                sleep(PANEL_POLL_SECONDS)

            # A press that arrived during the watch has been answered by
            # the watch itself -- do not let it buy a second weighing.
            bridge.confirm_event.clear()
            print("  still no cup; waiting for the button again.")
            continue

        # An older screen asks for a scale check instead of pressing: an
        # order already in flight when this changed, or the simulator.
        # Answered the way it expects, so an upgrade cannot strand a drink
        # halfway through a recipe that still carries a sensor block.
        if bridge.detect_request.is_set():
            bridge.detect_request.clear()
            print("  check pressed; reading the scale.")

            found = look_at_the_scale()
            save_process(
                recipe_path,
                document,
                dry_run,
            )

            bridge.detected = found
            bridge.detect_sensor = {
                "current_gram": (
                    sensor.get("current_gram")
                    if isinstance(sensor, dict)
                    else None
                ),
                "min_gram": round(min_gram, 1),
            }
            bridge.detect_done.set()

            if found:
                return

    raise ProcessError(
        f"Step {step.get('step')} was interrupted while "
        "waiting for the cup."
    )


# ============================================================
# 6. INVENTORY
# ============================================================

def finish_cancelled(
    recipe_path: Path,
    document: dict[str, Any],
    bridge: "GuiBridge | None",
    executed_steps: list[dict[str, Any]],
    update_inventory: bool,
    dry_run: bool,
) -> bool:
    """End an order that staff abandoned. Always returns False.

    Separate from the failure path because a cancel is not a fault: the
    customer is told "đã hủy" rather than "máy gặp sự cố", and error_log
    keeps a category that means somebody decided, not something broke.

    The steps already poured ARE deducted. The liquid is in a cup whatever
    the reason, and stock that only counts finished drinks drifts away from
    the shelf -- which is the whole reason failures started being charged.
    """
    reason = bridge.cancel_reason if bridge is not None else ""
    note = bridge.cancel_note if bridge is not None else ""

    document["cancelled_at"] = now_text()
    document["cancel_reason"] = reason
    document["cancel_note"] = note
    document["error"] = "Đơn đã bị hủy."
    document.pop("paused_at", None)
    save_process(recipe_path, document, dry_run)

    print(f"[runner] Đơn bị hủy: {reason}"
          + (f" — {note}" if note else ""))

    record_step_failure(
        document,
        {"step": document.get("cancelled_after_step"), "type": "order"},
        f"Hủy đơn: {reason}" + (f" — {note}" if note else "")
        + f" (đã xong {len(executed_steps)} bước)",
        severity="warning",
    )

    # Give the screen its chance to read the cancellation before the
    # server goes down with this process.
    linger_for_screen(threading.Event(), dry_run)

    if update_inventory and not dry_run:
        charge_for_failed_order(executed_steps)

    return False


def gate_abandoned(bridge: "GuiBridge | None") -> bool:
    """True when a gate should stop waiting because staff cancelled.

    A gate -- the start prompt, a manual step, the cup check -- is idle by
    definition: it is waiting for a person, nothing is pouring, and there
    is no pour to protect. So a cancel takes effect here and now.

    That is the opposite of a PUMP step, which is allowed to finish before
    a cancel is honoured, because stopping halfway leaves a cup holding an
    amount nobody chose.

    This exists because the two were once treated the same. When cancels
    stopped setting stop_event -- so that a pour could finish -- the gates
    lost the only thing that could ever wake them, and pressing "Hủy đơn"
    during a cup check did nothing at all: the machine sat waiting for a
    cup that was never coming, for an order somebody had already
    abandoned.
    """
    return bridge is not None and bridge.cancel_event.is_set()


def hold_while_paused(
    recipe_path: Path,
    document: dict[str, Any],
    bridge: "GuiBridge | None",
    stop_event: threading.Event,
    dry_run: bool,
) -> bool:
    """Hold between steps while staff decide. True to carry on, False to stop.

    WHY AT THE END OF A STEP
        A step is the smallest unit the recipe is written in. Stopping
        inside one leaves a cup holding an amount nobody chose and a
        half-open question about whether to count it. Finishing the step
        first means the pause always lands somewhere the recipe describes,
        and resuming is simply "do the next one".

    WHAT THE SCREEN SEES
        paused_at goes into current_recipe.json, so the screen can say the
        machine has actually stopped rather than that a request was sent.
        The two are different, and staff standing at a machine that is
        still pouring deserve to be told which is true.

    Returns False when the order is to be abandoned -- cancelled from the
    dialog, or the whole run stopped -- so the caller can end the order
    the same way it ends any other.
    """
    if bridge is None:
        return True

    # Checked before the pause flag: a cancel can arrive without anyone
    # having paused first (a direct request, or a second person acting
    # while the dialog is open), and it must still end the order rather
    # than fall through and pour the next step.
    if bridge.cancel_event.is_set():
        return False

    if stop_event.is_set():
        return False

    if not bridge.pause_event.is_set():
        return True

    document["paused_at"] = now_text()
    save_process(recipe_path, document, dry_run)
    bridge.paused_now.set()
    print("[runner] Tạm dừng ở cuối bước. Chờ Tiếp tục hoặc Hủy đơn.")

    try:
        while not stop_event.is_set():
            if bridge.cancel_event.is_set():
                return False

            if bridge.resume_event.is_set() or not bridge.pause_event.is_set():
                break

            # Waited on stop_event rather than slept, so Ctrl+C and a
            # cancel are both immediate rather than up to a tick late.
            stop_event.wait(0.1)
    finally:
        bridge.paused_now.clear()

    if stop_event.is_set():
        return False

    bridge.pause_event.clear()
    bridge.resume_event.clear()
    document.pop("paused_at", None)
    save_process(recipe_path, document, dry_run)
    print("[runner] Tiếp tục.")
    return True


def record_step_failure(
    document: dict[str, Any],
    step: dict[str, Any],
    message: str,
    *,
    severity: str = "error",
) -> None:
    """Put one step failure in the error_log table.

    Imported here rather than at module scope so that a machine with no
    database still runs: this file drives pumps, and it should not fail to
    import because MySQL is unavailable.

    Silent on failure by design -- database/error_log.py already reports
    its own problems to stderr, and an order that has just failed must not
    be derailed further by the recording of it.

    There is no `detail` or `category` any more -- both columns were
    dropped on 2026-09-07. Whatever a person needs in front of them goes
    in `message`, which is the column the fault screen shows, and
    `severity` is all that sorts one kind of fault from another.

    `message` is also how the fault names its ticket: log_step_failure()
    reads `ticket_serial` out of the document this is handed -- it was
    written there when the QR was claimed -- and tags the head of the
    sentence with it. That is the whole link from a fault back to the
    order, and it needed no column; see HOW A FAULT STILL NAMES ITS
    TICKET in database/error_log.py.
    """
    try:
        from database import error_log

        error_log.log_step_failure(
            document, step, message, severity=severity,
        )
    except Exception:      # noqa: BLE001 - never worsen an existing failure
        pass


def linger_for_screen(stop_event: threading.Event, dry_run: bool) -> None:
    """Stay up briefly so the screen can read the failure this process wrote.

    Under --dry-run no screen is served, so there is nobody to wait for.
    Interruptible, so Ctrl+C is still immediate.
    """
    if dry_run:
        return

    stop_event.wait(GUI_ERROR_LINGER_SECONDS)


@trace
def read_settled_gram(stop_event: threading.Event) -> float | None:
    """Weigh what is on the scale once the pour has finished landing.

    Returns None if the scale does not answer, which is a wiring fault
    rather than an empty cup -- the caller treats it as "cannot verify"
    and says so, instead of pretending the step poured nothing.
    """
    from loadcell.cup_detection import read_current_gram

    if stop_event.wait(WEIGHT_SETTLE_SECONDS):
        return None             # cancelled while settling

    reading = None
    good = 0

    # Read more than once and keep the last: the first call after a pour
    # can still catch the tail of the movement, and a second costs 0.75 s.
    #
    # A None does not count towards that total -- the chip simply did not
    # answer, so the loop is allowed WEIGHT_NONE_RETRIES further goes at
    # getting an answer at all before giving up and reporting a fault.
    for _ in range(WEIGHT_READ_ATTEMPTS + WEIGHT_NONE_RETRIES):
        value = read_current_gram()

        if value is not None:
            reading = value
            good += 1

            if good >= WEIGHT_READ_ATTEMPTS:
                break

        if stop_event.is_set():
            return None

    return reading


def guard_cup_on_scale(
    step: dict[str, Any],
    baseline_gram: float,
    measured: float,
    poured: float,
) -> None:
    """Refuse a reading lighter than the cup this step started with.

    Raises ProcessError if the scale LOST weight across the pour. Returns
    quietly otherwise -- including on a pour that delivered nothing at
    all, which is a real shortfall and exactly what the top-up is for.

    WHY THIS RUNS BEFORE ANY TOP-UP, AND AGAIN AFTER EVERY ONE
        The top-up loop trusts `shortfall` enough to convert it into pump
        seconds. That is only safe while the number describes liquid. A
        cup lifted off the scale makes it describe the cup instead, and
        the loop cannot tell the difference -- see WEIGHT_LOSS_LIMIT_GRAM
        for what that cost. So the reading is checked at the one place it
        can still be refused: before it is believed.

        Checked again after each top-up because the cup can just as
        easily be lifted DURING one, and a loop that only validated its
        first reading would run the same way from its second.

    It is a ProcessError like a weight mismatch, so it fails the order,
    reaches the screen and lands in error_log the same way. The sentence
    is different because the answer is: nothing is wrong with the pump,
    and telling somebody to check the tubing would send them the wrong
    way entirely.
    """
    if poured >= -WEIGHT_LOSS_LIMIT_GRAM:
        return

    step["weight_check"] = {
        "status": "cup_lost",
        "baseline_gram": round(baseline_gram, 2),
        "measured_gram": round(measured, 2),
        "lost_gram": round(-poured, 2),
        "limit_gram": WEIGHT_LOSS_LIMIT_GRAM,
    }

    raise ProcessError(
        f"Ly rời khỏi cân ở bước {step.get('step')}: cân nhẹ đi "
        f"{-poured:.1f}g trong lúc bơm (còn {measured:.1f}g, trước đó "
        f"{baseline_gram:.1f}g). Máy đã dừng bơm. Đặt ly lại lên cân và "
        "pha đơn mới."
    )


@trace
def verify_pump_step(
    step: dict[str, Any],
    baseline_gram: float | None,
    stop_event: threading.Event,
    dry_run: bool,
) -> tuple[float | None, float]:
    """Weigh what a pump step poured. Raises ProcessError if it is wrong.

    Returns (new_baseline, poured_gram).

    HOW THE TARGET IS WORKED OUT
        From the weight measured after the PREVIOUS step, never from what
        that step was supposed to leave behind. If step 1 was asked for
        100 g and really poured 95, step 2 is judged from 95 -- so a single
        small shortfall does not put every later step out of tolerance and
        turn one fault into a cascade of them. Each step is answerable only
        for its own pour.

    WHY A SHORT POUR IS ONLY TOPPED UP ON A ONE-PUMP STEP
        A step runs its pumps together, so the scale sees one number for
        the lot. If Water and Sugar pour at once and 10 g are missing,
        nothing in the reading says which pump was short -- and pumping
        "the shortfall" through both would add more of whichever ingredient
        was already fine. On a step with one pump there is no ambiguity and
        the correction is exact.

    An over-pour is never recoverable: liquid cannot be taken back out, so
    it fails immediately.

    WHAT THE TOP-UP IS NOT ALLOWED TO BELIEVE
        That a reading lighter than the cup started at is a shortfall.
        Lifting the cup mid-pour made `poured` negative, and every step
        from there was individually reasonable: a negative poured is a
        large shortfall, a large shortfall on a single-pump step is
        topped up, and a top-up runs for as many seconds as the shortfall
        is grams. The result was a pump running for over a minute instead
        of a weight mismatch on the screen.

        Two things stop it now, and they are independent on purpose:
        guard_cup_on_scale() refuses the reading before it is believed,
        and the top-up asks for at most the step's own target and runs
        for at most the step's own duration whatever it is asked for.
    """
    if dry_run:
        return baseline_gram, 0.0

    orders = validated_pumps(step)
    target_gram = sum(gram for _, _, _, gram in orders)

    measured = read_settled_gram(stop_event)

    if stop_event.is_set():
        raise ProcessError("Interrupted while weighing the step.")

    if measured is None:
        raise ProcessError(
            "Không đọc được cân sau khi bơm. Kiểm tra dây load cell."
        )

    if baseline_gram is None:
        # Nothing to measure against -- the cup was never weighed. Record
        # the reading so later steps have a baseline, but do not pretend
        # this step was checked.
        step["weight_check"] = {
            "status": "skipped",
            "reason": "no baseline weight for this cup",
            "measured_gram": round(measured, 2),
        }
        print("  weight check: skipped, the cup was never weighed.")
        return measured, 0.0

    poured = measured - baseline_gram
    shortfall = target_gram - poured

    print(
        f"  weight check: poured {poured:.1f}g of {target_gram:g}g "
        f"(scale {measured:.1f}g, was {baseline_gram:.1f}g)"
    )

    # Before anything is done with `shortfall`, and in particular before
    # it is turned into pump seconds below.
    guard_cup_on_scale(step, baseline_gram, measured, poured)

    single_pump = len(orders) == 1
    attempts = 0

    # Top up while it is short, it is worth doing, and this step's pump can
    # be identified. Each pass re-weighs, so the loop ends on the truth.
    while (
        single_pump
        and shortfall > WEIGHT_TOLERANCE_GRAM
        and shortfall >= TOPUP_MIN_GRAM
        and attempts < TOPUP_MAX_ATTEMPTS
    ):
        attempts += 1
        pump_number, step_seconds, _, _ = orders[0]

        # The same conversion the recipe was built with, from the same
        # calibration file -- a second copy of t = (gram - b) / a here
        # could drift from the one that produced the original durations.
        try:
            from database.export_data import (
                duration_for_gram,
                load_pump_calibration,
            )
            seconds = duration_for_gram(
                # Never more than the step was asked for in the first
                # place: a step that poured nothing needs topping up by
                # its whole target and no step can ever need more. With
                # the guard above in place `shortfall` cannot exceed that
                # anyway -- this is the second lock on the same door, and
                # the door is a pump that does not stop.
                pump_number, min(shortfall, target_gram),
                load_pump_calibration(),
            )
        except (ValueError, OSError) as error:
            print(f"  cannot top up: {error}")
            break

        # And never longer than the step's own pour took. Whatever the
        # arithmetic above decides, one top-up cannot outrun the pour it
        # is correcting.
        seconds = min(seconds, step_seconds)

        print(
            f"  short by {shortfall:.1f}g -- topping up pump "
            f"{pump_number} for {seconds:.2f}s "
            f"(attempt {attempts}/{TOPUP_MAX_ATTEMPTS})"
        )

        run_pump_for_duration(pump_number, seconds, stop_event)

        measured = read_settled_gram(stop_event)

        if stop_event.is_set():
            raise ProcessError("Interrupted while topping up.")

        if measured is None:
            raise ProcessError(
                "Không đọc được cân sau khi bơm bù."
            )

        poured = measured - baseline_gram
        shortfall = target_gram - poured
        print(f"  after top-up: {poured:.1f}g of {target_gram:g}g")

        # The cup can be lifted during a top-up just as easily as during
        # the pour -- and a loop that only checked its first reading
        # would run away from its second exactly as before.
        guard_cup_on_scale(step, baseline_gram, measured, poured)

    difference = poured - target_gram

    step["weight_check"] = {
        "status": "ok" if abs(difference) <= WEIGHT_TOLERANCE_GRAM else "failed",
        "target_gram": round(target_gram, 2),
        "poured_gram": round(poured, 2),
        "difference_gram": round(difference, 2),
        "tolerance_gram": WEIGHT_TOLERANCE_GRAM,
        "baseline_gram": round(baseline_gram, 2),
        "measured_gram": round(measured, 2),
        "topups": attempts,
    }

    if abs(difference) > WEIGHT_TOLERANCE_GRAM:
        names = ", ".join(
            str(pump.get("ingredient_name", {}).get("en", pump.get("pump")))
            for pump in step.get("pumps", [])
        )
        raise ProcessError(
            f"Cân không khớp ở bước {step.get('step')}: cần {target_gram:g}g "
            f"({names}), thực tế {poured:.1f}g "
            f"(lệch {difference:+.1f}g, cho phép ±{WEIGHT_TOLERANCE_GRAM:g}g). "
            "Kiểm tra bơm, ống dẫn và bình nguyên liệu."
        )

    return measured, poured


def collect_ingredient_usage(
    steps: list[dict[str, Any]],
) -> dict[int, float]:
    """Sum the grams of the given steps, by ingredient.

    Only pass steps this run actually executed. A step carrying the
    status of an earlier run must never reach here, or its ingredients
    would be billed to the inventory a second time.
    """
    usage: dict[int, float] = {}

    for step in steps:
        if step.get("status") != STATUS_COMPLETED:
            continue

        if step["type"] == STEP_TYPE_PUMP:
            items = step.get("pumps", [])
        elif step["type"] == STEP_TYPE_MANUAL:
            items = step.get("buttons", [])
        else:
            continue

        for item in items:
            ingredient_id = int(
                item["ingredient_id"]
            )
            gram = float(
                item.get("gram", 0)
            )

            if gram <= 0:
                continue

            usage[ingredient_id] = usage.get(
                ingredient_id,
                0.0,
            ) + gram

    return {
        ingredient_id: round(gram, 3)
        for ingredient_id, gram in sorted(usage.items())
    }


def partial_step_usage(step: dict[str, Any]) -> dict[int, float]:
    """What a step that FAILED must be charged, by ingredient: all of it.

    The step is billed its FULL recipe amount, not the amount the scale
    measured. A step asking for 50 g is charged 50 g even when the scale
    saw 0.

    WHY THE FULL AMOUNT AND NOT THE MEASURED ONE
        Because the measurement is the thing that just failed. If the load
        cell reads 0 g the liquid may genuinely not have come out -- or the
        cup may have been knocked, or the scale may be the fault. The one
        thing known for certain is how much the machine was told to pour
        and that it ran the pumps for that long.

        So the error is taken in the safe direction. Charging too much
        makes the database believe there is LESS in the container than
        there is, which ends in someone topping up early. Charging too
        little makes it believe there is more, which ends in a pump running
        dry in the middle of a paid order -- the failure that costs a
        customer their drink, and the exact drift this whole check exists
        to stop.

    The proportional split this used to do -- billing each ingredient its
    share of what arrived -- was a better estimate on average and worse
    when it was wrong, because it was wrong in the optimistic direction.
    """
    usage: dict[int, float] = {}

    for pump in step.get("pumps", []):
        try:
            ingredient_id = int(pump["ingredient_id"])
            gram = float(pump.get("gram", 0))
        except (KeyError, TypeError, ValueError):
            continue

        if gram > 0:
            usage[ingredient_id] = round(
                usage.get(ingredient_id, 0.0) + gram, 3,
            )

    return usage


@trace
def charge_for_failed_order(
    executed_steps: list[dict[str, Any]],
    failed_step: dict[str, Any] | None = None,
) -> None:
    """Deduct what a failed order poured before it stopped.

    Stock is otherwise only touched when a drink finishes, so every failure
    used to leave the database believing it still had ingredients that were
    already in a cup. Over many failures the shelf and the database drift
    apart silently, and the first sign is a pump running dry on a drink the
    machine was sure it could make.

    Never raises: the order has already failed, and a database problem must
    not replace the real error with a different one.
    """
    usage = collect_ingredient_usage(executed_steps)

    if failed_step is not None:
        for ingredient_id, gram in partial_step_usage(failed_step).items():
            usage[ingredient_id] = round(
                usage.get(ingredient_id, 0.0) + gram, 3,
            )

    if not usage:
        print("[inventory] Nothing was poured; stock unchanged.")
        return

    try:
        from database.inventory_service import consume_recipe_usage

        consume_recipe_usage(usage)
        print(
            # "the part poured" was the old, proportional rule. The failed
            # step is now charged in full, so the message says so.
            "[inventory] Đơn hỏng -- đã trừ theo công thức: "
            + ", ".join(
                f"ingredient {ingredient_id}={gram:g}g"
                for ingredient_id, gram in sorted(usage.items())
            )
        )
    except Exception as error:      # noqa: BLE001 - the order already failed
        print(f"[inventory] Deduction after failure failed: {error}")


@trace
def consume_inventory(
    steps: list[dict[str, Any]],
) -> None:
    """Subtract what the machine actually poured from the database."""
    usage = collect_ingredient_usage(
        steps
    )

    if not usage:
        print("[inventory] Nothing to deduct.")
        return

    from database.inventory_service import consume_recipe_usage

    consume_recipe_usage(usage)
    print(
        "[inventory] Deducted: "
        + ", ".join(
            f"ingredient {ingredient_id}={gram:g}g"
            for ingredient_id, gram in usage.items()
        )
    )


# ============================================================
# 7. RUN ONE RECIPE
# ============================================================

@trace
def run_step(
    step: dict[str, Any],
    recipe_path: Path,
    document: dict[str, Any],
    panel_command_queue: queue.Queue[tuple[str, object]] | None,
    button_event_queue: queue.Queue[int] | None,
    stop_event: threading.Event,
    dry_run: bool,
    cup_gram: float | None = None,
    bridge: GuiBridge | None = None,
    run_state: dict[str, Any] | None = None,
) -> None:
    """Dispatch one step to the library that performs it."""
    step_type = step["type"]

    if is_start_step(step):
        weighed = measure_cup_weight(
            step,
            recipe_path,
            document,
            bridge.confirm_event if bridge is not None else None,
            stop_event,
            dry_run,
            bridge,
        )

        if run_state is not None:
            run_state["cup_gram"] = weighed
            # The empty cup is where the weighing of every later pump step
            # starts from.
            run_state["baseline_gram"] = weighed

        return

    if step_type == STEP_TYPE_PUMP:
        POURING.set()

        try:
            run_pump_step(
                step,
                stop_event,
                dry_run,
            )
        finally:
            POURING.clear()

        return

    if step_type == STEP_TYPE_MANUAL:
        run_manual_step(
            step,
            recipe_path,
            document,
            panel_command_queue,
            button_event_queue,
            stop_event,
            dry_run,
            bridge,
        )
        return

    if step_type == STEP_TYPE_ACTION:
        run_action_step(
            step,
            stop_event,
            dry_run,
            bridge,
        )
        return

    run_detect_step(
        step,
        recipe_path,
        document,
        stop_event,
        dry_run,
        cup_gram,
        bridge,
    )


@trace
def run_process(
    recipe_path: Path,
    document: dict[str, Any],
    panel_command_queue: queue.Queue[tuple[str, object]] | None,
    button_event_queue: queue.Queue[int] | None,
    stop_event: threading.Event,
    dry_run: bool,
    update_inventory: bool,
    step_delay: float = STEP_DELAY_SECONDS,
    bridge: GuiBridge | None = None,
) -> bool:
    """Run every unfinished step in order and record the result."""
    ensure_start_step(
        document
    )
    steps = validated_steps(
        document
    )

    if not document.get("order_id"):
        document["order_id"] = uuid4().hex

    if not document.get("created_at"):
        document["created_at"] = now_text()

    # A restart stamped by the previous run must not greet this one: the
    # screen reads it as "the machine is going down now" and would show
    # that card over a drink that is only just starting.
    document.pop("restarting_at", None)

    document["error"] = None
    save_process(
        recipe_path,
        document,
        dry_run,
    )

    print(
        f"[runner] Order {document['order_id']} "
        f"({document.get('drink_name')}): {len(steps)} steps."
    )

    # The glass is weighed by the start step below, so a later detect
    # step can recognise this glass instead of trusting a fixed
    # threshold. It lives only for this run and is never written down.
    # cup_gram   the empty glass, used by the detect step to know it is back
    # baseline_gram  what the scale read after the last verified step; every
    #                pump step is measured as a change from this, never from
    #                what the recipe expected to be there
    run_state: dict[str, Any] = {"cup_gram": None, "baseline_gram": None}

    # Only the steps this run poured itself may be deducted from stock.
    executed_steps: list[dict[str, Any]] = []

    for step in steps:
        if step.get("status") == STATUS_COMPLETED:
            print(
                f"[runner] Step {step['step']} already completed; skipped."
            )
            continue

        # A press left over from the gate before must not answer this step.
        #
        # CLEARED HERE, BEFORE THE STEP IS ANNOUNCED -- not on entry to the
        # handler, which is where it used to be. The screen raises a gate as
        # soon as a step turns `waiting`, which is STEP_DELAY_SECONDS before
        # the handler starts waiting on the event. A press made inside that
        # window -- the usual one, because the operator is already standing
        # at the machine with the cup in their hand -- was accepted by the
        # HTTP server, answered with 202, and then wiped by the handler's
        # own clear. The gate then waited for a press that had already
        # happened, and the screen sat on "Dang xu ly..." for good: it had
        # locked the button for a request it believed was still in flight.
        if bridge is not None:
            bridge.confirm_event.clear()

        # The pause belongs between two steps, never before the first one
        # and never after a step that was skipped.
        #
        # Nor after the start gate. This delay exists to let the lines
        # drain and the liquid settle, and the gate moves no liquid at all
        # -- it holds for a person and weighs a glass. Charging it two
        # seconds put dead time exactly where the customer is watching for
        # the machine to react to their press.
        if (
            executed_steps
            and not is_start_step(executed_steps[-1])
            and step_delay > 0
        ):
            print(
                f"[runner] Waiting {step_delay:g}s before the next step."
            )

            # Held, not yet pouring: the screen shows this step as current
            # with its meters at zero instead of appearing to stall.
            step["status"] = STATUS_WAITING
            save_process(
                recipe_path,
                document,
                dry_run,
            )

            if not dry_run:
                stop_event.wait(step_delay)

            if stop_event.is_set():
                document["error"] = "interrupted between steps"
                save_process(
                    recipe_path,
                    document,
                    dry_run,
                )
                print("[runner] Interrupted between steps.")
                return False

        print(
            f"[runner] Step {step['step']} ({step['type']}):"
        )

        # started_at lets the screen clock the pour from the machine's own
        # start instead of from whenever it first polled the step.
        step["status"] = STATUS_RUNNING
        step["started_at"] = now_text()
        step.pop("error", None)
        save_process(
            recipe_path,
            document,
            dry_run,
        )

        try:
            run_step(
                step,
                recipe_path,
                document,
                panel_command_queue,
                button_event_queue,
                stop_event,
                dry_run,
                run_state["cup_gram"],
                bridge,
                run_state,
            )
        except Exception as error:
            # A cancel from the screen arrives here as an interrupted pump,
            # which looks exactly like a hardware failure from inside the
            # step. It is not one, and everything downstream cares about
            # the difference: the customer is told "đã hủy" rather than
            # "máy gặp sự cố", and the fault table stays a record of things
            # that are actually broken.
            cancelled = bridge is not None and bridge.cancel_event.is_set()

            step["status"] = STATUS_FAILED
            # The screen shows the failing step's own error next to it.
            step["error"] = str(error)
            document["error"] = str(error)

            if cancelled:
                document["cancelled_at"] = now_text()
                document["cancel_reason"] = bridge.cancel_reason
                document["cancel_note"] = bridge.cancel_note

            save_process(
                recipe_path,
                document,
                dry_run,
            )
            print(
                f"[runner] Step {step['step']} "
                + ("cancelled" if cancelled else f"failed: {error}")
            )

            # A pump, the panel or the load cell threw. The exception type
            # is kept: "[Errno 121] Remote I2C error" and "no such pump"
            # are the same category to a customer and completely different
            # to whoever fixes it.
            # "Phần cứng:" is written in because error_log.category, the
            # column that used to carry that word, is gone -- and telling
            # a broken pump from a cancelled order at a glance is the
            # whole reason anybody opens this log.
            record_step_failure(
                document, step,
                (f"Hủy đơn: {bridge.cancel_reason}"
                 + (f" — {bridge.cancel_note}" if bridge.cancel_note else ""))
                if cancelled
                else f"Phần cứng: {error} [{type(error).__name__}]",
                severity=("warning" if cancelled else "error"),
            )

            linger_for_screen(stop_event, dry_run)

            # The failing step is billed too, in full. It threw part-way
            # through, so how much reached the cup is unknown -- and an
            # unknown amount is charged as the whole amount, for the same
            # reason as a failed weight check: the database must never
            # believe there is more in a container than there is. A step
            # that threw before pouring anything (bad recipe data, say) has
            # no pumps to bill, so it costs nothing.
            if update_inventory and not dry_run:
                charge_for_failed_order(executed_steps, step)

            return False

        # --- did the pumps actually deliver? -----------------------------
        # After the step ran, not during: the pumps are open-loop, and this
        # is the only thing between a stalled pump and a customer getting a
        # drink that looks finished. A failure here is a step failure, so
        # it takes the same path as any other -- including the stock
        # correction below, since whatever DID come out is really gone.
        if step["type"] == STEP_TYPE_PUMP:
            try:
                run_state["baseline_gram"], _ = verify_pump_step(
                    step,
                    run_state.get("baseline_gram"),
                    stop_event,
                    dry_run,
                )
            except Exception as error:
                step["status"] = STATUS_FAILED
                step["error"] = str(error)
                document["error"] = str(error)
                save_process(recipe_path, document, dry_run)
                print(f"[runner] Step {step['step']} failed: {error}")

                # Recorded before anything else is attempted, so a fault is
                # in the table even if the stock correction below then hits
                # a database problem of its own.
                record_step_failure(
                    document, step, f"Sai khối lượng: {error}",
                )

                # Hold the door open. The bartender screen finds out this
                # order is dead by polling current_recipe.json -- which is
                # served by THIS process. Returning now would take the
                # server down with the news still in flight, leaving the
                # screen to work it out from the silence instead, several
                # polls later. The stock correction below happens inside
                # the wait, so it costs nothing.
                linger_for_screen(stop_event, dry_run)

                # The liquid that did come out is gone from the containers
                # whether or not the drink was finished, so the database is
                # corrected before giving up. Without this a machine that
                # fails often drifts steadily richer than the shelf.
                if update_inventory and not dry_run:
                    charge_for_failed_order(executed_steps, step)

                return False

        elif not dry_run and not is_start_step(step):
            # A manual or detect step changes the cup by an amount nothing
            # here knows: the operator tips in milk, and the cup leaves the
            # scale and comes back. So the baseline is taken afresh rather
            # than carried over, and the next pump step is measured from
            # whatever is really in the cup now.
            #
            # The start gate is the exception, and is excluded above. It
            # has just weighed the glass, and run_step has already made
            # that reading the baseline. Refreshing it here re-measured an
            # unchanged scale -- two seconds of settling for a pour that
            # never happened, plus the read -- and did it in the one place
            # the customer is waiting on the machine.
            refreshed = read_settled_gram(stop_event)
            cup_gram = run_state.get("cup_gram")

            if refreshed is None:
                print("  baseline not refreshed: the scale did not answer.")
            elif (
                cup_gram is not None
                and refreshed < cup_gram - CUP_RETURN_TOLERANCE_GRAM
            ):
                # Lighter than the empty cup, so the cup is not on the
                # scale -- almost always a manual step with the drink in
                # somebody's hand. Keeping the old baseline is right: the
                # detect step that follows will refresh it once the cup is
                # back, and a bad number here would fail the next pour.
                print(
                    f"  baseline kept: scale reads {refreshed:.1f}g, "
                    "the cup is not on it."
                )
            else:
                run_state["baseline_gram"] = refreshed
                print(f"  baseline now {refreshed:.1f}g.")

        step["status"] = STATUS_COMPLETED
        executed_steps.append(step)
        save_process(
            recipe_path,
            document,
            dry_run,
        )

        # Staff asked to stop. Honoured here, between steps, so the drink
        # is always left at a point the recipe describes.
        if not hold_while_paused(recipe_path, document, bridge,
                                 stop_event, dry_run):
            return finish_cancelled(
                recipe_path, document, bridge, executed_steps,
                update_inventory, dry_run,
            )

    document["completed_at"] = now_text()
    document["error"] = None
    save_process(
        recipe_path,
        document,
        dry_run,
    )
    print(
        f"[runner] Order {document['order_id']} completed."
    )

    # Hold the door open, exactly as a failure does.
    #
    # The bartender screen learns the drink is finished by reading
    # current_recipe.json -- served by THIS process. Returning here would
    # take the server down with the news still in flight: the screen would
    # never see completed_at, would decide the machine had gone quiet, and
    # would send the customer back to the store page with no thank-you at
    # all. That is the bug, and it is a race, so it looked intermittent.
    #
    # The inventory work below happens inside the wait, so this costs the
    # customer nothing -- the screen has already started its countdown by
    # the time the deduction finishes.
    linger_for_screen(stop_event, dry_run)

    if update_inventory and not dry_run:
        try:
            consume_inventory(executed_steps)
        except Exception as error:
            # The drink is already poured, so a database problem is
            # reported without turning the run into a failure.
            print(
                f"[inventory] Deduction failed: {error}"
            )

    return True


# ============================================================
# 8. COMMAND LINE
# ============================================================

# How long to keep serving after announcing a restart, so a screen can
# read it before this process dies.
#
# Sized for the SLOWER of the two readers: the bartender screen polls
# every 120 ms, but the store screen polls once a second, so the box lands
# within a second and the rest is reading time. Keep in step with
# STORE_RESTART_NOTICE_SECONDS in order/run_flow.py. It is the same trick
# order/run_flow.py uses for a cancel, and for the same reason: the
# customer is standing in front of a screen that is about to go blank, and
# a moment of warning is the difference between "the machine is coming
# back" and an error page with no explanation.
RESTART_NOTICE_SECONDS = 5.0


def restart_backend_if_idle(
    recipe_path: Path | None = None,
    document: dict[str, Any] | None = None,
) -> None:
    """Answer the panel's restart button, unless liquid is moving.

    While an order is open this process owns the button chip, so the idle
    watcher in panel_control/button_watch.py cannot see the press -- and
    an order that has stalled at a gate is precisely when somebody reaches
    for the button. So the press is answered here instead.

    Refused mid-pour: see POURING.
    """
    from panel_control.button_watch import RESTART_PANEL_ID, restart_backend

    if POURING.is_set():
        print(
            f"[executor] Service button {RESTART_PANEL_ID} ignored: "
            "the machine is pouring. Wait for the step to finish."
        )
        return

    announce_restart(recipe_path, document)
    restart_backend(f"nút {RESTART_PANEL_ID}")


def announce_restart(
    recipe_path: Path | None,
    document: dict[str, Any] | None,
) -> None:
    """Tell the screen the machine is going down, and give it time to read.

    Written into the order the screen is already polling rather than sent
    to it: this process is about to stop answering, so anything that
    needed a reply would arrive too late to be of use.
    """
    # BOTH screens, because either can be the one being watched. The
    # handoff normally moves the browser to the bartender screen when an
    # order starts, but staff walk back to the store screen mid-order, and
    # after the restart the store screen is where everyone lands anyway.
    # That is why this event breaks run_flow's usual "no store notice
    # after the handoff" rule: a restart ends with everyone there.
    warn_store_screen()

    if recipe_path is not None and document is not None:
        document["restarting_at"] = now_text()

        try:
            save_process(
                recipe_path,
                document,
                False,
            )
        except OSError as error:
            print(f"[executor] Could not announce the restart: {error}")

    sleep(RESTART_NOTICE_SECONDS)


def warn_store_screen() -> None:
    """Put the restart on the store screen, through run_flow's own writer.

    Imported here rather than at the top of the file: run_flow imports
    this module's package and pulls in the scanner and the database with
    it, none of which this process needs until somebody presses the
    button. If the import fails, the restart still happens -- a warning
    nobody could have read is not worth losing the recovery over.
    """
    try:
        from order.run_flow import (
            NOTICE_KIND_RESTART,
            SCAN_NOTICE_FILE,
            write_scan_notice,
        )

        write_scan_notice(
            SCAN_NOTICE_FILE,
            "Máy sẽ sẵn sàng lại sau vài giây. Quý khách vui lòng đợi.",
            "",
            title="Máy đang khởi động lại",
            kind=NOTICE_KIND_RESTART,
        )
        print("[executor] Warned the store screen about the restart.")
    except Exception as error:      # noqa: BLE001 - a notice, not a gate
        print(f"[executor] Could not warn the store screen: {error}")


def link_panel_failure(
    panel_stop_event: threading.Event,
    stop_event: threading.Event,
) -> threading.Thread:
    """End the order if the panel chip dies, for a recipe that needs it.

    panel_worker signals its own death by setting the event it was given.
    That used to be the order's stop_event, which is why the panel thread
    was only started for a recipe with a manual step: on a machine with no
    panel wired, an all-pump drink would have been killed by a chip it was
    never going to ask for.

    Now the panel gets its own event and this thread decides what it
    means. A recipe with a manual step still fails fast -- it is about to
    wait on buttons that will never light -- and one without simply loses
    a service button it can do nothing about.
    """
    def wait_and_link() -> None:
        panel_stop_event.wait()

        if stop_event.is_set():
            # Ordinary shutdown: main() sets stop_event first, then this
            # one, to bring the panel thread home.
            return

        print("[runner] Panel hardware stopped; ending the order.")
        stop_event.set()

    thread = threading.Thread(
        target=wait_and_link,
        name="panel-failure-link",
        daemon=True,
    )
    thread.start()
    return thread


def start_panel_thread(
    panel_command_queue: queue.Queue[tuple[str, object]],
    button_event_queue: queue.Queue[int],
    stop_event: threading.Event,
    recipe_path: Path | None = None,
    document: dict[str, Any] | None = None,
) -> threading.Thread:
    """Start the LED and button worker used by manual steps."""
    from panel_control.button_watch import RESTART_PANEL_ID
    from panel_control.panel import panel_worker

    thread = threading.Thread(
        target=panel_worker,
        args=(
            panel_command_queue,
            button_event_queue,
            stop_event,
            RESTART_PANEL_ID,
            lambda: restart_backend_if_idle(recipe_path, document),
        ),
        name="panel-thread",
        daemon=True,
    )
    thread.start()
    return thread


def create_gui_server(
    port: int,
    bridge: GuiBridge,
) -> ThreadingHTTPServer:
    """Serve the bartender screen and accept its one write.

    The screen is otherwise read-only: it polls current_recipe.json and
    renders whatever the machine wrote. POST /api/confirm is the single
    exception, releasing the gate the runner is blocked on.
    """
    project_dir = str(
        Path(__file__).resolve().parent.parent
    )

    class GuiHandler(SimpleHTTPRequestHandler):
        """Serve the screen's files and take its one write."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            """Serve everything relative to the project directory."""
            super().__init__(
                *args,
                directory=project_dir,
                **kwargs,
            )

        def translate_path(self, path: str) -> str:
            """Refuse anything outside the served directories.

            Loopback-only, so this is not the exposed copy -- but it is
            the same document root, and four handlers agreeing by accident
            is how the next one forgets. See configuration/served_paths.py.
            """
            return served_paths.guard(super().translate_path(path))

        def _send_json(
            self,
            status: int,
            payload: dict[str, object],
        ) -> None:
            """Answer one request with a JSON body."""
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header(
                "Content-Type",
                "application/json; charset=utf-8",
            )
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def end_headers(self) -> None:
            """Add the no-cache header to every response."""
            # The screen polls one file several times a second; a cached
            # copy would freeze it on whatever it read first.
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def _read_json(self) -> dict[str, Any]:
            """Read the request body, or an empty mapping if unusable."""
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return {}

            if length <= 0:
                return {}

            try:
                payload = json.loads(
                    self.rfile.read(length).decode("utf-8")
                )
            except (ValueError, UnicodeDecodeError):
                return {}

            return payload if isinstance(payload, dict) else {}

        def do_POST(self) -> None:
            """Route the screen's three writes to the waiting runner.

            /api/confirm         releases the place-the-glass gate.
            /api/pause           hold at the end of the current step.
            /api/resume          carry on with the next step.
            /api/cancel          abandon the order, with a reason.
            /api/process/button  lights one lamp on a manual step.
            /api/process/detect  asks for one cup check and waits for
                                 the runner's answer.
            """
            route = self.path.split("?")[0]

            if route == "/api/confirm":
                bridge.confirm_event.set()
                self._send_json(202, {"accepted": True})
                return

            if route == "/api/pause":
                bridge.resume_event.clear()
                bridge.pause_event.set()
                self._send_json(202, {"accepted": True})
                return

            if route == "/api/resume":
                bridge.pause_event.clear()
                bridge.resume_event.set()
                self._send_json(202, {"accepted": True})
                return

            if route == "/api/cancel":
                payload = self._read_json()

                with bridge.cancel_lock:
                    # First reason wins. A second tap while the machine is
                    # already stopping must not overwrite what the first
                    # person said.
                    if not bridge.cancel_event.is_set():
                        bridge.cancel_reason = str(
                            payload.get("reason") or "khac"
                        )[:64]
                        bridge.cancel_note = str(
                            payload.get("note") or ""
                        )[:500]

                # Set last, so the runner never wakes to an empty reason.
                bridge.cancel_event.set()
                self._send_json(202, {"accepted": True})
                return

            if route == "/api/process/button":
                payload = self._read_json()

                try:
                    panel = int(payload["panel"])
                    step_label = str(payload["step"])
                except (KeyError, TypeError, ValueError):
                    self._send_json(
                        400,
                        {"error": "step and panel are required"},
                    )
                    return

                try:
                    bridge.button_queue.put_nowait(
                        (step_label, panel)
                    )
                except queue.Full:
                    self._send_json(
                        503,
                        {"error": "the machine is not reading buttons"},
                    )
                    return

                self._send_json(202, {"accepted": True})
                return

            if route == "/api/process/detect":
                # The runner owns the load cell, so ask it and wait for
                # the answer rather than reading the hardware here.
                bridge.detect_done.clear()
                bridge.detect_request.set()

                if not bridge.detect_done.wait(
                    timeout=GUI_DETECT_TIMEOUT_SECONDS
                ):
                    self._send_json(
                        503,
                        {"error": "the machine did not answer in time"},
                    )
                    return

                # The numbers travel with the answer. The screen writes
                # "Chưa thấy ly — {a} / {b} g" from them, and without
                # them it rendered "— / —": a refusal that named neither
                # what the scale read nor what it wanted.
                sensor = bridge.detect_sensor or {}
                self._send_json(
                    200,
                    {
                        "detected": bool(bridge.detected),
                        "current_gram": sensor.get("current_gram"),
                        "min_gram": sensor.get("min_gram"),
                    },
                )
                return

            self._send_json(404, {"error": "route not found"})

        def log_message(self, *args: Any) -> None:
            """Stay quiet: polling would drown the runner's own output."""

    class GuiServer(ThreadingHTTPServer):
        """Threaded server that survives a quick stop and restart."""

        # Restarting the runner within a minute of stopping it would
        # otherwise fail while the old socket sits in TIME_WAIT.
        allow_reuse_address = True
        daemon_threads = True

    try:
        # Loopback, not 0.0.0.0. No browser reaches this server any more:
        # the bartender screen is served from store_gui/serve.py on the one
        # public port, and that server relays these controls here. Binding
        # it to the network would publish a second address that is only up
        # while a drink is pouring -- the thing that stranded pages on
        # "this site can't be reached" when they were sent to it directly.
        return GuiServer(
            ("127.0.0.1", port),
            GuiHandler,
        )
    except OSError as error:
        raise ProcessError(
            f"Cannot serve the screen on port {port}: {error}. "
            "Something else is already using it -- a "
            "'python3 -m http.server' left running is the usual cause. "
            f"Stop it, choose another port with --serve PORT, or run "
            "headless with --no-serve."
        ) from error


def parse_args() -> argparse.Namespace:
    """Read the command line options of this runner."""
    parser = argparse.ArgumentParser(
        description="Run every step of one process recipe file.",
    )
    parser.add_argument(
        "recipe",
        nargs="?",
        default=str(DEFAULT_RECIPE_PATH),
        help="Path to the process recipe file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan without touching pumps, panel or database.",
    )
    parser.add_argument(
        "--no-inventory",
        action="store_true",
        help="Do not deduct the used ingredients from the database.",
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Run every step again, including the ones already completed.",
    )
    parser.add_argument(
        "--serve",
        type=int,
        nargs="?",
        const=DEFAULT_GUI_PORT,
        default=DEFAULT_GUI_PORT,
        metavar="PORT",
        help=(
            f"Serve the bartender screen on PORT (default {DEFAULT_GUI_PORT}) "
            "and take its start button."
        ),
    )
    parser.add_argument(
        "--no-serve",
        dest="serve",
        action="store_const",
        const=None,
        help=(
            "Run headless. Without a screen nothing can press start, so "
            "the machine weighs the glass as soon as one appears."
        ),
    )
    parser.add_argument(
        "--step-delay",
        type=float,
        default=STEP_DELAY_SECONDS,
        metavar="SECONDS",
        help=(
            "Pause between two steps "
            f"(default {STEP_DELAY_SECONDS:g}s, 0 disables it)."
        ),
    )
    arguments = parser.parse_args()

    if arguments.step_delay < 0:
        parser.error("--step-delay cannot be negative")

    return arguments


def reset_progress(
    document: dict[str, Any],
) -> None:
    """Return every step to pending so the whole recipe runs again."""
    for step in document.get("steps", []):
        if not isinstance(step, dict):
            continue

        step["status"] = STATUS_PENDING

        for button in step.get("buttons", []):
            if isinstance(button, dict):
                button["lit"] = False

    document["order_id"] = None
    document["created_at"] = None
    document["completed_at"] = None
    document["error"] = None


def main() -> int:
    """Run one recipe file and return a shell-friendly exit code."""
    arguments = parse_args()
    recipe_path = Path(
        arguments.recipe
    )

    try:
        document = load_process(
            recipe_path
        )

        if arguments.restart:
            reset_progress(document)

        steps = validated_steps(
            document
        )
    except ProcessError as error:
        print(f"[runner] {error}")
        return 1

    stop_event = threading.Event()

    # The panel's own stop flag. Kept apart from the order's so that a
    # panel that fails -- unplugged, loose, wrong address -- does not by
    # itself end a drink that needs no panel. See link_panel_failure.
    panel_stop_event = threading.Event()
    bridge = GuiBridge()

    # A cancel from the screen has to reach the pumps, not just the loop.
    # stop_event is what run_pump_for_duration checks while it is counting
    # down, so setting it is what actually stops liquid mid-pour; waiting
    # for the step to end first would keep pouring a drink somebody has
    # already said they do not want.
    # No thread turns a cancel into stop_event any more. A cancel is
    # honoured where a pause is -- at the end of the current step -- so the
    # cup is never left holding an amount nobody chose, and the order ends
    # through finish_cancelled() rather than looking like a pump fault.
    # Ctrl+C remains the way to stop the machine dead.
    panel_command_queue: queue.Queue[tuple[str, object]] | None = None
    button_event_queue: queue.Queue[int] | None = None
    panel_thread: threading.Thread | None = None
    gui_server: ThreadingHTTPServer | None = None
    gui_thread: threading.Thread | None = None

    try:
        if arguments.serve is not None and not arguments.dry_run:
            gui_server = create_gui_server(
                arguments.serve,
                bridge,
            )
            gui_thread = threading.Thread(
                target=gui_server.serve_forever,
                name="gui-server",
                daemon=True,
            )
            gui_thread.start()
            print(
                "[runner] Bartender screen: "
                f"http://<this-machine>:{arguments.serve}"
                "/bartender_gui/index.html"
            )

        # Started for EVERY order, not just one with a manual step. This
        # thread is the only reader of the button chip while an order is
        # open -- run_flow pauses the idle watcher for the whole of it --
        # so without it panel button 14 cannot restart a machine that has
        # stalled on an all-pump drink, which is five of the seven on this
        # menu. See link_panel_failure for why that is now safe.
        if not arguments.dry_run:
            panel_command_queue = queue.Queue(
                maxsize=PANEL_COMMAND_QUEUE_SIZE,
            )
            button_event_queue = queue.Queue(
                maxsize=BUTTON_EVENT_QUEUE_SIZE,
            )
            panel_thread = start_panel_thread(
                panel_command_queue,
                button_event_queue,
                panel_stop_event,
                recipe_path,
                document,
            )

            if has_manual_step(steps):
                link_panel_failure(
                    panel_stop_event,
                    stop_event,
                )

        completed = run_process(
            recipe_path,
            document,
            panel_command_queue,
            button_event_queue,
            stop_event,
            arguments.dry_run,
            not arguments.no_inventory,
            arguments.step_delay,
            bridge if arguments.serve is not None else None,
        )

    except KeyboardInterrupt:
        print("\n[runner] Stopped by operator.")
        return 1

    except ProcessError as error:
        print(f"[runner] {error}")
        return 1

    finally:
        stop_event.set()
        # After stop_event, never before: link_panel_failure reads that
        # order to tell a shutdown from a chip that died.
        panel_stop_event.set()

        if panel_command_queue is not None:
            try:
                panel_command_queue.put_nowait(
                    ("clear", None)
                )
            except queue.Full:
                pass

        if panel_thread is not None:
            panel_thread.join(
                timeout=5.0
            )

        if gui_server is not None:
            gui_server.shutdown()
            gui_server.server_close()

        if gui_thread is not None:
            gui_thread.join(
                timeout=5.0
            )

    return 0 if completed else 1


if __name__ == "__main__":
    raise SystemExit(main())
