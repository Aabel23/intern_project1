"""Turn the MySQL recipes into the steps the machine can run.

WHAT THIS FILE IS
    The bridge from the database to a runnable order. MySQL is where a
    recipe is edited; this module compiles one drink into the step list
    order/process_runner.py executes.

    It no longer writes files. It used to export recipe/menu.json and a
    recipe/<Drink>.json per drink, but nothing read them: the machine
    builds the recipe in memory at scan time, because the QR code carries
    the customer's own choices and a pre-built file cannot know them.
    order/qr_to_recipe.py calls get_recipe_rows(), build_drinks() and
    build_process_document() directly and writes the one file that
    matters -- order/current_recipe.json.

THE FLOW OF ONE ORDER
    1.  RECIPE_QUERY joins drink, recipe and ingredient. It is a LEFT
        JOIN on nothing: gpio now lives on the ingredient row itself.
    2.  build_drinks() groups the rows by drink and step, splitting each
        step by ingredient.type:
            PUMP    -> dispensed by a pump on ingredient.gpio (a BCM pin)
            MANUAL  -> added by hand and acknowledged on the panel
                       button at ingredient.gpio (a panel position 0-15)
    3.  build_process_document() expands one drink into ordered steps:
            a pump step for the pumped ingredients,
            then, if the step has hand-added ingredients, a manual step
            followed by a detect step, because the cup leaves the scale
            to be topped and the machine must see it come back.
    4.  duration_for_gram() converts each target gram into pump seconds
        using that pump's own calibration:
            duration = (gram - dead_gram) / gram_per_sec
        The recipe carries the seconds, not the grams, so the machine and
        the bartender screen run off one clock. Grams stay in the file
        for inventory only.

WHY BUILDING A RECIPE CAN FAIL
    A pump cannot deliver less than its own dead zone, so a target below
    it raises here rather than shipping a recipe that would crash the
    executor mid-drink. A MANUAL ingredient with no panel position, or a
    PUMP ingredient with no pin, is rejected the same way.
"""

from collections import OrderedDict
import json
from pathlib import Path
import re
from typing import Any

from mysql.connector import Error

from configuration.configuration import PUMP_CALIB_FILE

try:
    from .db_core import (
        close_database_resources,
        connect_database,
        gpio_number,
        mysql_number,
        recalculate_thresholds,
    )
    from .inventory_service import refresh_drink_instock
except ImportError:
    from db_core import (
        close_database_resources,
        connect_database,
        gpio_number,
        mysql_number,
        recalculate_thresholds,
    )
    from inventory_service import refresh_drink_instock


# ============================================================
# 1. DATABASE QUERIES
# ============================================================

PROCESS_SCHEMA = "flexmix.process/1"

INGREDIENT_TYPE_PUMP = "PUMP"
INGREDIENT_TYPE_MANUAL = "MANUAL"

GPIO_TO_PUMP = {
    26: 1,
    15: 2,
    21: 3,
    20: 4,
    16: 5,
    12: 6,
    13: 7,
    6: 8,
    5: 9,
    14: 10,
}

# Vietnamese labels for the bilingual names used by the process format.
# An ingredient missing here falls back to its English database name.
INGREDIENT_NAME_VI = {
    1: "Nước",
    2: "Trà",
    3: "Cà phê",
    4: "Siro đào",
    5: "Siro dâu",
    6: "Soda",
    7: "Đường",
    8: "Sữa",
    9: "Kem",
    10: "Sô cô la",
    11: "Dâu",
    12: "Đá",
    13: "Trân châu",
}

# An ingredient with no pump is added by hand and acknowledged on the panel.
# Its panel button carries the same number as its ingredient_id.
MANUAL_STEP_TITLE = {
    "vi": "Lấy ly ra và cho thêm nguyên liệu",
    "en": "Take the cup out and add the ingredients",
}
MANUAL_STEP_DETAIL = {
    "vi": (
        "Nhấc ly khỏi bàn cân. Cho từng nguyên liệu vào ly, "
        "mỗi lần cho xong bấm đúng nút của nó trên máy."
    ),
    "en": (
        "Lift the cup off the scale. Add each ingredient and press "
        "its own button on the machine."
    ),
}
DETECT_STEP_TITLE = {
    "vi": "Đặt ly trở lại máy",
    "en": "Put the cup back on the machine",
}
DETECT_STEP_DETAIL = {
    "vi": "Đặt ly lên bàn cân, rồi bấm nút bên dưới để máy chạy tiếp.",
    "en": (
        "Put the cup on the scale, then press the button below "
        "to continue."
    ),
}
# The wording matches the cup_back gate in bartender_gui/config/gui_config.json
# so the simulator and the real machine say the same thing.
DETECT_STEP_CONFIRM = {
    "vi": "Đã đặt ly — chạy tiếp",
    "en": "Cup is in place — continue",
}

MENU_QUERY = """
    SELECT
        drink.drink_id,
        drink.drink_name,
        drink.image,
        drink.available,
        drink.in_stock

    FROM drink AS drink

    WHERE drink.deleted_at IS NULL

    ORDER BY drink.drink_id
"""


# Steps a person performs, keyed by the same (drink_id, step_no) the pump
# rows use so the two sets interleave on one numbering. LEFT JOIN is not
# wanted here: a drink with no action steps simply returns no rows.
ACTION_QUERY = """
    SELECT drink_id,
           step_no,
           media_src,
           title_vi,
           title_en,
           detail_vi,
           detail_en,
           confirm_vi,
           confirm_en,
           cup_returns
    FROM recipe_action
    ORDER BY drink_id, step_no
"""

RECIPE_QUERY = """
    SELECT
        drink.drink_id,
        drink.drink_name,
        drink.image,

        -- The glass this drink is served in. LEFT JOIN, not JOIN: a drink
        -- with no glass set yet must still be pourable, so the columns
        -- come back NULL rather than the drink dropping out of the menu.
        glass.glass_id,
        glass.glass_name,
        glass.art AS glass_art,

        -- How the drink is built and on what ice. Same LEFT JOIN reasoning
        -- as glass: reference data for the person, absent until somebody
        -- fills it in, and never a reason for a drink to drop out.
        drink_type.drink_type_id,
        drink_type.type_name,
        drink_type.art AS drink_type_art,
        drink_type.method,
        drink_type.detail AS drink_type_detail,

        drink.garnish,

        recipe.step_no,
        recipe.target_gram,

        ingredient.ingredient_id,
        ingredient.ingredient_name,
        ingredient.type,
        ingredient.data_type,
        ingredient.gpio

    FROM drink AS drink

    LEFT JOIN glass AS glass
        ON glass.glass_id = drink.glass_id

    LEFT JOIN drink_type AS drink_type
        ON drink_type.drink_type_id = drink.drink_type_id

    JOIN recipe AS recipe
        ON recipe.drink_id = drink.drink_id

    JOIN ingredient AS ingredient
        ON ingredient.ingredient_id = recipe.ingredient_id

    WHERE drink.deleted_at IS NULL

    ORDER BY
        drink.drink_id,
        recipe.step_no,
        ingredient.gpio
"""


# ============================================================
# 1b. GRAM -> PUMP SECONDS
# ============================================================

def load_pump_calibration() -> dict[str, Any]:
    """Read the same calibration table the pump control library uses."""
    try:
        with open(PUMP_CALIB_FILE, encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as error:
        raise FileNotFoundError(
            f"Pump calibration not found: {PUMP_CALIB_FILE}. "
            "Run pump_control/calib_pump.py first."
        ) from error


def duration_for_gram(
    pump_number: int,
    gram: float,
    pump_calibration: dict[str, Any],
) -> float:
    """Convert one target amount into pump seconds: t = (gram - b) / a."""
    key = f"pump_{pump_number}"
    calibration = pump_calibration.get(key)

    if calibration is None:
        raise ValueError(
            f"Pump {pump_number} is not calibrated in {PUMP_CALIB_FILE}."
        )

    gram_per_sec = float(
        calibration["gram_per_sec"]
    )
    dead_gram = float(
        calibration["dead_gram"]
    )

    if gram_per_sec <= 0:
        raise ValueError(
            f"Pump {pump_number} has an invalid gram_per_sec."
        )

    duration = (float(gram) - dead_gram) / gram_per_sec

    # pump_control rejects a non-positive duration, so an amount below the
    # dead zone must fail here instead of shipping an unrunnable recipe.
    if duration <= 0:
        raise ValueError(
            f"Pump {pump_number} cannot deliver {float(gram):.2f}g "
            f"because its dead zone is {dead_gram:.2f}g."
        )

    return round(
        duration,
        3,
    )


def bilingual_name(
    ingredient_id: int,
    english_name: str,
) -> dict[str, str]:
    """Build the {"vi", "en"} label pair used by the process format."""
    return {
        "vi": INGREDIENT_NAME_VI.get(
            ingredient_id,
            english_name,
        ),
        "en": english_name,
    }


# ============================================================
# 4. READ RECIPE ROWS FROM DATABASE
# ============================================================

def get_recipe_rows(cursor) -> list[dict[str, Any]]:
    """Read one row per drink, step and ingredient."""
    cursor.execute(RECIPE_QUERY)
    return cursor.fetchall()


def get_action_rows(cursor) -> list[dict[str, Any]]:
    """Read one row per action step.

    Tolerates the table not being there: a database that predates the
    migration should still pour drinks, just without action steps.
    """
    try:
        cursor.execute(ACTION_QUERY)
    except Exception:      # noqa: BLE001 - an old schema is not an error
        return []

    return cursor.fetchall()


def attach_actions(
    drinks: dict[int, dict[str, Any]],
    action_rows: list[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    """Hang each action row on its drink, keyed by step number.

    Rows for a drink with no poured ingredients are dropped: build_drinks
    only knows about drinks that reached it through RECIPE_QUERY, and a
    drink that pours nothing has nothing for the machine to do.
    """
    for row in action_rows:
        drink_id = int(row["drink_id"])

        if drink_id not in drinks:
            continue

        drinks[drink_id]["actions"][int(row["step_no"])] = row

    return drinks


# ============================================================
# 7. BUILD DRINK -> STEP -> PUMP
# ============================================================

def build_drinks(
    rows: list[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    """Group recipe rows by drink and step, keeping pump and manual apart."""
    drinks: OrderedDict[int, dict[str, Any]] = OrderedDict()

    for row in rows:
        drink_id = int(row["drink_id"])
        step_no = row["step_no"]
        raw_gpio = row["gpio"]
        ingredient_id = int(
            row["ingredient_id"]
        )
        gram = mysql_number(
            row["target_gram"]
        )

        if drink_id not in drinks:
            drinks[drink_id] = {
                "drink_id": drink_id,
                "drink_name": row["drink_name"],
                "image": row.get("image"),
                # Filled by attach_actions() after this pass. Kept on the
                # drink rather than the step because an action carries no
                # ingredient, so no RECIPE_QUERY row ever creates its step.
                "actions": {},
                # None all the way through when no glass is set, which is
                # what the bartender screen reads as "skip the glass step".
                "glass": (
                    {
                        "id": int(row["glass_id"]),
                        "name": row.get("glass_name"),
                        "art": row.get("glass_art"),
                    }
                    if row.get("glass_id") is not None
                    else None
                ),
                # Same rule as glass: None all the way through when no
                # build method is set, and the screen shows one prep fact
                # fewer rather than an empty one.
                #
                # Plain strings, not {"vi", "en"} pairs. The screen's
                # localised() takes either, and these four facts are
                # Vietnamese-only by decision -- see the drink_type table
                # comment in database.sql.
                "drink_type": (
                    {
                        "id": int(row["drink_type_id"]),
                        "art": row.get("drink_type_art"),
                        "name": row.get("type_name"),
                        "method": row.get("method"),
                        "detail": row.get("drink_type_detail"),
                    }
                    if row.get("drink_type_id") is not None
                    else None
                ),
                "garnish": row.get("garnish") or None,
                "steps": OrderedDict(),
            }

        steps = drinks[drink_id]["steps"]

        if step_no not in steps:
            steps[step_no] = {
                "step_number": step_no,
                "pump_step": [],
                "manual_step": [],
            }

        ingredient_type = str(
            row.get("type", INGREDIENT_TYPE_PUMP)
        ).upper()

        # A MANUAL ingredient is added by hand, and its gpio column holds
        # the panel position of its LED and button, not a pump pin.
        if ingredient_type == INGREDIENT_TYPE_MANUAL:
            if raw_gpio is None:
                raise ValueError(
                    f"Ingredient {ingredient_id} "
                    f"({row['ingredient_name']}) is MANUAL but has no "
                    "panel position in its gpio column."
                )

            panel_id = gpio_number(raw_gpio)

            if not 0 <= panel_id <= 15:
                raise ValueError(
                    f"Ingredient {ingredient_id} "
                    f"({row['ingredient_name']}) has panel {panel_id}, "
                    "outside the supported range 0-15."
                )

            steps[step_no]["manual_step"].append(
                {
                    "panel": panel_id,
                    "ingredient_id": ingredient_id,
                    "ingredient_name": row["ingredient_name"],
                    "gram": gram,
                }
            )
            continue

        if raw_gpio is None:
            raise ValueError(
                f"Ingredient {ingredient_id} ({row['ingredient_name']}) "
                "is PUMP but has no gpio pin."
            )

        # "G26" -> 26. gpio_number() also accepts a bare number, so this
        # reads a migrated database and an un-migrated one alike.
        gpio = gpio_number(raw_gpio)

        if gpio is None:
            raise ValueError(
                f"Ingredient {ingredient_id} ({row['ingredient_name']}) "
                f"has an unreadable hardware slot: {raw_gpio!r}"
            )

        try:
            pump_number = GPIO_TO_PUMP[gpio]
        except KeyError as error:
            raise ValueError(f"Unsupported pump GPIO: {gpio}") from error

        steps[step_no]["pump_step"].append(
            {
                "pump": pump_number,
                "ingredient_id": ingredient_id,
                "ingredient_name": row["ingredient_name"],
                "gram": gram,
                "source": gpio,
            }
        )

    return dict(drinks)


# ============================================================
# 7. BUILD ONE current_recipe.json DOCUMENT
# ============================================================

def build_pump_step(
    step: dict[str, Any],
    step_label: str,
    step_order: int,
    pump_calibration: dict[str, Any],
) -> dict[str, Any]:
    """Build one automatic pump step in the process format."""
    pumps = sorted(
        step["pump_step"],
        key=lambda pump: int(pump["pump"]),
    )

    return {
        "step": step_label,
        "order": step_order,
        "type": "pump",
        "status": "pending",
        "pumps": [
            {
                "pump": pump["pump"],
                "ingredient_id": pump["ingredient_id"],
                "ingredient_name": bilingual_name(
                    pump["ingredient_id"],
                    pump["ingredient_name"],
                ),
                "gram": pump["gram"],
                "duration_sec": duration_for_gram(
                    pump["pump"],
                    pump["gram"],
                    pump_calibration,
                ),
            }
            for pump in pumps
        ],
    }


def build_manual_step(
    step: dict[str, Any],
    step_label: str,
    step_order: int,
) -> dict[str, Any]:
    """Build one hand-added step whose buttons are confirmed on the panel."""
    manual_items = sorted(
        step["manual_step"],
        key=lambda item: int(item["panel"]),
    )

    return {
        "step": step_label,
        "order": step_order,
        "type": "manual",
        "owner": "gui",
        "status": "pending",
        "icon": "hand",
        "title": MANUAL_STEP_TITLE,
        "detail": MANUAL_STEP_DETAIL,
        "buttons": [
            {
                "panel": item["panel"],
                "ingredient_id": item["ingredient_id"],
                "label": bilingual_name(
                    item["ingredient_id"],
                    item["ingredient_name"],
                ),
                "gram": item["gram"],
                "lit": False,
            }
            for item in manual_items
        ],
    }


def build_action_step(
    action: dict[str, Any],
    step_label: str,
    step_order: int,
) -> dict[str, Any]:
    """Build one step the bartender performs while a clip loops on screen.

    owner is "gui" for the same reason a manual step's is: the machine
    cannot tell when a person has finished shaking, so only the on-screen
    press ends it.
    """
    def bilingual(vi_key: str, en_key: str) -> dict[str, str]:
        """Fall back to Vietnamese when no English was written.

        An empty string would blank the card for an English reader; the
        Vietnamese they cannot read is still better than nothing there.
        """
        vietnamese = str(action.get(vi_key) or "").strip()
        english = str(action.get(en_key) or "").strip()

        return {"vi": vietnamese, "en": english or vietnamese}

    step = {
        "step": step_label,
        "order": step_order,
        "type": "action",
        "owner": "gui",
        "status": "pending",
        "icon": "hand",
        "media": {
            "src": str(action["media_src"]),
        },
        "title": bilingual("title_vi", "title_en"),
        "detail": bilingual("detail_vi", "detail_en"),
    }

    confirm = bilingual("confirm_vi", "confirm_en")

    # Left out entirely when nobody wrote one, so the screen falls back to
    # its own default label rather than showing an empty button.
    if confirm["vi"]:
        step["confirm"] = confirm

    return step


def build_detect_step(
    step_label: str,
    step_order: int,
) -> dict[str, Any]:
    """Build the cup-back gate that follows a hand-added step.

    NO `sensor` BLOCK, DELIBERATELY
        A sensor block is what tells the bartender screen that the MACHINE
        is the one watching, and it is what this step used to carry. It
        made the step un-passable: the runner compares against the glass
        weighed at the start gate, so a load cell reading low -- or not
        answering -- refuses a cup that is plainly on the scale, and the
        screen offers no way round a refusal. The drink could only be
        cancelled.

        Without one, the screen renders an ordinary confirm gate and the
        operator's press releases the step, exactly as on a manual step.
        See run_detect_step() in order/process_runner.py for the other
        half, and mapStepStatus() in bartender_gui/js/guide.js for how the
        shape is read.

        The `detect` type stays: it is what tells the runner this is the
        step where the cup comes back, which is still where the pour
        baseline is retaken.
    """
    return {
        "step": step_label,
        "order": step_order,
        "type": "detect",
        "status": "pending",
        # The operator resolves this one now, so it declares itself the
        # way every other gate they answer does. See PROCESS_SCHEMA.md.
        "owner": "gui",
        "icon": "cup",
        "title": DETECT_STEP_TITLE,
        "detail": DETECT_STEP_DETAIL,
        "confirm": DETECT_STEP_CONFIRM,
    }


def build_process_steps(
    drink_data: dict[str, Any],
    pump_calibration: dict[str, Any],
) -> list[dict[str, Any]]:
    """Expand one drink into pump, action, manual and detect steps."""
    actions = drink_data.get("actions") or {}

    # An action pours nothing, so RECIPE_QUERY produced no row for its
    # step number and build_drinks never made an entry for it. Without
    # these placeholders the loop below would simply never reach it, and
    # the step would vanish from a recipe that clearly asks for it.
    by_number: dict[int, dict[str, Any]] = {
        int(step["step_number"]): step
        for step in drink_data["steps"].values()
    }

    for number in actions:
        by_number.setdefault(
            int(number),
            {
                "step_number": int(number),
                "pump_step": [],
                "manual_step": [],
            },
        )

    steps = sorted(
        by_number.values(),
        key=lambda step: int(step["step_number"]),
    )

    process_steps: list[dict[str, Any]] = []

    for step in steps:
        step_label = str(
            step["step_number"]
        )

        if step["pump_step"]:
            process_steps.append(
                build_pump_step(
                    step,
                    step_label,
                    len(process_steps) + 1,
                    pump_calibration,
                )
            )

        action = actions.get(int(step["step_number"]))

        if action is not None:
            process_steps.append(
                build_action_step(
                    action,
                    f"{step_label}a",
                    len(process_steps) + 1,
                )
            )

            # Only when the glass was lifted off. A garnish at the end
            # leaves it standing on the scale, and a detect step there
            # would stop the drink to confirm something already true.
            if int(action.get("cup_returns", 1)):
                process_steps.append(
                    build_detect_step(
                        f"{step_label}ad",
                        len(process_steps) + 1,
                    )
                )

        if not step["manual_step"]:
            continue

        # The cup leaves the scale for a hand-added step, so the machine
        # must detect it again before any later pump step runs.
        process_steps.append(
            build_manual_step(
                step,
                f"{step_label}m",
                len(process_steps) + 1,
            )
        )
        process_steps.append(
            build_detect_step(
                f"{step_label}d",
                len(process_steps) + 1,
            )
        )

    return process_steps


def build_process_document(
    drink_data: dict[str, Any],
    image: str | None,
    pump_calibration: dict[str, Any],
) -> dict[str, Any]:
    """Build one recipe template in the order/current_recipe.json format."""
    return {
        "schema": PROCESS_SCHEMA,
        "drink_id": drink_data["drink_id"],
        "order_id": None,
        "drink_name": drink_data["drink_name"],
        "image": image,
        # Reference data for the person, not an instruction to the machine:
        # nothing in process_runner reads it. It rides in the recipe because
        # that is the one document that reaches the bartender screen.
        "glass": drink_data.get("glass"),
        # The ice and the build method, and the drink's own garnish. Read
        # by nobody but the bartender screen, and carried here for the same
        # reason as the glass: the recipe is the one document that reaches
        # it.
        "drink_type": drink_data.get("drink_type"),
        "garnish": drink_data.get("garnish"),
        "error": None,
        "created_at": None,
        "updated_at": None,
        "completed_at": None,
        "options": {},
        "steps": build_process_steps(
            drink_data,
            pump_calibration,
        ),
    }
