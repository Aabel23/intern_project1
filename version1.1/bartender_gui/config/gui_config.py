"""Read, edit and expand configuration/gui_config.json.

This file is the contract between the Python machine code and the bartender
GUI. Python writes it; the GUI fetches it and runs from it.

Command line
------------
    python bartender_gui/config/gui_config.py show
    python bartender_gui/config/gui_config.py drinks
    python bartender_gui/config/gui_config.py set-pour   --drink 2 --step 1 --ingredient 1 --gram 60
    python bartender_gui/config/gui_config.py set-topping --panels 11 12 13
    python bartender_gui/config/gui_config.py set-ui     --key step_delay_ms --value 1500
    python bartender_gui/config/gui_config.py build      --drink 2 --out order/current_recipe.json
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


CONFIG_FILE = Path(__file__).resolve().parent / "gui_config.json"
PROJECT_DIR = CONFIG_FILE.parent.parent.parent


class ConfigError(RuntimeError):
    """Raised when gui_config.json is missing or inconsistent."""


# ----------------------------------------------------------------- load ----

def load(path: Path = CONFIG_FILE) -> dict[str, Any]:
    """Load and validate the configuration."""
    try:
        with path.open("r", encoding="utf-8") as file:
            config = json.load(file)
    except FileNotFoundError as error:
        raise ConfigError(f"Config not found: {path}") from error
    except json.JSONDecodeError as error:
        raise ConfigError(f"Invalid JSON in {path}: {error}") from error

    validate(config)
    return config


def save(config: dict[str, Any], path: Path = CONFIG_FILE) -> Path:
    """Validate then write the config atomically."""
    validate(config)
    temporary = path.with_suffix(path.suffix + ".tmp")

    with temporary.open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=2, ensure_ascii=False)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())

    os.replace(temporary, path)
    return path


def validate(config: dict[str, Any]) -> None:
    """Fail loudly on the mistakes that would break the GUI silently."""
    for key in ("ui", "ingredients", "panel_buttons", "gates", "drinks"):
        if key not in config:
            raise ConfigError(f"Missing top-level key: {key!r}")

    ingredients = config["ingredients"]
    gates = config["gates"]
    panels = config["panel_buttons"]

    # every gate a drink references must exist
    for drink in config["drinks"]:
        label = drink.get("name", drink.get("drink_id"))
        for index, step in enumerate(drink.get("steps", []), start=1):
            kind = step.get("type")

            if kind == "gate":
                if step.get("gate") not in gates:
                    raise ConfigError(
                        f"{label} step {index}: unknown gate {step.get('gate')!r}"
                    )
            elif kind == "pump":
                pours = step.get("pours") or []
                if not pours:
                    raise ConfigError(f"{label} step {index}: pump step has no pours")

                used: set[int] = set()
                for pour in pours:
                    ingredient = str(pour.get("ingredient"))
                    if ingredient not in ingredients:
                        raise ConfigError(
                            f"{label} step {index}: unknown ingredient {ingredient}"
                        )

                    pump = ingredients[ingredient].get("pump")
                    if pump is None:
                        raise ConfigError(
                            f"{label} step {index}: ingredient {ingredient} "
                            "has no pump and cannot be poured"
                        )
                    if pump in used:
                        raise ConfigError(
                            f"{label} step {index}: pump {pump} used twice in one step"
                        )
                    used.add(pump)

                    if float(pour.get("gram", 0)) <= 0:
                        raise ConfigError(
                            f"{label} step {index}: gram must be greater than zero"
                        )
            else:
                raise ConfigError(f"{label} step {index}: unknown type {kind!r}")

    # every panel a hardware gate needs must be defined
    for name, gate in gates.items():
        if gate.get("release") == "hardware":
            buttons = gate.get("buttons") or []
            if not buttons:
                raise ConfigError(f"gate {name!r}: hardware gate has no buttons")
            for panel in buttons:
                if str(panel) not in panels:
                    raise ConfigError(f"gate {name!r}: undefined panel button {panel}")


# ------------------------------------------------------------- editing ----

def find_drink(config: dict[str, Any], drink_id: int) -> dict[str, Any]:
    for drink in config["drinks"]:
        if int(drink["drink_id"]) == int(drink_id):
            return drink
    raise ConfigError(f"drink_id {drink_id} is not in the config")


def set_pour(
    config: dict[str, Any],
    drink_id: int,
    step_number: int,
    ingredient_id: int,
    gram: float,
) -> None:
    """Set (or add) one ingredient amount inside one pump step."""
    drink = find_drink(config, drink_id)
    steps = drink["steps"]

    if not 1 <= step_number <= len(steps):
        raise ConfigError(f"step {step_number} outside 1-{len(steps)}")

    step = steps[step_number - 1]
    if step.get("type") != "pump":
        raise ConfigError(f"step {step_number} is a gate, not a pump step")

    for pour in step["pours"]:
        if int(pour["ingredient"]) == int(ingredient_id):
            pour["gram"] = float(gram)
            return

    step["pours"].append({"ingredient": int(ingredient_id), "gram": float(gram)})


def set_topping_buttons(
    config: dict[str, Any],
    panels: list[int],
    gate_name: str = "topping",
) -> None:
    """Choose which physical panel buttons a hardware gate waits for."""
    gate = config["gates"].get(gate_name)
    if gate is None:
        raise ConfigError(f"unknown gate {gate_name!r}")
    if gate.get("release") != "hardware":
        raise ConfigError(f"gate {gate_name!r} is not a hardware gate")

    for panel in panels:
        if str(panel) not in config["panel_buttons"]:
            raise ConfigError(f"panel {panel} is not defined in panel_buttons")

    gate["buttons"] = [int(p) for p in panels]


def set_ui(config: dict[str, Any], key: str, value: Any) -> None:
    if key not in config["ui"]:
        raise ConfigError(f"unknown ui key {key!r}; known: {sorted(config['ui'])}")
    config["ui"][key] = value


# -------------------------------------------------- runtime expansion ----

def build_current_recipe(
    config: dict[str, Any],
    drink_id: int,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Expand a configured drink into the runtime shape the GUI consumes.

    The start gate is prepended automatically, exactly as the GUI simulator
    does, so the machine never pours before a cup is under the nozzles.
    """
    drink = find_drink(config, drink_id)
    ingredients = config["ingredients"]
    panels = config["panel_buttons"]
    gates = config["gates"]
    now = datetime.now().isoformat(timespec="seconds")

    source: list[dict[str, Any]] = [{"type": "gate", "gate": "start"}]
    source.extend(drink["steps"])

    steps: list[dict[str, Any]] = []
    for number, raw in enumerate(source, start=1):
        if raw["type"] == "gate":
            gate = json.loads(json.dumps(gates[raw["gate"]]))  # deep copy

            buttons = []
            for panel in gate.get("buttons", []):
                buttons.append(
                    {
                        "panel": int(panel),
                        "label": panels[str(panel)]["label"],
                        "lit": False,
                    }
                )
            if buttons:
                gate["buttons"] = buttons

            steps.append(
                {
                    "step_number": number,
                    "step_type": "manual",
                    "gate": gate,
                    "pump_step": [],
                    "panel_ids": [b["panel"] for b in buttons],
                    "status": "pending",
                    "error": None,
                }
            )
            continue

        items = []
        for pour in raw["pours"]:
            key = str(pour["ingredient"])
            spec = ingredients[key]
            items.append(
                {
                    "pump": spec["pump"],
                    "ingredient_id": int(key),
                    "ingredient_name": spec["name"]["en"],
                    "base_gram": float(pour["gram"]),
                    "gram": float(pour["gram"]),
                    "poured_gram": 0,
                    "enabled": True,
                    "status": "pending",
                    "error": None,
                }
            )

        steps.append(
            {
                "step_number": number,
                "step_type": "pump",
                "pump_step": items,
                "panel_ids": sorted(i["pump"] for i in items),
                "status": "pending",
                "error": None,
            }
        )

    return {
        "order_id": uuid4().hex,
        "protocol_version": "1.3",
        "sku": drink["drink_id"],
        "drink_id": drink["drink_id"],
        "name": drink["name"],
        "image": drink.get("image"),
        "source_recipe_file": "configuration/gui_config.json",
        "status": "waiting_confirm",
        "current_step": None,
        "error": None,
        "options": options if options is not None else drink.get("options", {}),
        "created_at": now,
        "updated_at": now,
        "steps": steps,
    }


# ------------------------------------------------------------------ CLI ----

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FlexMix GUI configuration")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("show", help="Print a summary of the config")
    sub.add_parser("drinks", help="List drinks and their steps")

    p = sub.add_parser("set-pour", help="Set one ingredient amount in a pump step")
    p.add_argument("--drink", type=int, required=True)
    p.add_argument("--step", type=int, required=True)
    p.add_argument("--ingredient", type=int, required=True)
    p.add_argument("--gram", type=float, required=True)

    p = sub.add_parser("set-topping", help="Set which panel buttons a gate waits for")
    p.add_argument("--panels", type=int, nargs="+", required=True)
    p.add_argument("--gate", default="topping")

    p = sub.add_parser("set-ui", help="Change one ui setting")
    p.add_argument("--key", required=True)
    p.add_argument("--value", required=True)

    p = sub.add_parser("build", help="Expand a drink into a runtime recipe")
    p.add_argument("--drink", type=int, required=True)
    p.add_argument("--out", type=Path)

    args = parser.parse_args(argv)
    config = load()

    if args.command == "show":
        print(f"version           : {config.get('version')}")
        print(f"ingredients       : {len(config['ingredients'])}")
        print(f"panel buttons     : {sorted(int(k) for k in config['panel_buttons'])}")
        print(f"gates             : {', '.join(config['gates'])}")
        print(f"drinks            : {len(config['drinks'])}")
        for key, value in config["ui"].items():
            print(f"  ui.{key:<22}: {value}")
        return 0

    if args.command == "drinks":
        for drink in config["drinks"]:
            print(f"\n[{drink['drink_id']}] {drink['name']}")
            for number, step in enumerate(drink["steps"], start=1):
                if step["type"] == "gate":
                    print(f"   {number}. GATE  {step['gate']}")
                else:
                    parts = ", ".join(
                        f"{config['ingredients'][str(x['ingredient'])]['name']['en']}"
                        f" {x['gram']}g"
                        for x in step["pours"]
                    )
                    print(f"   {number}. PUMP  {parts}")
        return 0

    if args.command == "set-pour":
        set_pour(config, args.drink, args.step, args.ingredient, args.gram)
        save(config)
        print(f"drink {args.drink} step {args.step}: "
              f"ingredient {args.ingredient} = {args.gram} g")
        return 0

    if args.command == "set-topping":
        set_topping_buttons(config, args.panels, args.gate)
        save(config)
        print(f"gate {args.gate!r} now waits for panels {args.panels}")
        return 0

    if args.command == "set-ui":
        raw = args.value
        try:
            value: Any = json.loads(raw)
        except json.JSONDecodeError:
            value = raw
        set_ui(config, args.key, value)
        save(config)
        print(f"ui.{args.key} = {value!r}")
        return 0

    if args.command == "build":
        recipe = build_current_recipe(config, args.drink)
        text = json.dumps(recipe, indent=2, ensure_ascii=False)
        if args.out:
            out = args.out if args.out.is_absolute() else PROJECT_DIR / args.out
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text + "\n", encoding="utf-8")
            print(f"wrote {out}  ({len(recipe['steps'])} steps)")
        else:
            print(text)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
