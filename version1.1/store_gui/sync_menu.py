"""Rebuild the store POS menu from the database.

WHAT THIS FILE IS
    store_gui/drinks-pos.js is a static page with no server behind it, so it
    cannot query MySQL. This script does the querying and writes what it
    finds to store_gui/menu-data.js, which the page loads before its own
    script. Run it whenever the menu, the recipes or the stock change.

THE FLOW OF ONE RUN
    1.  Read the drinks, their categories, their images and their prices.
    2.  Read every recipe row and keep the ingredients a customer can
        choose -- the boolean ones (a topping to tick) and the percentage
        ones (a dial like sugar). Those become that drink's options, so a
        drink only ever offers what its own recipe contains.
    3.  Read ingredient stock, and work out for each drink whether it can
        be poured at all.
    4.  Write menu-data.js as one assignment to window.MENU_DATA.

    The output is a .js file, not .json, on purpose: a page opened from
    file:// cannot fetch() a local JSON file -- the browser blocks it as a
    cross-origin request -- but it can always load a <script>.

WHY OPTIONS COME FROM THE RECIPE
    order/qr_to_recipe.py can drop or scale an ingredient the recipe
    already contains, but it cannot add one that is missing. A POS that
    offered Pearls on a drink whose recipe has no Pearls would charge for
    something the machine then silently would not add. Building each
    drink's option list from its own recipe rows makes that impossible.

WHAT "OUT OF STOCK" MEANS HERE
    A drink is orderable when drink.available is true (the staff are
    offering it) and drink.in_stock is true (every ingredient is above its
    threshold). The two are different switches and the page shows the
    difference: an unavailable drink is off the menu, an out-of-stock one
    is on the menu but cannot be poured. Either way the tile is visible
    and not clickable, so customers can see what exists.

    drink.in_stock is maintained by triggers in database.sql, so it is
    already correct when this script reads it.

RUNNING IT
    python3 -m store_gui.sync_menu           # write store_gui/menu-data.js
    python3 -m store_gui.sync_menu --print   # show it, write nothing
    python3 -m store_gui.sync_menu --interval 5    # keeps the menu fresh
    python3 -m order.run_flow                       # scanner + machine
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote


if __package__ in {None, ""}:
    project_dir = str(Path(__file__).resolve().parent.parent)

    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

from database.db_core import connect_database


STORE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = STORE_DIR.parent
OUTPUT_FILE = STORE_DIR / "menu-data.js"

# data_type values a customer can act on. Anything else (a weight) is poured
# from the recipe and is not a choice, so it never reaches the screen.
BOOLEAN_DATA_TYPES = {"boolean"}
PERCENTAGE_DATA_TYPES = {"percentage"}

# What a dial offers. These were once per-ingredient columns, but every row
# held the same values -- a dial is a share of what the recipe already pours,
# so 100% is always "as written" and the steps between are a presentation
# choice, not a property of the ingredient.
DIAL_DEFAULT_PERCENT = 100.0
DIAL_CHOICES = (0.0, 25.0, 50.0, 75.0, 100.0)

# The page lives in store_gui/, drink images in recipe/image/.
IMAGE_PREFIX = "../"

# What the strips do when store_setting has nothing to say -- which is
# the case on a database that has not taken the migrations yet. Enabled,
# because the operator's first sign that the feature exists should be the
# strip appearing once they tick a drink, not an empty admin panel that
# seems to do nothing.
# How a strip arranges its drinks.
#
#   carousel   one row of menu-style cards that scrolls sideways. The
#              default, and what a drinks kiosk normally does.
#   cinematic  full-bleed photo tiles, name and price ON the photo behind
#              a scrim -- no border, no white caption bar. The photo gets
#              the whole tile instead of sharing it with a shelf.
#   board      no cards at all: a round thumbnail, the name in display
#              type, dot leaders, the price. A wall menu.
#   bubble     round photos with soft double shadows and the caption
#              underneath. Claymorphism, which the design database names
#              as a secondary style for food service.
#   chart      the rank set large as the ground with the drink over it.
#              Exaggerated Minimalism.
#
# WHY chart IS NOT OFFERED ON THE FEATURED STRIP
#   Its whole design is the rank numeral. The featured strip is drinks an
#   operator ticked in no particular order, so a number in front of each
#   would be inventing a ranking the shop never made. The two sets below
#   are what each module may be set to.
STRIP_STYLES = ("carousel", "cinematic", "board", "bubble", "chart")
FEATURED_STYLES = ("carousel", "cinematic", "board", "bubble")
BESTSELLER_STYLES = STRIP_STYLES
STRIP_STYLE_DEFAULT = "carousel"

# The arrangements that stack their items down the tray, and so have a
# column count to answer. The other three run sideways and scroll, where
# "columns" is not a question -- the setting is still stored for them, so
# switching a strip away from board and back finds the choice intact, but
# it is not applied.
COLUMN_STYLES = ("board", "chart")

# One to three. Not four: at that width the chart's rank numeral and the
# board's leaders have nowhere left to go, and both stop being what they
# are. Three is already only sensible on a wide kiosk.
STRIP_COLUMN_RANGE = (1, 3)
STRIP_COLUMN_DEFAULT = 1

FEATURED_DEFAULTS = {
    "enabled": True,
    "title": "Món nổi bật",
    "style": STRIP_STYLE_DEFAULT,
    "columns": STRIP_COLUMN_DEFAULT,
}

BESTSELLER_DEFAULTS = {
    "enabled": True,
    "title": "Bán chạy nhất",
    # 30 days: all-time freezes whatever was popular in the first weeks
    # and never lets go, which stops being "bán chạy" and becomes a hall
    # of fame. A week, at this shop's volume, is a handful of cups and the
    # ranking would be noise.
    "windowDays": 30,
    "count": 6,
    "style": STRIP_STYLE_DEFAULT,
    "columns": STRIP_COLUMN_DEFAULT,
}

# Guard rails on what an operator may ask for. The window is bounded
# because "0 days" is an empty strip and "10 years" is the all-time list
# under a name that promises otherwise; the count because past about six a
# strip stops being a recommendation and becomes a second menu to read
# before reaching the first one.
BESTSELLER_WINDOW_RANGE = (1, 365)
BESTSELLER_COUNT_RANGE = (1, 12)

# The blocks the store screen stacks, and the order it falls back to.
# 'grid' is the menu itself: it can be moved but never dropped, because a
# drinks machine showing no drinks is not a state worth configuring.
LAYOUT_BLOCKS = ("featured", "bestseller", "grid")
LAYOUT_REQUIRED = "grid"
LAYOUT_DEFAULT = "featured,bestseller,grid"

# Picked by keyword when a drink has no image on disk. Presentation only --
# nothing downstream depends on it.
EMOJI_BY_KEYWORD = (
    ("coffee", "&#9749;"),
    ("tea", "&#127861;"),
    ("milk", "&#129371;"),
    ("soda", "&#127864;"),
    ("choco", "&#127851;"),
    ("straw", "&#127827;"),
    ("peach", "&#127825;"),
)
DEFAULT_EMOJI = "&#129380;"

DRINK_QUERY = """
    SELECT drink_id, drink_name, image, price, available, in_stock, featured
    FROM drink
    WHERE deleted_at IS NULL
    ORDER BY drink_id
"""

# Everything the screen is told about itself that is not a drink. Read
# whole rather than by key: the page decides what it recognises, so adding
# a setting is a row here and a default above -- not another query.
SETTING_QUERY = """
    SELECT setting_key, setting_value
    FROM store_setting
"""

# WHAT "BÁN CHẠY" ACTUALLY MEANS
#
#   status = 'used'   the only status that is a sale. 'expired' and
#                     'noqr_err' are tickets that never became a drink,
#                     and counting them would rank the machine's failures.
#
#   completed_at      when the drink was finished, not when the label was
#                     printed. It is also the column the admin report
#                     totals takings by, so the strip and the report can
#                     never disagree about which day a sale fell in.
#
#   the JOIN          a drink that is deleted, off the menu or out of
#                     stock is dropped here rather than later: a "bán
#                     chạy" card the machine cannot pour is the biggest
#                     picture on the screen doing nothing when tapped.
#
#   the tie-break     COUNT alone leaves drinks on equal sales in
#                     whatever order the engine felt like, which would
#                     reshuffle the strip on every rebuild for no reason a
#                     customer could see. Most recently sold wins, then
#                     drink_id, so the same sales always give the same row.
BESTSELLER_QUERY = """
    SELECT t.drink_id,
           COUNT(*) AS sold,
           MAX(t.completed_at) AS last_sold
    FROM order_ticket AS t
    JOIN drink AS d
      ON d.drink_id = t.drink_id
    WHERE t.status = 'used'
      AND t.completed_at >= NOW() - INTERVAL %s DAY
      AND d.deleted_at IS NULL
      AND d.available = 1
      AND d.in_stock = 1
    GROUP BY t.drink_id
    ORDER BY sold DESC, last_sold DESC, t.drink_id ASC
    LIMIT %s
"""

CATEGORY_QUERY = """
    SELECT category_id, category_name
    FROM category
    ORDER BY category_id
"""

MAPPING_QUERY = """
    SELECT drink_id, category_id
    FROM drink_category_mapping
"""

RECIPE_QUERY = """
    SELECT
        recipe.drink_id,
        recipe.step_no,
        recipe.target_gram,
        ingredient.ingredient_id,
        ingredient.ingredient_name,
        ingredient.data_type,
        ingredient.in_stock
    FROM recipe AS recipe
    JOIN ingredient AS ingredient
        ON ingredient.ingredient_id = recipe.ingredient_id
    JOIN drink AS drink
        ON drink.drink_id = recipe.drink_id
       AND drink.deleted_at IS NULL
    ORDER BY recipe.drink_id, recipe.step_no, ingredient.ingredient_id
"""


def emoji_for(name: str) -> str:
    """Pick a fallback glyph for a drink with no image."""
    lowered = name.lower()

    for keyword, glyph in EMOJI_BY_KEYWORD:
        if keyword in lowered:
            return glyph

    return DEFAULT_EMOJI


def image_url(image: str | None) -> str | None:
    """Turn a database image path into one the page can load.

    Paths are stored relative to the project root; the page is one
    directory down. A file that is not actually on disk returns None so
    the page falls back to a glyph rather than showing a broken image.
    """
    if not image:
        return None

    if not (PROJECT_DIR / image).is_file():
        return None

    # Percent-encode the path. Drink names have spaces in them -- "Peach
    # Tea.webp" -- and while a browser quietly encodes those when resolving
    # an <img src>, anything fetching the URL itself would not. Encoding it
    # here means the value in menu-data.js is a URL, not a filename that
    # only happens to work in one context. The slashes stay as slashes.
    return IMAGE_PREFIX + quote(image, safe="/")


def read_optional(cursor, query: str, what: str,
                  params: tuple = ()) -> list[dict] | None:
    """Run a query that a database from before a migration cannot answer.

    Returns None -- not an empty list -- when the table or column named
    in the query does not exist, so the caller can tell "the operator
    has not run the migration" apart from "there is nothing there".

    WHY THIS IS NOT JUST LET TO RAISE
        This script writes the file the kiosk reads. If it dies, the
        menu is not rebuilt at all: prices, stock and availability all
        stop updating on the shop floor over a feature nobody had
        switched on yet. Degrading to "no featured strip" keeps every
        other fact on that screen current, and the line printed here is
        what tells the operator why the strip never appears.
    """
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    except Exception as error:          # noqa: BLE001 - reported, not raised
        message = str(error).lower()

        if "doesn't exist" not in message and "unknown column" not in message:
            raise

        print(
            f"  ! {what} is not in this database -- run the migrations:\n"
            f"      mysql -u root -p beveragepos "
            f"< database/migrate_featured.sql\n"
            f"      mysql -u root -p beveragepos "
            f"< database/migrate_bestseller.sql",
            file=sys.stderr,
        )
        return None


def read_menu() -> dict:
    """Read everything the page needs, in one pass over the database."""
    connection = connect_database()

    try:
        cursor = connection.cursor(dictionary=True)

        drinks = read_optional(cursor, DRINK_QUERY, "drink.featured")

        if drinks is None:
            # Same menu, minus the one column this database has not got.
            # build_menu() reads it with .get(), so the drinks simply come
            # out unfeatured.
            cursor.execute(
                DRINK_QUERY.replace(", featured\n", "\n"),
            )
            drinks = cursor.fetchall()

        cursor.execute(CATEGORY_QUERY)
        categories = cursor.fetchall()

        cursor.execute(MAPPING_QUERY)
        mappings = cursor.fetchall()

        cursor.execute(RECIPE_QUERY)
        recipe_rows = cursor.fetchall()

        # Read BEFORE the bestseller query, which is parameterised by two
        # of these rows -- how far back to look and how many to keep.
        settings = read_optional(cursor, SETTING_QUERY, "store_setting")
        settings = settings or []
        wanted = bestseller_config(settings)

        bestsellers = read_optional(
            cursor,
            BESTSELLER_QUERY,
            "order_ticket",
            (wanted["windowDays"], wanted["count"]),
        )

        cursor.close()
    finally:
        connection.close()

    return {
        "drinks": drinks,
        "categories": categories,
        "mappings": mappings,
        "recipe_rows": recipe_rows,
        "settings": settings,
        "bestsellers": bestsellers or [],
    }


def settings_map(rows: list[dict]) -> dict[str, str]:
    """store_setting as a plain dict of strings."""
    return {
        str(row["setting_key"]): str(row["setting_value"])
        for row in rows
    }


def setting_flag(stored: dict, key: str, fallback: bool) -> bool:
    """A '1'/'0' setting, read leniently.

    Anything but an explicit '0' is on: this table is edited by hand as
    well as by the admin console, and 'true', 'yes' and '1' all plainly
    mean the same thing to whoever typed them.
    """
    if key not in stored:
        return fallback

    return stored[key].strip() != "0"


def setting_int(stored: dict, key: str, fallback: int,
                bounds: tuple[int, int]) -> int:
    """A whole-number setting, clamped to what the screen can act on.

    Out of range is CLAMPED rather than refused, because this reader runs
    on the shop floor: a nonsense value typed straight into MySQL should
    cost a sensible strip, not the whole menu rebuild. The admin console
    refuses it properly, up front, where somebody is there to read why.
    """
    low, high = bounds

    try:
        value = int(str(stored.get(key, "")).strip())
    except ValueError:
        return fallback

    return max(low, min(value, high))


def setting_style(stored: dict, key: str, allowed: tuple) -> str:
    """One strip's arrangement, or carousel if this module cannot draw it.

    `allowed` differs per module, so a featured_style of 'chart' -- which
    only a ranked strip can mean anything by -- lands on the default here
    rather than reaching the page.
    """
    value = stored.get(key, "").strip().lower()
    return value if value in allowed else STRIP_STYLE_DEFAULT


def featured_config(rows: list[dict]) -> dict:
    """The featured strip's settings, as the page will read them."""
    stored = settings_map(rows)
    title = stored.get("featured_title", "").strip()

    return {
        "enabled": setting_flag(stored, "featured_enabled",
                                FEATURED_DEFAULTS["enabled"]),
        "title": title or FEATURED_DEFAULTS["title"],
        "style": setting_style(stored, "featured_style", FEATURED_STYLES),
        "columns": setting_int(stored, "featured_columns",
                               STRIP_COLUMN_DEFAULT, STRIP_COLUMN_RANGE),
    }


def bestseller_config(rows: list[dict]) -> dict:
    """The bán-chạy strip's settings, as the page will read them.

    Validated here rather than on the page: menu-data.js is generated, so
    the screen is entitled to assume the window is a number it can print
    and the title is a string.
    """
    stored = settings_map(rows)
    title = stored.get("bestseller_title", "").strip()

    return {
        "enabled": setting_flag(stored, "bestseller_enabled",
                                BESTSELLER_DEFAULTS["enabled"]),
        "title": title or BESTSELLER_DEFAULTS["title"],
        "windowDays": setting_int(stored, "bestseller_window_days",
                                  BESTSELLER_DEFAULTS["windowDays"],
                                  BESTSELLER_WINDOW_RANGE),
        "count": setting_int(stored, "bestseller_count",
                             BESTSELLER_DEFAULTS["count"],
                             BESTSELLER_COUNT_RANGE),
        "style": setting_style(stored, "bestseller_style", BESTSELLER_STYLES),
        "columns": setting_int(stored, "bestseller_columns",
                               STRIP_COLUMN_DEFAULT, STRIP_COLUMN_RANGE),
    }


def layout_order(rows: list[dict]) -> list[str]:
    """The order the store screen stacks its blocks.

    REPAIRED, NOT REFUSED
        A stored list can be wrong in three ways -- a block this version
        does not know, a block named twice, or the menu itself missing --
        and every one of them arrives on a kiosk with nobody standing at
        it. So unknown and duplicate names are dropped, and any known
        block the list forgot is appended in its default order. 'grid'
        appended last is the important one: a layout without it would be
        a store screen with no drinks on it.
    """
    stored = settings_map(rows).get("layout_order", "").strip()
    wanted = [part.strip() for part in stored.split(",") if part.strip()]

    order: list[str] = []

    for block in wanted:
        if block in LAYOUT_BLOCKS and block not in order:
            order.append(block)

    for block in LAYOUT_DEFAULT.split(","):
        if block not in order:
            order.append(block)

    return order


def build_menu(raw: dict) -> dict:
    """Shape the database rows into what drinks-pos.js expects."""
    category_names = {
        int(row["category_id"]): row["category_name"]
        for row in raw["categories"]
    }

    categories_by_drink: dict[int, list[int]] = {}

    for row in raw["mappings"]:
        categories_by_drink.setdefault(
            int(row["drink_id"]), [],
        ).append(int(row["category_id"]))

    # Per drink: the ingredients a customer can choose, and any that are
    # out of stock. Weight-typed rows are poured from the recipe and are
    # not choices, but they still decide whether the drink can be made.
    options_by_drink: dict[int, list[dict]] = {}
    missing_by_drink: dict[int, list[str]] = {}
    seen_option: dict[int, set[int]] = {}
    toppings: dict[int, dict] = {}

    # An ingredient's total across every step of one drink. A dial needs it:
    # the payload carries the customer's chosen weight in grams, and this is
    # the 100% figure that choice is a share of.
    gram_totals: dict[tuple[int, int], float] = {}

    for row in raw["recipe_rows"]:
        key = (int(row["drink_id"]), int(row["ingredient_id"]))
        gram_totals[key] = gram_totals.get(key, 0.0) + float(row["target_gram"])

    for row in raw["recipe_rows"]:
        drink_id = int(row["drink_id"])
        ingredient_id = int(row["ingredient_id"])
        data_type = row["data_type"]
        in_stock = bool(row["in_stock"])

        if not in_stock:
            missing = missing_by_drink.setdefault(drink_id, [])
            if row["ingredient_name"] not in missing:
                missing.append(row["ingredient_name"])

        if data_type not in BOOLEAN_DATA_TYPES | PERCENTAGE_DATA_TYPES:
            continue

        # An ingredient poured at two steps is still one choice.
        if ingredient_id in seen_option.setdefault(drink_id, set()):
            continue

        seen_option[drink_id].add(ingredient_id)

        kind = (
            "boolean"
            if data_type in BOOLEAN_DATA_TYPES
            else "percentage"
        )

        option = {
            "ingredientId": ingredient_id,
            "name": row["ingredient_name"],
            "kind": kind,
            "inStock": in_stock,
        }

        if kind == "percentage":
            # A dial opens at 100% -- the amount the recipe already pours.
            option["default"] = DIAL_DEFAULT_PERCENT
            option["choices"] = list(DIAL_CHOICES)
            # recipe.target_gram is that 100% amount. The screen multiplies
            # it by the chosen percentage and puts the RESULT in the QR
            # code, so the machine reads a weight and never has to work one
            # out.
            option["gram"] = round(gram_totals[(drink_id, ingredient_id)], 2)
        else:
            # A topping starts ticked. Being in the recipe is the statement
            # that it belongs in the drink; unticking is what removes it.
            option["default"] = True

        options_by_drink.setdefault(drink_id, []).append(option)

        if kind == "boolean":
            toppings[ingredient_id] = {
                "ingredientId": ingredient_id,
                "name": row["ingredient_name"],
                "inStock": in_stock,
            }

    drinks = []

    for row in raw["drinks"]:
        drink_id = int(row["drink_id"])
        available = bool(row["available"])
        in_stock = bool(row["in_stock"])
        category_ids = categories_by_drink.get(drink_id, [])
        options = sorted(
            options_by_drink.get(drink_id, []),
            key=lambda item: item["ingredientId"],
        )
        missing = missing_by_drink.get(drink_id, [])

        if not available:
            reason = "Off the menu"
        elif not in_stock:
            reason = (
                "Out of " + ", ".join(missing) if missing else "Out of stock"
            )
        else:
            reason = None

        drinks.append({
            "drinkId": drink_id,
            "name": row["drink_name"],
            "price": float(row["price"]),
            "image": image_url(row["image"]),
            "emoji": emoji_for(row["drink_name"]),
            "categoryIds": category_ids,
            "category": (
                category_names.get(category_ids[0], "Other")
                if category_ids else "Other"
            ),
            "available": available,
            "inStock": in_stock,
            "orderable": available and in_stock,
            "unavailableReason": reason,
            # Read with .get() because a database from before
            # migrate_featured.sql has no such column -- see read_menu().
            "featured": bool(row.get("featured")),
            "options": options,
        })

    categories = [{
        "id": "all",
        "name": "All Menu",
        "count": sum(1 for d in drinks if d["orderable"]),
    }]

    for row in raw["categories"]:
        category_id = int(row["category_id"])
        count = sum(
            1 for d in drinks
            if category_id in d["categoryIds"] and d["orderable"]
        )
        categories.append({
            "id": f"c{category_id}",
            "name": row["category_name"],
            "count": count,
        })

    settings = raw.get("settings") or []
    bestseller = bestseller_config(settings)

    # The bestseller query already excludes anything unsellable, but it and
    # the drink list are two reads: between them a trigger can flip
    # in_stock. Checked against the list the page will actually draw from,
    # so a rank can never point at a card that is not there.
    sellable = {d["drinkId"] for d in drinks if d["orderable"]}

    return {
        # Milliseconds, not seconds. The store screen decides the menu has
        # changed by comparing this string, so two rebuilds inside one
        # second used to be indistinguishable -- and that is no longer a
        # theoretical gap: the admin console republishes on every edit, so
        # switching a drink off and on again, or a price change followed
        # straight away by a toggle, lands twice in the same second. The
        # screen would keep serving the first of the two for ever.
        "generatedAt": datetime.now().astimezone().isoformat(
            timespec="milliseconds",
        ),
        "categories": categories,
        "drinks": drinks,
        # The order the page stacks its blocks. The screen reads this
        # rather than holding an opinion, so moving the bán-chạy strip
        # above the menu is a row in store_setting and no code at all.
        "layout": layout_order(settings),

        # The featured strip: its settings, and the drinks it may draw.
        #
        # ONLY ORDERABLE DRINKS ARE LISTED
        #     A promotion for something the machine cannot pour is worse
        #     than no promotion: it is the biggest thing on the screen
        #     and tapping it does nothing. A featured drink that goes out
        #     of stock therefore drops out of the strip on the next
        #     rebuild and stays on the menu below with its reason badge,
        #     which is where a customer can see what happened to it.
        #
        #     This is why the page must not filter ITEMS by `featured`
        #     itself -- it would put the dead card back.
        "featured": {
            **featured_config(settings),
            "drinkIds": [
                d["drinkId"] for d in drinks
                if d["featured"] and d["orderable"]
            ],
        },

        # The bán-chạy strip. Unlike the featured one, nobody picks these:
        # drinkIds is what order_ticket says actually sold inside the
        # window, in rank order, and it is recomputed on every rebuild.
        #
        # NOT THE "Bestseller" CATEGORY
        #     That pill is hand-mapped in drink_category_mapping and
        #     nothing keeps it true -- checked on 2026-08-31 it held a
        #     drink that had never been sold, while the shop's two best
        #     sellers were not in it. This is the query that category's
        #     description always claimed to be.
        "bestseller": {
            **bestseller,
            "drinkIds": [
                int(row["drink_id"]) for row in raw.get("bestsellers") or []
                if int(row["drink_id"]) in sellable
            ],
            # What each of them sold, for the rank badge on the card. Keyed
            # by drink id as strings because this is about to be JSON, and
            # JSON object keys are strings whatever they started as.
            "sold": {
                str(row["drink_id"]): int(row["sold"])
                for row in raw.get("bestsellers") or []
            },
        },
        "toppings": sorted(
            toppings.values(),
            key=lambda item: item["ingredientId"],
        ),
    }


def render_js(menu: dict) -> str:
    """Render the menu as a single assignment to window.MENU_DATA."""
    return (
        "/* GENERATED FILE -- do not edit by hand.\n"
        "   Rebuild with:  python3 -m store_gui.sync_menu\n"
        f"   Generated {menu['generatedAt']} from the beveragepos database. */\n"
        "window.MENU_DATA = "
        + json.dumps(menu, ensure_ascii=False, indent=2)
        + ";\n"
    )


def report(menu: dict) -> None:
    """Print what was found, and anything the operator should act on."""
    print(f"{len(menu['drinks'])} drinks, "
          f"{len(menu['categories']) - 1} categories, "
          f"{len(menu['toppings'])} choosable toppings\n")

    for drink in menu["drinks"]:
        state = (
            "orderable" if drink["orderable"]
            else f"BLOCKED: {drink['unavailableReason']}"
        )
        options = ", ".join(
            f"{o['name']}({o['kind'][:4]})" for o in drink["options"]
        ) or "no options"
        image = "image" if drink["image"] else "emoji"
        print(f"  {drink['drinkId']:>2}  {drink['name']:<18} "
              f"${drink['price']:>6.2f}  {image:<5}  {state:<28} {options}")

    unpriced = [d["name"] for d in menu["drinks"] if d["price"] <= 0]

    if unpriced:
        print(f"\n  WARNING: {len(unpriced)} drink(s) priced 0.00 -- "
              "the till will ring up nothing:")
        print(f"    {', '.join(unpriced)}")
        print("    Set them with: "
              "UPDATE drink SET price = <amount> WHERE drink_id = <id>;")

    optionless = [d["name"] for d in menu["drinks"] if not d["options"]]

    if optionless:
        print(f"\n  NOTE: {len(optionless)} drink(s) have no choosable "
              "ingredient, so their detail panel shows no options:")
        print(f"    {', '.join(optionless)}")

    report_featured(menu)


def columns_note(config: dict) -> str:
    """" x2" when the column count is doing something, "" when it is not."""
    if config.get("style") not in COLUMN_STYLES:
        return ""

    columns = int(config.get("columns") or 1)
    return f" x{columns}" if columns > 1 else ""


def report_featured(menu: dict) -> None:
    """What the featured strip will do on the shop floor.

    Worth its own paragraph because every way the strip can end up
    invisible is a setting somebody chose on another screen, and none of
    them look like a fault from the kiosk -- the strip is simply not
    there. This is the one place all of them are said out loud.
    """
    featured = menu.get("featured") or {}
    shown = featured.get("drinkIds") or []
    picked = [d for d in menu["drinks"] if d["featured"]]
    held_back = [d["name"] for d in picked if not d["orderable"]]

    where = " > ".join(menu.get("layout") or [])

    print(f"\n  Page order: {where}")
    print(f"\n  Featured strip: {'on' if featured.get('enabled') else 'OFF'}"
          f" · {featured.get('style')}{columns_note(featured)}"
          f" · \"{featured.get('title')}\""
          f" · {len(shown)} of {len(picked)} picked drink(s) showing")

    if held_back:
        print("    Held back -- picked but not sellable right now: "
              f"{', '.join(held_back)}")

    if featured.get("enabled") and not shown:
        print("    Nothing to draw, so the strip stays hidden. "
              "Tick a sellable drink in the admin Menu page.")

    report_bestseller(menu)


def report_bestseller(menu: dict) -> None:
    """What the bán-chạy strip will hold, and why."""
    best = menu.get("bestseller") or {}
    ids = best.get("drinkIds") or []
    sold = best.get("sold") or {}
    names = {d["drinkId"]: d["name"] for d in menu["drinks"]}

    print(f"\n  Bestseller strip: {'on' if best.get('enabled') else 'OFF'}"
          f" · last {best.get('windowDays')} day(s)"
          f" · top {best.get('count')}"
          f" · {best.get('style')}{columns_note(best)}"
          f" · \"{best.get('title')}\""
          f" · {len(ids)} drink(s) qualify")

    for rank, drink_id in enumerate(ids, start=1):
        print(f"    {rank}. {names.get(drink_id, drink_id):<20} "
              f"{sold.get(str(drink_id), 0)} sold")

    if best.get("enabled") and not ids:
        print("    Nothing sold in that window, so the strip stays hidden. "
              "Widen it in the admin Menu page.")

    # The same drink in both strips is drawn twice, one above the other.
    # Legal, and sometimes wanted -- but it is never what somebody meant
    # to configure, so it is said out loud rather than left to be noticed
    # on the shop floor.
    both = [names.get(i, i) for i in ids
            if i in set((menu.get("featured") or {}).get("drinkIds") or [])]

    if both:
        print(f"\n  NOTE: {len(both)} drink(s) appear in BOTH strips, so "
              "they are drawn twice:")
        print(f"    {', '.join(str(n) for n in both)}")


def write_menu(path: Path, javascript: str) -> None:
    """Write menu-data.js atomically.

    The store screen polls this file for its generatedAt stamp, so it must
    never read a half-written one and conclude the menu is broken.
    """
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(javascript, encoding="utf-8")
    temporary.replace(path)
    print(f"\nĐã ghi {path}")


def menu_body(javascript: str) -> str | None:
    """The menu as sorted data, with its timestamp removed.

    Compared as DATA, not as text. render_js() writes the timestamp
    twice -- once in the header comment and once in the JSON -- so
    stripping one line still left every rebuild looking different, which
    is exactly the bug this function exists to prevent.

    None when the text cannot be parsed, which the caller treats as
    "assume it changed" and rewrites.
    """
    try:
        start = javascript.index("{")
        end = javascript.rindex("}") + 1
        data = json.loads(javascript[start:end])
    except (ValueError, TypeError):
        return None

    if not isinstance(data, dict):
        return None

    data.pop("generatedAt", None)
    return json.dumps(data, sort_keys=True, ensure_ascii=False)


def publish_menu(path: Path = OUTPUT_FILE,
                 menu: dict | None = None) -> bool:
    """Rebuild the snapshot, but write it only if anything really changed.

    WHY THE COMPARISON MATTERS
        The store screen decides the menu has changed by comparing
        generatedAt, and reloads itself when it differs. A rebuild that
        rewrote the file every time would therefore reload the customer's
        screen on a timer, mid-order, for ever -- while showing them
        exactly the same menu. The stamp has to move only when something
        a customer could notice has moved with it.

    When nothing changed the file's modification time is bumped anyway,
    so whoever asked "is this stale?" gets a fresh answer and does not
    rebuild again on the very next request.

    Pass `menu` when the caller has already built one -- the watch loop
    has, for its own log line, and reading the database a second time
    here would not only be wasted work: the two reads could disagree, and
    the line printed would describe a menu other than the one published.

    Returns True if the file was rewritten.
    """
    javascript = render_js(
        build_menu(read_menu()) if menu is None else menu
    )

    try:
        if path.exists():
            current = menu_body(path.read_text(encoding="utf-8"))
            fresh = menu_body(javascript)

            if current is not None and current == fresh:
                os.utime(path, None)
                return False
    except OSError:
        pass                      # unreadable: fall through and rewrite it

    write_menu(path, javascript)
    return True


def watch(output: Path, minutes: float) -> int:
    """Rebuild the menu on a timer until stopped.

    The store screen is a static snapshot: stock falls as drinks are poured
    and prices, images and availability change in the database, but nothing
    re-reads any of it. This is what keeps that snapshot honest.

    A failed rebuild is reported and the loop carries on -- a database that
    is briefly unreachable should not take the menu down with it, and the
    file already on disk stays valid in the meantime.
    """
    seconds = max(10.0, minutes * 60.0)
    print(f"\nTự cập nhật mỗi {minutes:g} phút. Ctrl+C để dừng.", flush=True)

    while True:
        try:
            time.sleep(seconds)
        except KeyboardInterrupt:
            print("\nĐã dừng tự cập nhật.")
            return 0

        try:
            menu = build_menu(read_menu())
        except Exception as error:
            print(f"[sync] Không đọc được database: {error}",
                  file=sys.stderr, flush=True)
            continue

        if not menu["drinks"]:
            print("[sync] Database không có món nào, giữ nguyên file cũ.",
                  file=sys.stderr, flush=True)
            continue

        # publish_menu, NOT write_menu: it compares the new snapshot with
        # the one on disk and leaves the file alone when only the stamp
        # would have moved. Writing unconditionally moved generatedAt on
        # every tick, and the store screen reloads itself whenever that
        # stamp changes -- so an idle screen was reloading every single
        # cycle, for ever, to be shown exactly the same menu. See
        # publish_menu's own docstring: this is the thing it exists to
        # prevent, and the loop was going around it.
        if not publish_menu(output, menu):
            continue

        blocked = [d["name"] for d in menu["drinks"] if not d["orderable"]]
        print(f"[sync] {menu['generatedAt']} -- "
              f"{len(menu['drinks']) - len(blocked)}/{len(menu['drinks'])} "
              f"món bán được"
              + (f"; hết: {', '.join(blocked)}" if blocked else ""),
              flush=True)


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a shell-friendly exit code."""
    parser = argparse.ArgumentParser(
        description="Rebuild store_gui/menu-data.js from the database.",
    )
    parser.add_argument(
        "--output", type=Path, default=OUTPUT_FILE,
        help=f"Where to write (default {OUTPUT_FILE}).",
    )
    parser.add_argument(
        "--print", dest="print_only", action="store_true",
        help="Print the generated file instead of writing it.",
    )
    parser.add_argument(
        "--interval", type=float, metavar="MINUTES",
        help=(
            "Keep running, rebuilding every MINUTES. Without this the "
            "script writes once and exits."
        ),
    )
    args = parser.parse_args(argv)

    try:
        menu = build_menu(read_menu())
    except Exception as error:
        print(f"Không đọc được database: {error}", file=sys.stderr)
        return 1

    if not menu["drinks"]:
        print("Database không có món nào.", file=sys.stderr)
        return 1

    javascript = render_js(menu)

    if args.print_only:
        print(javascript)
        return 0

    report(menu)
    write_menu(args.output, javascript)

    if args.interval is None:
        return 0

    return watch(args.output, args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
