"""Serve the admin console and the database behind it.

WHY THIS IS ITS OWN SERVER AND NOT PART OF store_gui/serve.py
    The store server faces the customer. Everything it can do -- issue a
    ticket, draw a QR, print a label, start an order -- is something a
    customer is meant to cause. The endpoints here change the menu, the
    prices and the recipes, and putting those on the same port would mean
    the tablet a customer taps is one URL away from rewriting the menu.

    A separate port is not authentication and does not pretend to be. It
    is a smaller thing that is still worth having: the two jobs can be
    stopped, started, firewalled and bound to different interfaces
    independently. Run this one with --local while the store screen serves
    the room, and the admin API is not on the network at all.

WHAT IT SERVES
    The project directory, like store_gui/serve.py, so the pages under
    admin_gui/ load with their relative paths intact -- plus:

        GET  /api/menu             every drink and category, as the page
                                   renders them
        POST /api/drink/available  the "Đang bán" switch
        POST /api/drink/price      the price cell
        POST /api/drink/featured   the star: put a drink in the featured
                                   strip on the customer screen
        POST /api/store/featured   that strip's own settings -- on/off
                                   and its heading
        POST /api/store/bestseller the bán-chạy strip: on/off, heading,
                                   how far back it looks, how many it shows
        POST /api/store/layout     the order the store screen stacks its
                                   blocks in
        GET  /api/recipe-editor    one drink's recipe, and the ingredients
                                   that can be put in it
        POST /api/recipe           save a drink and its recipe
        GET  /api/ingredients      the stock page: every ingredient, how
                                   full it is, which pump it is on
        POST /api/ingredient/refill   top a container back up
        POST /api/ingredient/refill-all  fill every container to its max
        POST /api/ingredient/save     add one, or change what one is
        POST /api/ingredient/delete   remove one no recipe uses

WHERE THE MENU SHAPE COMES FROM
    store_gui/sync_menu.py, imported rather than copied. It already turns
    these tables into the vocabulary the POS speaks -- orderable, inStock,
    unavailableReason -- and the admin screen showing a drink as sellable
    while the POS calls it out of stock would be a bug nobody could see
    from either page. One query, one shape, two readers.

AUTHENTICATION
    There is none, and admin_gui/login.js is not it -- that gate lives in
    the browser and anything can talk to this port directly. Before this
    runs anywhere a stranger can reach, it needs a real session check on
    every handler below. Until then: --local, or a machine on a network
    you trust.

RUNNING IT
    python3 -m admin_gui.serve                # port 8100, whole LAN
    python3 -m admin_gui.serve --local        # this machine only
    python3 -m admin_gui.serve --port 9000
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from datetime import date, datetime, timedelta
from typing import Any
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse


ADMIN_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ADMIN_DIR.parent

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from admin_gui import auth
from admin_gui import permissions
from configuration import net_addresses
from configuration import machine
from configuration import served_paths
from printer import spool
# Imported for the ticket tag alone -- tag_ticket()/split_ticket()/
# ticket_like() are the one definition of how a fault names its ticket,
# and this file is the reader half of it. Spelling the format out again
# here would work until somebody edited one of the two copies, and the
# failure would be a link that silently matches nothing.
from database import error_log
from configuration import order_mode
from configuration import display_mode
from database.db_core import (
    close_database_resources,
    connect_database,
    gpio_number,
    gpio_slot,
    mysql_number,
)
from store_gui.sync_menu import (
    BESTSELLER_COUNT_RANGE,
    BESTSELLER_DEFAULTS,
    BESTSELLER_WINDOW_RANGE,
    FEATURED_DEFAULTS,
    LAYOUT_BLOCKS,
    LAYOUT_REQUIRED,
    BESTSELLER_STYLES,
    COLUMN_STYLES,
    FEATURED_STYLES,
    STRIP_COLUMN_RANGE,
    OUTPUT_FILE as MENU_DATA_FILE,
    bestseller_config,
    build_menu,
    emoji_for,
    featured_config,
    image_url,
    layout_order,
    publish_menu,
    read_menu,
)


DEFAULT_PORT = machine.ADMIN_STANDALONE_PORT
ADMIN_PAGE = "/admin_gui/login.html"

MENU_PATH = "/api/menu"
AVAILABLE_PATH = "/api/drink/available"
PRICE_PATH = "/api/drink/price"
# Which drinks the shop is pushing, and how the strip that shows them is
# set up. Two endpoints because they are two different things: one is a
# property of a drink, the other is a property of the screen.
FEATURED_PATH = "/api/drink/featured"
FEATURED_CONFIG_PATH = "/api/store/featured"
# The bán-chạy strip's own settings, and the order the store screen
# stacks its blocks in. Three endpoints rather than one "store settings"
# blob because they are three different decisions, made on three
# different controls, and a partial write to a shared blob is how one of
# them silently reverts another.
BESTSELLER_CONFIG_PATH = "/api/store/bestseller"
LAYOUT_PATH = "/api/store/layout"
DELETE_PATH = "/api/drink/delete"
RESTORE_PATH = "/api/drink/restore"
PURGE_PATH = "/api/drink/purge"
BIN_PATH = "/api/drink/bin"
IMAGES_PATH = "/api/images"
IMAGE_UPLOAD_PATH = "/api/image"

# Where drink photos live. Both screens reach them as ../recipe/image/...
IMAGE_DIR = PROJECT_DIR / "recipe" / "image"

# A photo for a menu tile. Generous enough for a phone picture, small
# enough that a mistake cannot fill the Pi's card.
IMAGE_MAX_BYTES = 5 * 1024 * 1024

# How much of an over-sized upload to read and throw away so the refusal
# can be delivered as a proper 413. Beyond this the connection is simply
# closed -- nobody uploading 64 MB to a drinks machine is doing it by
# accident.
IMAGE_DRAIN_LIMIT = 64 * 1024 * 1024

# Recognised by CONTENT, not by the name the browser sent. A file called
# .webp that is really something else would be served back to every
# customer screen, so the first bytes decide -- and anything unrecognised
# is refused rather than stored.
IMAGE_SIGNATURES = (
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
)

MEDIA_UPLOAD_PATH = "/api/media"
MEDIA_LIST_PATH = "/api/medias"

# Where the action steps' instruction clips live. Kept apart from
# recipe/image/ so a clip can never be offered as a menu tile photo, and
# so clearing one set never touches the other. store_gui/serve.py serves
# PROJECT_DIR, so both screens reach these as ../recipe/media/...
MEDIA_DIR = PROJECT_DIR / "recipe" / "media"

# Bigger than a photo because this is a few seconds of video. A 6-second
# 1280x960 MP4 lands near 2 MB; 12 MB leaves room for a clip shot without
# any compression, while still refusing anything that would fill the card.
MEDIA_MAX_BYTES = 12 * 1024 * 1024

# A GIF this size will still play, but it is ten times the file an MP4
# needs for the same seconds and it is capped at 256 colours. Warned
# about rather than refused: the bartender usually already has the GIF.
MEDIA_GIF_WARN_BYTES = 4 * 1024 * 1024

# Same rule as IMAGE_SIGNATURES: the first bytes decide, never the name.
# MP4 is the odd one -- its marker sits at offset 4, after the box size,
# so it is matched separately in sniff_media().
MEDIA_MP4_BRANDS = (
    b"isom", b"iso2", b"mp41", b"mp42", b"avc1", b"M4V ", b"dash",
)
EDITOR_PATH = "/api/recipe-editor"
REPORT_PATH = "/api/report"
ORDERS_PATH = "/api/report/orders"
RECIPE_PATH = "/api/recipe"
INGREDIENTS_PATH = "/api/ingredients"
INGREDIENT_REFILL_PATH = "/api/ingredient/refill"
INGREDIENT_REFILL_ALL_PATH = "/api/ingredient/refill-all"
INGREDIENT_SAVE_PATH = "/api/ingredient/save"
INGREDIENT_DELETE_PATH = "/api/ingredient/delete"
ERRORS_PATH = "/api/errors"
# Deleting from the fault log. Its own endpoint AND its own permission
# area -- see delete_errors() and permissions.AREA_ERRORS_PURGE.
ERRORS_DELETE_PATH = "/api/errors/delete"
TICKETS_PATH = "/api/tickets"
TICKET_STATUS_PATH = "/api/ticket/status"
# Another COPY of a label already sold -- never another code. See
# reprint_ticket() for why that distinction is the whole safety of it.
TICKET_REPRINT_PATH = "/api/ticket/reprint"
# The one endpoint that does NOT need a session -- it is how you get one.
LOGIN_PATH = "/api/admin/login"

# Accounts. Reachable by an owner and nobody else -- see AREA_ROLES.
USERS_PATH = "/api/users"
USER_SAVE_PATH = "/api/user/save"
USER_PASSWORD_PATH = "/api/user/password"
USER_ROLE_PATH = "/api/user/role"
USER_ACTIVE_PATH = "/api/user/active"
USER_DELETE_PATH = "/api/user/delete"

# Which areas each role holds. Same AREA_USERS gate as the accounts
# themselves: whoever may create an owner may also decide what a role is.
PERMISSIONS_PATH = "/api/permissions"
PERMISSIONS_SAVE_PATH = "/api/permissions/save"

# Who am I, according to the server? Every signed-in account may ask, and
# the console asks on load: the role in sessionStorage came from a login
# that may be twelve hours old, and a demotion since then has to reach the
# screen without waiting for the holder to log out.
WHOAMI_PATH = "/api/admin/whoami"

# Changing your OWN password. Separate from USER_PASSWORD_PATH on purpose:
# that one is an owner acting on somebody else and is gated as such, while
# this one every account may use on itself and on nothing else. One
# endpoint doing both would have to decide which it was from the body, and
# the body is the part a stranger writes.
MY_PASSWORD_PATH = "/api/admin/password"

# Which buttons the customer screen offers -- see configuration/order_mode.py.
#
# READING IT NEEDS NO SESSION, WRITING IT DOES
#     The customer screen is a tablet nobody logs in to, and it has to know
#     which buttons to draw. So the GET is answered before require_login()
#     -- see dispatch_get(). It gives away nothing: the screen shows the
#     answer to anybody standing in front of it either way.
#
#     The POST is gated like the page that offers it (AREA_REFILL, which is
#     what unlocks the "mode" screen), so who may change how the shop sells
#     is the same question as who may open the page that says so.
ORDER_MODE_PATH = "/api/order-mode"

# The kiosk panel's resolution. Three paths rather than one because
# applying and keeping are deliberately separate steps -- see
# handle_display_apply() for why a screen setting on a machine with no
# keyboard has to be able to undo itself.
DISPLAY_PATH = "/api/display"
DISPLAY_APPLY_PATH = "/api/display/apply"
DISPLAY_KEEP_PATH = "/api/display/keep"

GET_PATHS = (MENU_PATH, EDITOR_PATH, REPORT_PATH, ORDERS_PATH,
             BIN_PATH, IMAGES_PATH, MEDIA_LIST_PATH, INGREDIENTS_PATH,
             ERRORS_PATH, TICKETS_PATH, USERS_PATH, WHOAMI_PATH,
             PERMISSIONS_PATH, ORDER_MODE_PATH, DISPLAY_PATH)
POST_PATHS = (AVAILABLE_PATH, PRICE_PATH, RECIPE_PATH, DELETE_PATH,
              RESTORE_PATH, PURGE_PATH, INGREDIENT_REFILL_PATH,
              INGREDIENT_REFILL_ALL_PATH,
              INGREDIENT_SAVE_PATH, INGREDIENT_DELETE_PATH,
              TICKET_STATUS_PATH, TICKET_REPRINT_PATH,
              ERRORS_DELETE_PATH,
              FEATURED_PATH, FEATURED_CONFIG_PATH,
              BESTSELLER_CONFIG_PATH, LAYOUT_PATH,
              USER_SAVE_PATH, USER_PASSWORD_PATH, USER_ROLE_PATH,
              USER_ACTIVE_PATH, USER_DELETE_PATH, MY_PASSWORD_PATH,
              PERMISSIONS_SAVE_PATH, ORDER_MODE_PATH,
              DISPLAY_APPLY_PATH, DISPLAY_KEEP_PATH)

# The most drinks the featured strip may hold. Not a database constraint
# -- it is a statement about a screen. Past about six the strip stops
# being a recommendation and becomes a second menu the customer has to
# read before reaching the first one, and on a kiosk that is the whole
# fold gone. Refused server-side so the number cannot be got round by
# opening two admin tabs and ticking in both.
FEATURED_MAX = 6

# How many rows either log page will hand over at once. Both tables grow
# without bound and neither page paginates, so this is what stops a year of
# faults being serialised into one response.
LOG_PAGE_LIMIT = 300

# The statuses a ticket may be moved to by hand, matching the CHECK
# constraint on order_ticket.status. Held here rather than read from the
# database so an unknown value is refused before it reaches SQL.
TICKET_STATUSES = ("unused", "in_progress", "used", "expired", "noqr_err")

# The only two statuses this console may write, and the ones it refuses to
# move a ticket OUT of. See set_ticket_status() for why each list is what
# it is.
STATUS_SETTABLE = ("unused", "used")
STATUS_LOCKED = ("noqr_err",)

# max_gram IS A COLUMN ON ingredient. It used to be this JSON file, and
# the file is still read once, to carry old figures into the column.
#
# WHY IT MOVED
#   It is a per-row fact about a row in that table -- this bottle holds
#   this much -- and keeping it beside the table instead of in it meant
#   the two could disagree. A file keyed by ingredient_id has no foreign
#   key: delete an ingredient and its entry stayed behind, and the next
#   ingredient to be handed that auto-increment id inherited a capacity
#   somebody declared for something else. delete_ingredient() had to
#   remember to sweep up after itself, and "fill every bottle" had to read
#   a file and a table and hope they were talking about the same thirteen
#   rows. The column cannot drift from the row it is part of, and a refill
#   is now one UPDATE against one table.
#
#   It also let the database state the rule. ck_ingredient_max_gram says
#   max_gram IS NULL OR max_gram > 0, so a zero-sized bottle -- which
#   would divide by zero on screen and make "fill this" mean "empty this"
#   -- is refused by the column rather than by whoever remembers to check.
#
# WHAT THE FILE IS NOW
#   Only a source for adopt_capacity_file(), which moves whatever it holds
#   into the column once and then renames it aside. Nothing reads it after
#   that, and nothing has ever written it except this console.
LEGACY_MAX_GRAM_FILE = PROJECT_DIR / "configuration" / "ingredient_capacity.json"

# What a container with no declared max is assumed to hold, in grams. Only
# ever a starting point -- the stock page sets the real figure per
# ingredient, and says on screen which of the two a percentage came from.
DEFAULT_MAX_GRAM = 10000.0

# DECIMAL(10,2), same as the price column and refused here for the same
# reason: a typo should come back as a sentence, not a driver error.
AMOUNT_MAX = 99999999.99

# The pins the ingredient table may name. Wider than the Pi's header on
# purpose -- panel_control addresses its own board by small numbers, and
# this endpoint is not the place that knows which is which.
GPIO_MAX = 63

# DECIMAL(10,2) in the drink table. Rejected here as well so the page gets
# a sentence rather than a driver error, and so a typo in a price cell
# cannot be written as something the column silently rounds.
PRICE_MAX = 99999999.99

# The page is a snapshot of a table that other things write -- the stock
# triggers, the runner deducting ingredients. Never let a proxy or the
# browser hold one.
NEVER_CACHE_SUFFIXES = (".html", ".js", ".css", ".json")


class AdminError(Exception):
    """A request that cannot be carried out, with a sentence for the page."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


# --------------------------------------------------------------------------
# reading
# --------------------------------------------------------------------------
def menu_payload() -> dict:
    """Every drink and category, in the shape admin_gui/menu-store.js wants.

    build_menu() is the POS's own view of these tables, so the two screens
    agree on what "orderable" means. The admin screen needs three things
    the POS does not: the numeric category_id (the POS only ever uses the
    'c1' string, but a save has to name a real row), the drink id as an
    SKU, and the raw image path rather than the POS's ../ prefixed URL --
    the admin edits the stored value, not the link.
    """
    # read_menu() already filters the bin out -- see its DRINK_QUERY --
    # so a binned drink cannot reach the admin table or the POS.
    menu = build_menu(read_menu())
    stored_images = read_image_paths()

    return {
        "categories": [
            {
                **category,
                "database_id": (
                    int(category["id"][1:])
                    if category["id"].startswith("c") else None
                ),
            }
            for category in menu["categories"]
        ],
        "drinks": [
            {
                # The QR payload's SKU field IS the drink id, so the number
                # shown under each name is the number in the customer's
                # code. drink.sku was dropped from the schema; this is what
                # replaced it in practice.
                "id": drink["drinkId"],
                "sku": drink["drinkId"],
                "name": drink["name"],
                "emoji": drink["emoji"],
                "price": drink["price"],
                # Two forms, because they are used for two things: the
                # editor edits the stored path, and the table needs
                # something a browser can actually load from one
                # directory down -- percent-encoded, since drink names
                # have spaces in them.
                "image": stored_images.get(drink["drinkId"]),
                "imageUrl": image_page_url(stored_images.get(
                    drink["drinkId"])),
                "cat": drink["category"],
                "catId": (
                    f"c{drink['categoryIds'][0]}"
                    if drink["categoryIds"] else None
                ),
                "categoryIds": drink["categoryIds"],
                "available": drink["available"],
                "ingredientStock": drink["inStock"],
                "soldOut": not drink["orderable"],
                "unavailableReason": drink["unavailableReason"],
                "featured": drink["featured"],
            }
            for drink in menu["drinks"]
        ],
        # Exactly what the store screen was handed, so the admin panel
        # cannot describe a page different from the one on the shop floor.
        # The caps and ranges travel too, rather than being hard-coded in
        # the browser: the numbers in the sentences an operator reads and
        # the numbers the server enforces must be the same numbers.
        "featuredConfig": menu["featured"],
        "featuredMax": FEATURED_MAX,
        "bestsellerConfig": menu["bestseller"],
        "bestsellerWindowRange": list(BESTSELLER_WINDOW_RANGE),
        "bestsellerCountRange": list(BESTSELLER_COUNT_RANGE),
        "layout": menu["layout"],
        "layoutBlocks": list(LAYOUT_BLOCKS),
        # Per module, not one list: the console must not offer the
        # chart on a strip the server will refuse it for.
        "featuredStyles": list(FEATURED_STYLES),
        "bestsellerStyles": list(BESTSELLER_STYLES),
        # Which arrangements the column count actually does anything for,
        # so the console can hide a control that would do nothing.
        "columnStyles": list(COLUMN_STYLES),
        "columnRange": list(STRIP_COLUMN_RANGE),
    }


def image_page_url(stored: str | None) -> str | None:
    """Turn a stored image path into one an admin page can load.

    None when there is no image, and None when the file named is not
    actually on disk -- the page falls back to the drink's glyph, which
    is better than a broken-image icon in every row.
    """
    if not stored:
        return None

    if not (PROJECT_DIR / stored).is_file():
        return None

    return "../" + quote(stored, safe="/")


def read_image_paths() -> dict[int, str | None]:
    """The image column as stored, keyed by drink.

    build_menu() rewrites the path for the POS -- prefixed with ../, and
    None when the file is not on disk -- but the editor edits the column,
    so it has to see what is actually in it.
    """
    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT drink_id, image FROM drink")
        return {int(r["drink_id"]): r["image"] for r in cursor.fetchall()}
    finally:
        close_database_resources(cursor, connection)


def editor_payload(drink_id: int | None) -> dict:
    """One drink's recipe, plus every ingredient that may go in a recipe.

    EVERY ingredient, deliberately -- not only the ones with a pump. The
    recipe table already holds MANUAL rows (drink 6 pours Milk and Cream
    as a hand-added step), and an editor that hides them would rewrite
    those rows into whichever ingredient its <select> happened to land on.
    Showing them is what makes saving safe: what the editor displays is
    exactly what the recipe contains, so writing back what it displays
    cannot lose anything.
    """
    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            # Pumped ingredients first: they are what most steps are made
            # of, so they belong at the top of every <select> rather than
            # below six toppings because 'MANUAL' sorts before 'PUMP'.
            "SELECT ingredient_id, ingredient_name, type, data_type, gpio "
            "FROM ingredient "
            "ORDER BY (type = 'PUMP') DESC, ingredient_id"
        )
        ingredients = [
            {
                "ingredient_id": int(row["ingredient_id"]),
                # Labelled, because "Milk" in a pump list and "Milk" in a
                # manual list mean different things to whoever is building
                # a recipe: one is poured, one is handed to the bartender.
                "ingredient_name": (
                    row["ingredient_name"]
                    if str(row["type"]).upper() == "PUMP"
                    else f"{row['ingredient_name']} (thủ công)"
                ),
                "type": row["type"],
                "data_type": row["data_type"],
            }
            for row in cursor.fetchall()
        ]

        # Offered by the recipe editor's glass picker. Ordered by
        # sort_order so the list reads the way a bar thinks about glasses
        # rather than by primary key.
        cursor.execute(
            "SELECT glass_id, glass_name, art, capacity_ml FROM glass "
            "ORDER BY sort_order, glass_id"
        )
        glasses = [
            {
                "glass_id": int(row["glass_id"]),
                "glass_name": row["glass_name"],
                "art": row["art"],
                "capacity_ml": row["capacity_ml"],
            }
            for row in cursor.fetchall()
        ]

        # The build methods, for the picker beside the glass one. Same
        # ordering rule: sort_order, so the list reads the way a bar thinks
        # about ice rather than by primary key.
        # drink_count comes along because `detail` is editable from the
        # recipe editor and is SHARED: typing in it while editing one
        # drink changes what every other drink of that type shows. The
        # count is what makes that visible before the save rather than
        # after -- "áp dụng cho 12 món" is a warning a number can give and
        # a sentence cannot.
        cursor.execute(
            "SELECT t.drink_type_id, t.type_name, t.art, "
            "t.method, t.detail, "
            "COUNT(d.drink_id) AS drink_count "
            "FROM drink_type AS t "
            "LEFT JOIN drink AS d "
            "  ON d.drink_type_id = t.drink_type_id "
            " AND d.deleted_at IS NULL "
            "GROUP BY t.drink_type_id, t.type_name, t.art, "
            "         t.method, t.detail, t.sort_order "
            "ORDER BY t.sort_order, t.drink_type_id"
        )
        drink_types = [
            {
                "drink_type_id": int(row["drink_type_id"]),
                "type_name": row["type_name"],
                "art": row["art"],
                "method": row["method"],
                "detail": row["detail"] or "",
                "drink_count": int(row["drink_count"]),
            }
            for row in cursor.fetchall()
        ]

        recipes = []

        if drink_id is not None:
            cursor.execute(
                "SELECT drink_id, drink_name, image, price, available, "
                "glass_id, drink_type_id, garnish "
                "FROM drink WHERE drink_id = %s",
                (drink_id,),
            )
            drink = cursor.fetchone()

            if drink is None:
                raise AdminError(f"Không có món id {drink_id}.", 404)

            cursor.execute(
                "SELECT category_id FROM drink_category_mapping "
                "WHERE drink_id = %s ORDER BY category_id",
                (drink_id,),
            )
            category_ids = [int(r["category_id"]) for r in cursor.fetchall()]

            cursor.execute(
                "SELECT step_no, ingredient_id, target_gram FROM recipe "
                "WHERE drink_id = %s ORDER BY step_no, ingredient_id",
                (drink_id,),
            )

            steps: dict[int, list[dict]] = {}

            for row in cursor.fetchall():
                steps.setdefault(int(row["step_no"]), []).append({
                    "ingredient_id": int(row["ingredient_id"]),
                    "target_gram": float(row["target_gram"]),
                })

            # Steps a person performs, on the same numbering as the pours.
            # Tolerates the table not being there so an admin page still
            # opens on a database that predates the migration.
            actions: dict[int, dict] = {}

            try:
                cursor.execute(
                    "SELECT step_no, media_src, title_vi, title_en, "
                    "detail_vi, detail_en, confirm_vi, confirm_en, "
                    "cup_returns FROM recipe_action "
                    "WHERE drink_id = %s ORDER BY step_no",
                    (drink_id,),
                )
            except Exception:      # noqa: BLE001 - an old schema is not an error
                pass
            else:
                for row in cursor.fetchall():
                    actions[int(row["step_no"])] = {
                        "media_src": row["media_src"],
                        "title_vi": row["title_vi"] or "",
                        "title_en": row["title_en"] or "",
                        "detail_vi": row["detail_vi"] or "",
                        "detail_en": row["detail_en"] or "",
                        "confirm_vi": row["confirm_vi"] or "",
                        "confirm_en": row["confirm_en"] or "",
                        "cup_returns": bool(row["cup_returns"]),
                    }

            recipes.append({
                "drink": {
                    "drink_id": int(drink["drink_id"]),
                    "name": drink["drink_name"],
                    "image": drink["image"],
                    "price": float(drink["price"]),
                    "available": bool(drink["available"]),
                    # None when nobody has chosen one. The bartender screen
                    # reads that as "skip the glass step", so it is a
                    # working value, not a missing one.
                    "glass_id": (
                        int(drink["glass_id"])
                        if drink["glass_id"] is not None else None
                    ),
                    # Same "None is a working value" rule as glass_id: the
                    # drink pours either way, the prep card just carries
                    # one fact fewer.
                    "drink_type_id": (
                        int(drink["drink_type_id"])
                        if drink["drink_type_id"] is not None else None
                    ),
                    "garnish": drink["garnish"] or "",
                    "category_ids": category_ids,
                },
                # One list, both kinds, in run order. A step carries
                # EITHER ingredients or an action, never both -- the
                # editor enforces that and save_recipe() relies on it.
                "steps": [
                    {
                        "step_no": number,
                        "ingredients": steps.get(number, []),
                        "action": actions.get(number),
                    }
                    for number in sorted(
                        set(steps) | set(actions)
                    )
                ],
            })

        return {
            "recipes": recipes,
            "ingredients": ingredients,
            "glasses": glasses,
            "drink_types": drink_types,
        }
    finally:
        close_database_resources(cursor, connection)


# --------------------------------------------------------------------------
# reporting
#
# WHERE SALES COME FROM
#     There is no orders table. There does not need to be one: order_ticket
#     already holds a row per drink ordered -- which drink, what it cost,
#     when the label was printed, when the machine finished it, and how it
#     ended. A ticket that reached 'used' is a drink that was made and
#     handed over, which is what "sold" means here.
#
# WHICH DATE A SALE FALLS ON
#     completed_at, the moment the drink was finished. created_at is when
#     the label came out of the printer, and those differ across midnight
#     often enough to matter for a day's takings.
#
# WHY THE PRICE IS NOT JOINED FROM drink
#     Because it would make yesterday's takings change when somebody edits
#     a price today. order_ticket.price is what the drink cost when it was
#     sold. Rows from before that column existed have NULL, and those fall
#     back to the current price -- counted and reported separately, so a
#     number that is partly an estimate never looks like one that is not.
# --------------------------------------------------------------------------
SOLD_STATUS = "used"
FAILED_STATUS = "noqr_err"

# One page of the order list. Paged on the SERVER: a shop that has been
# open a year has tens of thousands of these rows, and a page that fetches
# them all to show ten of them stops working long before anyone notices
# why. LIMIT/OFFSET keeps the cost of page 1 the same on day 400 as day 1.
ORDERS_PAGE_SIZE = 10


def parse_date(value: str, field: str) -> date:
    """A yyyy-mm-dd from the page's date picker."""
    try:
        return date.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        raise AdminError(f"Ngày {field} không hợp lệ: {value!r}.") from None


def sales_window(from_text: str, to_text: str, category: str | None):
    """Work out the WHERE clause every sales query shares.

    Pulled out so the summary and the order list cannot drift apart on
    what counts as being inside the range -- they are two views of one
    set of rows, and a report whose total disagrees with the list under
    it is worse than either on its own.

    Returns (start, end, category_id, clause, params).
    """
    start = parse_date(from_text, "bắt đầu") if from_text else None
    end = parse_date(to_text, "kết thúc") if to_text else None

    if start is None or end is None:
        today = date.today()
        start = start or today.replace(day=1)
        end = end or today

    if start > end:
        # Swapped rather than refused: two date boxes get filled in either
        # order, and the intent is never ambiguous.
        start, end = end, start

    category_id = None

    if category and str(category).strip() not in ("", "all"):
        text = str(category).strip()
        try:
            category_id = int(text[1:] if text.startswith("c") else text)
        except ValueError:
            raise AdminError(f"Danh mục không hợp lệ: {category!r}.") from None

    # BETWEEN on a DATETIME with a plain date as the upper bound would stop
    # at midnight and silently drop the whole last day. < next-day instead.
    where = ["t.status = %s", "t.completed_at >= %s", "t.completed_at < %s"]
    params: list = [SOLD_STATUS, start.isoformat(),
                    (end + timedelta(days=1)).isoformat()]

    if category_id is not None:
        where.append(
            "EXISTS (SELECT 1 FROM drink_category_mapping m "
            "WHERE m.drink_id = t.drink_id AND m.category_id = %s)"
        )
        params.append(category_id)

    return start, end, category_id, " AND ".join(where), params


def orders_payload(from_text: str, to_text: str, category: str | None,
                   page_text: str) -> dict:
    """One page of individual sales, newest first.

    Each row is one drink: which one, when it was finished, and what was
    actually charged for it. The summary above says how many; this says
    which, and that is the view somebody checks a till against.
    """
    start, end, category_id, clause, params = sales_window(
        from_text, to_text, category)

    try:
        page = max(1, int(str(page_text).strip() or 1))
    except ValueError:
        raise AdminError(f"Trang không hợp lệ: {page_text!r}.") from None

    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            f"SELECT COUNT(*) AS total FROM order_ticket t WHERE {clause}",
            params,
        )
        total = int((cursor.fetchone() or {}).get("total") or 0)
        pages = max(1, -(-total // ORDERS_PAGE_SIZE))   # ceiling division

        # Asking for page 9 of 3 gets page 3, not an empty screen. The
        # page number can be stale simply because the range changed under
        # somebody who was on page 9 a moment ago.
        page = min(page, pages)

        cursor.execute(
            "SELECT t.serial, t.drink_id, t.completed_at, "
            "       COALESCE(t.drink_name, d.drink_name, "
            "                CONCAT('#', t.drink_id)) AS name, "
            "       d.image, "
            "       COALESCE(t.price, d.price, 0) AS price, "
            "       t.price IS NULL AS estimated "
            "FROM order_ticket t "
            "LEFT JOIN drink d ON d.drink_id = t.drink_id "
            f"WHERE {clause} "
            # serial breaks ties: several drinks can finish in the same
            # second, and without it their order between pages is
            # whatever the engine feels like -- which shows one row twice
            # and hides another.
            "ORDER BY t.completed_at DESC, t.serial DESC "
            "LIMIT %s OFFSET %s",
            [*params, ORDERS_PAGE_SIZE, (page - 1) * ORDERS_PAGE_SIZE],
        )
        rows = cursor.fetchall()
    finally:
        close_database_resources(cursor, connection)

    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "category": f"c{category_id}" if category_id is not None else "all",
        "page": page,
        "pages": pages,
        "pageSize": ORDERS_PAGE_SIZE,
        "total": total,
        "orders": [
            {
                "serial": int(row["serial"]),
                "drinkId": int(row["drink_id"]),
                "name": row["name"],
                # The same URL the POS uses, and None when the file is not
                # on disk -- so the page falls back to a glyph instead of
                # showing a broken image icon.
                "image": image_url(row["image"]),
                "emoji": emoji_for(str(row["name"])),
                "price": round(float(row["price"] or 0), 2),
                "estimated": bool(row["estimated"]),
                "completedAt": row["completed_at"].isoformat(
                    sep=" ", timespec="seconds",
                ) if row["completed_at"] else None,
            }
            for row in rows
        ],
    }


def report_payload(from_text: str, to_text: str,
                   category: str | None) -> dict:
    """Sales between two dates, totalled and broken down by drink."""
    start, end, category_id, clause, params = sales_window(
        from_text, to_text, category)
    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            # The ticket's own copy of the name comes first: it is what
            # the drink was called when it sold, and it is all that is
            # left once the drink has been deleted from the menu.
            #
            # MAX() around it because this GROUPs BY drink_id, and MySQL's
            # only_full_group_by (on by default) refuses a bare column
            # that is not in the GROUP BY. Every row in a group shares the
            # drink, so MAX simply picks that shared value -- except where
            # a drink was renamed mid-range, and then the newest name wins,
            # which is the one a person will recognise.
            "SELECT t.drink_id, "
            "       COALESCE(MAX(t.drink_name), MAX(d.drink_name), "
            "                CONCAT('#', t.drink_id)) AS name, "
            "       COUNT(*) AS sold, "
            "       SUM(COALESCE(t.price, d.price, 0)) AS revenue, "
            "       SUM(t.price IS NULL) AS estimated, "
            "       MAX(COALESCE(d.price, 0)) AS current_price "
            "FROM order_ticket t "
            "LEFT JOIN drink d ON d.drink_id = t.drink_id "
            f"WHERE {clause} "
            "GROUP BY t.drink_id "
            "ORDER BY sold DESC, name",
            params,
        )
        rows = cursor.fetchall()

        # Orders that did not become a drink. Same window and the same
        # category filter, so "sold 40, failed 3" is 43 attempts at the
        # same set of drinks rather than two unrelated numbers.
        # Same clause, same window, only the status differs -- which is a
        # parameter, so it is simply swapped in position 0.
        failed_params = [FAILED_STATUS, *params[1:]]

        # The same clause, with FAILED_STATUS bound where SOLD_STATUS was:
        # the status is a parameter, not baked into the SQL.
        cursor.execute(
            "SELECT COUNT(*) AS failed FROM order_ticket t "
            f"WHERE {clause}",
            failed_params,
        )
        failed = int((cursor.fetchone() or {}).get("failed") or 0)

        # Category names, so a filtered report can say what it is filtered
        # to without the page having to look it up.
        cursor.execute(
            "SELECT category_id, category_name FROM category "
            "ORDER BY category_id"
        )
        categories = [
            {"id": f"c{int(r['category_id'])}", "name": r["category_name"]}
            for r in cursor.fetchall()
        ]
    finally:
        close_database_resources(cursor, connection)

    drinks = [
        {
            "drinkId": int(row["drink_id"]),
            "name": row["name"],
            "emoji": emoji_for(str(row["name"])),
            "sold": int(row["sold"]),
            "revenue": round(float(row["revenue"] or 0), 2),
            "estimated": int(row["estimated"] or 0),
            "currentPrice": round(float(row["current_price"] or 0), 2),
            "averagePrice": round(
                float(row["revenue"] or 0) / int(row["sold"]), 2,
            ) if int(row["sold"]) else 0.0,
        }
        for row in rows
    ]

    sold = sum(item["sold"] for item in drinks)
    revenue = round(sum(item["revenue"] for item in drinks), 2)
    estimated = sum(item["estimated"] for item in drinks)

    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "category": f"c{category_id}" if category_id is not None else "all",
        "categories": categories,
        "totals": {
            "sold": sold,
            "revenue": revenue,
            "failed": failed,
            "drinks": len(drinks),
            "average": round(revenue / sold, 2) if sold else 0.0,
            # How many of those sales had no stored price and were valued
            # at today's. Shown on the page, because it is the difference
            # between a record and an estimate.
            "estimated": estimated,
        },
        "drinks": drinks,
    }


# --------------------------------------------------------------------------
# writing
# --------------------------------------------------------------------------
def publish_to_pos() -> str | None:
    """Rewrite store_gui/menu-data.js from the database.

    WHY EVERY WRITE ENDS HERE
        The customer screen has no server and cannot query MySQL. It reads
        menu-data.js, a snapshot, and that snapshot is the menu as far as
        any customer is concerned. Changing the database without rewriting
        it means the admin screen and the shop floor disagree -- a drink
        switched off here stays on sale out there, which is the one
        failure this console must not have.

        sync_menu.py can do this on a timer, but a timer is a guess about
        when somebody edits the menu. The moment the edit happens is known
        exactly: it is right here.

    Returns a sentence if it could not be written, None if it worked.
    The caller reports it rather than failing the request -- the database
    change succeeded and undoing it would be worse than saying the shop
    screen is a few seconds behind.
    """
    try:
        publish_menu(MENU_DATA_FILE)
        return None
    except Exception as error:      # noqa: BLE001 - reported, never raised
        return (f"Đã lưu vào database nhưng chưa cập nhật được màn hình bán "
                f"({MENU_DATA_FILE.name}): {error}")



def set_available(drink_id: int, available: bool) -> None:
    """Take a drink off the menu, or put it back."""
    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE drink SET available = %s WHERE drink_id = %s",
            (1 if available else 0, drink_id),
        )

        if cursor.rowcount == 0:
            raise AdminError(f"Không có món id {drink_id}.", 404)

        connection.commit()
    finally:
        close_database_resources(cursor, connection)


def set_featured(drink_id: int, featured: bool) -> dict:
    """Put a drink in the featured strip, or take it out.

    THE CAP IS ENFORCED HERE, NOT ONLY IN THE BROWSER
        The admin table greys out the remaining stars once the strip is
        full, but that is one tab's opinion. Two tabs open, or a page
        left sitting while somebody else ticked cards, and the check has
        already been made against a stale count. This one is made
        against the database inside the same transaction as the write.

    Returns the new count so the page can update its own limit line
    without a second round trip.
    """
    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor()

        # Existence BEFORE the cap. Both refusals are true of a missing
        # drink when the strip happens to be full, and "đã đủ 6 món" would
        # send the operator off to untick something over an id that was
        # never there.
        #
        # A binned drink counts as missing: it is off the menu, so it
        # cannot be promoted on it.
        cursor.execute(
            "SELECT COUNT(*) FROM drink "
            "WHERE drink_id = %s AND deleted_at IS NULL",
            (drink_id,),
        )

        if int(cursor.fetchone()[0]) == 0:
            raise AdminError(f"Không có món id {drink_id}.", 404)

        if featured:
            # Excluding this drink: re-ticking one that is already in the
            # strip must not be refused for filling it.
            cursor.execute(
                "SELECT COUNT(*) FROM drink "
                "WHERE featured = 1 AND deleted_at IS NULL "
                "AND drink_id <> %s",
                (drink_id,),
            )

            if int(cursor.fetchone()[0]) >= FEATURED_MAX:
                raise AdminError(
                    f"Đã đủ {FEATURED_MAX} món nổi bật. "
                    "Bỏ chọn một món khác trước đã.",
                )

        cursor.execute(
            "UPDATE drink SET featured = %s WHERE drink_id = %s "
            "AND deleted_at IS NULL",
            (1 if featured else 0, drink_id),
        )
        connection.commit()

        cursor.execute(
            "SELECT COUNT(*) FROM drink "
            "WHERE featured = 1 AND deleted_at IS NULL"
        )
        return {"featured_count": int(cursor.fetchone()[0])}
    finally:
        close_database_resources(cursor, connection)


def read_setting_rows() -> list[dict]:
    """store_setting as rows, or nothing on a database without it.

    Tolerant for the same reason store_gui/sync_menu.py is: an admin
    console that will not open at all because one migration has not been
    run is worse than one whose featured panel shows its defaults.
    """
    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT setting_key, setting_value FROM store_setting")
        return cursor.fetchall()
    except Exception as error:          # noqa: BLE001 - reported as defaults
        if "doesn't exist" not in str(error).lower():
            raise
        return []
    finally:
        close_database_resources(cursor, connection)


def write_settings(settings: dict[str, str]) -> None:
    """Upsert a handful of store_setting rows in one transaction.

    Shared by the three settings endpoints so they cannot drift on how a
    missing table is explained -- which is the one failure an operator
    will actually hit, on a database that has not taken the migrations.
    """
    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor()
        cursor.executemany(
            "INSERT INTO store_setting (setting_key, setting_value) "
            "VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)",
            list(settings.items()),
        )
        connection.commit()
    except Exception as error:          # noqa: BLE001 - named, not swallowed
        if "doesn't exist" in str(error).lower():
            raise AdminError(
                "Database chưa có bảng store_setting. Chạy: "
                "mysql -u root -p beveragepos "
                "< database/migrate_featured.sql",
            ) from None
        raise
    finally:
        close_database_resources(cursor, connection)


def clean_title(body: dict, fallback: str) -> str:
    """A strip heading: trimmed, length-checked, never blank.

    Blank falls back rather than being stored -- an empty heading over a
    row of cards reads as a rendering fault, not as a choice.
    """
    title = str(body.get("title") or "").strip()

    if len(title) > 60:
        # The heading sits on one line above the strip on a kiosk. Longer
        # than this and it wraps into the cards.
        raise AdminError("Tiêu đề dài quá 60 ký tự.")

    return title or fallback


def whole_number(body: dict, field: str, label: str,
                 bounds: tuple[int, int]) -> int:
    """One bounded integer from the form, refused with a sentence.

    Refused here and not clamped: this is a person typing into a box, and
    silently storing 30 when they asked for 3000 teaches them the box does
    not work. sync_menu.py clamps instead, because by the time it reads
    the value nobody is there to be told.
    """
    low, high = bounds
    raw = str(body.get(field, "")).strip()

    try:
        value = int(raw)
    except ValueError:
        raise AdminError(f"{label} phải là số nguyên: {raw!r}.") from None

    if not low <= value <= high:
        raise AdminError(f"{label} phải trong khoảng {low}–{high}.")

    return value


def store_config() -> dict:
    """The store screen's settings, read the way the screen reads them.

    Deliberately goes through sync_menu.py's own readers rather than
    re-parsing the rows here: the admin console showing a window of 30
    while the kiosk had clamped it to 365 would be a disagreement nobody
    could see from either screen. One reader, two callers.
    """
    rows = read_setting_rows()
    return {
        "featured": featured_config(rows),
        "bestseller": bestseller_config(rows),
        "layout": layout_order(rows),
    }


def clean_style(body: dict, allowed: tuple) -> str:
    """Which arrangement a strip is drawn in.

    `allowed` is per module, because they are not interchangeable: the
    chart's whole design is its rank numeral, and the featured strip is
    drinks an operator ticked in no order at all. Numbering those would
    invent a ranking the shop never made, so that combination is refused
    here rather than left to look like a bug on the kiosk.

    Refused rather than defaulted: silently storing 'carousel' when
    somebody asked for something else hides the disagreement.
    """
    style = str(body.get("style") or "").strip().lower()

    if style not in allowed:
        raise AdminError(
            f"Kiểu hiển thị không hợp lệ cho module này: "
            f"{body.get('style')!r}. Chỉ nhận {', '.join(allowed)}.",
        )

    return style


def save_featured_config(body: dict) -> dict:
    """Write the featured strip's settings."""
    write_settings({
        "featured_enabled": "1" if body.get("enabled") else "0",
        "featured_title": clean_title(body, FEATURED_DEFAULTS["title"]),
        "featured_style": clean_style(body, FEATURED_STYLES),
        "featured_columns": str(whole_number(
            body, "columns", "Số cột", STRIP_COLUMN_RANGE)),
    })
    return {"config": store_config()["featured"]}


def save_bestseller_config(body: dict) -> dict:
    """Write the bán-chạy strip's settings.

    The window and the count are what make this strip a different thing
    from the featured one: nobody picks its drinks, so the only controls
    are how far back to look and how many to keep.
    """
    write_settings({
        "bestseller_enabled": "1" if body.get("enabled") else "0",
        "bestseller_title": clean_title(body, BESTSELLER_DEFAULTS["title"]),
        "bestseller_window_days": str(whole_number(
            body, "windowDays", "Số ngày", BESTSELLER_WINDOW_RANGE)),
        "bestseller_count": str(whole_number(
            body, "count", "Số món", BESTSELLER_COUNT_RANGE)),
        "bestseller_style": clean_style(body, BESTSELLER_STYLES),
        "bestseller_columns": str(whole_number(
            body, "columns", "Số cột", STRIP_COLUMN_RANGE)),
    })
    return {"config": store_config()["bestseller"]}


def save_layout_order(body: dict) -> dict:
    """Write the order the store screen stacks its blocks in.

    VALIDATED WHOLE, NOT PER ITEM
        A layout is only correct as a set: every block named once, none
        invented, and the menu present. Checking the list as a whole is
        what stops a reorder that drops 'grid' -- a store screen with no
        drinks on it -- from being stored because each individual name
        happened to be spelt right.
    """
    wanted = body.get("order")

    if not isinstance(wanted, list):
        raise AdminError("Thiếu thứ tự khối.")

    order = [str(name).strip() for name in wanted if str(name).strip()]
    unknown = [name for name in order if name not in LAYOUT_BLOCKS]

    if unknown:
        raise AdminError(f"Khối không hợp lệ: {', '.join(unknown)}.")

    if len(set(order)) != len(order):
        raise AdminError("Có khối bị lặp lại trong thứ tự.")

    if LAYOUT_REQUIRED not in order:
        raise AdminError(
            "Thứ tự phải có khối menu — màn hình khách không thể "
            "không hiện món nào.",
        )

    if set(order) != set(LAYOUT_BLOCKS):
        missing = [b for b in LAYOUT_BLOCKS if b not in order]
        raise AdminError(f"Thiếu khối: {', '.join(missing)}.")

    write_settings({"layout_order": ",".join(order)})
    return {"layout": store_config()["layout"]}


def set_price(drink_id: int, price: float) -> None:
    """Change one price."""
    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE drink SET price = %s WHERE drink_id = %s",
            (round(price, 2), drink_id),
        )

        if cursor.rowcount == 0:
            raise AdminError(f"Không có món id {drink_id}.", 404)

        connection.commit()
    finally:
        close_database_resources(cursor, connection)


def delete_drink(drink_id: int) -> dict:
    """Move a drink to the recycle bin.

    WHAT HAPPENS
        deleted_at is stamped and available is switched off. The row, its
        recipe and its categories all stay exactly as they are, so a
        restore is instant and complete. Every query that lists a menu --
        the customer screen, the admin table, the machine's recipe
        lookup -- filters on deleted_at IS NULL, so the drink disappears
        from all of them at once.

    WHAT DOES NOT CHANGE
        The sales record. order_ticket keeps every ticket ever issued for
        this drink, including the name and price it sold at, so the report
        still adds up whether the drink is on the menu, in the bin, or
        purged for good.

    WHAT IT REFUSES
        A drink being poured right now. Taking it off the menu mid-order
        would leave the machine finishing a drink the screens can no
        longer describe.
    """
    connection = cursor = None

    try:
        connection = connect_database()
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT drink_name FROM drink WHERE drink_id = %s", (drink_id,))
        row = cursor.fetchone()

        if row is None:
            raise AdminError(f"Không có món id {drink_id}.", 404)

        name = row["drink_name"]

        cursor.execute(
            "SELECT COUNT(*) AS n FROM order_ticket "
            "WHERE drink_id = %s AND status = 'in_progress'",
            (drink_id,))

        if int(cursor.fetchone()["n"]):
            raise AdminError(
                f"\"{name}\" đang được pha. Đợi máy xong rồi xóa.", 409)

        # Labels already printed and not yet scanned. They stop working
        # the moment the drink goes, so the number is reported back and
        # the page says so before anything is removed.
        cursor.execute(
            "SELECT COUNT(*) AS n FROM order_ticket "
            "WHERE drink_id = %s AND status = 'unused'",
            (drink_id,))
        stranded = int(cursor.fetchone()["n"])

        cursor.execute(
            "SELECT COUNT(*) AS n FROM recipe WHERE drink_id = %s",
            (drink_id,))
        steps = int(cursor.fetchone()["n"])

        # Moved to the bin, not destroyed. The row stays and every query
        # that lists a menu skips it; restore() simply clears the stamp.
        # The recipe rows are left exactly where they are, which is what
        # makes a restore a restore rather than a retype.
        cursor.execute(
            "UPDATE drink SET deleted_at = NOW(), available = 0 "
            "WHERE drink_id = %s AND deleted_at IS NULL",
            (drink_id,))

        if cursor.rowcount == 0:
            raise AdminError(f"\"{name}\" đã ở trong thùng rác.", 409)

        connection.commit()

        return {"drink_id": drink_id, "name": name,
                "recipe_rows": steps, "stranded_tickets": stranded}
    except AdminError:
        if connection is not None:
            connection.rollback()
        raise
    except Exception as error:          # noqa: BLE001 - reported to the page
        if connection is not None:
            connection.rollback()
        raise AdminError(f"Không xóa được: {error}", 500) from error
    finally:
        close_database_resources(cursor, connection)


def sniff_image(data: bytes) -> str:
    """The file's real type as an extension, or "" if it is not an image.

    WEBP is checked separately: its signature is a RIFF container header
    with the format four bytes later, so a plain prefix match will not do.
    """
    for signature, extension in IMAGE_SIGNATURES:
        if data.startswith(signature):
            return extension

    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"

    return ""


def safe_image_name(raw: str, extension: str, fallback: str = "image") -> str:
    """Turn whatever the browser sent into a filename we are willing to use.

    Everything except letters, digits, space, dash and underscore is
    dropped, so no directory separator and no ".." can survive to reach
    a path outside recipe/image/. The extension comes from sniff_image(),
    never from the name.
    """
    stem = Path(str(raw or "")).stem
    stem = re.sub(r"[^\w \-]", "", stem, flags=re.UNICODE).strip()
    stem = re.sub(r"\s+", " ", stem)[:60]

    return f"{stem or fallback}{extension}"


def list_media() -> dict:
    """Every instruction clip already uploaded, newest first.

    Its own library, separate from list_images(). A clip and a menu photo
    are never interchangeable -- one is a moving demonstration inside a
    step, the other a still tile on the sales screen -- and a single
    gallery holding both would invite picking a drink photo as a
    demonstration because it happened to be in the list.
    """
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    found = []

    for path in MEDIA_DIR.iterdir():
        if not path.is_file():
            continue

        try:
            head = path.open("rb").read(16)
        except OSError:
            continue

        # By content, like everywhere else. A file that will not play is
        # not offered, whatever it is called.
        kind = sniff_media(head)

        if not kind:
            continue

        stat = path.stat()
        found.append({
            "name": path.name,
            # What goes in the step's media.src: the bare filename, since
            # process_runner.py refuses anything carrying a separator.
            "src": path.name,
            "url": "../" + quote(f"recipe/media/{path.name}", safe="/"),
            "kind": "video" if kind in (".mp4", ".webm") else "image",
            "bytes": stat.st_size,
            "modified": stat.st_mtime,
        })

    found.sort(key=lambda item: item["modified"], reverse=True)
    return {"media": found}


def list_images() -> dict:
    """Every photo already uploaded, newest first."""
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    found = []

    for path in IMAGE_DIR.iterdir():
        if not path.is_file():
            continue

        try:
            head = path.open("rb").read(16)
        except OSError:
            continue

        if not sniff_image(head):
            continue

        stat = path.stat()
        found.append({
            "name": path.name,
            # What goes in drink.image: relative to the project root, the
            # same shape every existing row already uses.
            "path": f"recipe/image/{path.name}",
            # What the admin page loads to show a thumbnail. It sits one
            # directory down, so it needs the ../.
            "url": "../" + quote(f"recipe/image/{path.name}", safe="/"),
            "bytes": stat.st_size,
            "modified": stat.st_mtime,
        })

    found.sort(key=lambda item: item["modified"], reverse=True)
    return {"images": found}


def save_image(filename: str, data: bytes) -> dict:
    """Store one uploaded photo and return where it went."""
    if not data:
        raise AdminError("Tệp rỗng.")

    if len(data) > IMAGE_MAX_BYTES:
        raise AdminError(
            f"Ảnh quá lớn ({len(data) / 1_048_576:.1f} MB). "
            f"Tối đa {IMAGE_MAX_BYTES // 1_048_576} MB.")

    extension = sniff_image(data)

    if not extension:
        raise AdminError("Tệp này không phải ảnh (chỉ nhận JPG, PNG, GIF, WEBP).")

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    name = safe_image_name(filename, extension)
    target = IMAGE_DIR / name

    # Never silently replace another drink's photo. A second upload of the
    # same name becomes "Peach Tea 2.webp", so the old tile keeps working.
    if target.exists():
        stem, suffix = target.stem, target.suffix
        number = 2

        while (IMAGE_DIR / f"{stem} {number}{suffix}").exists():
            number += 1

        target = IMAGE_DIR / f"{stem} {number}{suffix}"

    temporary = target.with_name(f".{target.name}.part")
    temporary.write_bytes(data)
    temporary.replace(target)

    return {
        "name": target.name,
        "path": f"recipe/image/{target.name}",
        "url": "../" + quote(f"recipe/image/{target.name}", safe="/"),
        "bytes": len(data),
    }


def binned_drinks() -> dict:
    """What is in the recycle bin, newest first."""
    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT d.drink_id, d.drink_name, d.image, d.price, d.deleted_at, "
            "       (SELECT COUNT(*) FROM recipe r "
            "         WHERE r.drink_id = d.drink_id) AS recipe_rows, "
            "       (SELECT COUNT(*) FROM order_ticket t "
            "         WHERE t.drink_id = d.drink_id "
            "           AND t.status = 'used') AS sold "
            "FROM drink d "
            "WHERE d.deleted_at IS NOT NULL "
            "ORDER BY d.deleted_at DESC"
        )
        rows = cursor.fetchall()
    finally:
        close_database_resources(cursor, connection)

    return {
        "drinks": [
            {
                "id": int(r["drink_id"]),
                "name": r["drink_name"],
                "emoji": emoji_for(str(r["drink_name"])),
                "image": image_url(r["image"]),
                "price": round(float(r["price"] or 0), 2),
                "deletedAt": r["deleted_at"].isoformat(
                    sep=" ", timespec="seconds") if r["deleted_at"] else None,
                "recipeRows": int(r["recipe_rows"]),
                "sold": int(r["sold"]),
            }
            for r in rows
        ]
    }


def restore_drink(drink_id: int) -> dict:
    """Put a drink back on the menu.

    It comes back switched OFF -- available = 0. Whoever binned it did so
    for a reason, and a drink reappearing on the customer screen the
    instant somebody browses the bin is not what restore should mean. The
    switch in the table puts it back on sale when they are ready.
    """
    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT drink_name, deleted_at FROM drink WHERE drink_id = %s",
            (drink_id,))
        row = cursor.fetchone()

        if row is None:
            raise AdminError(f"Không có món id {drink_id}.", 404)

        if row["deleted_at"] is None:
            raise AdminError(f"\"{row['drink_name']}\" không ở trong "
                             f"thùng rác.", 409)

        cursor.execute(
            "UPDATE drink SET deleted_at = NULL WHERE drink_id = %s",
            (drink_id,))
        connection.commit()

        return {"drink_id": drink_id, "name": row["drink_name"]}
    finally:
        close_database_resources(cursor, connection)


def purge_drink(drink_id: int) -> dict:
    """Delete a binned drink for good. This one really does remove it.

    Its recipe rows and category links go with it by ON DELETE CASCADE.
    The sales tickets survive, as they always do -- they carry their own
    copy of the name and price.

    Only reachable for a drink already in the bin, so nothing is ever one
    click from destruction.
    """
    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT drink_name, deleted_at FROM drink WHERE drink_id = %s",
            (drink_id,))
        row = cursor.fetchone()

        if row is None:
            raise AdminError(f"Không có món id {drink_id}.", 404)

        if row["deleted_at"] is None:
            raise AdminError(
                f"\"{row['drink_name']}\" vẫn đang trên menu. Xóa vào "
                f"thùng rác trước.", 409)

        cursor.execute("DELETE FROM drink WHERE drink_id = %s", (drink_id,))
        connection.commit()

        return {"drink_id": drink_id, "name": row["drink_name"]}
    finally:
        close_database_resources(cursor, connection)


def validated_action(action: dict, step_no: int, drink_id: int) -> tuple:
    """Turn one editor action step into a recipe_action row, or refuse it.

    media_src is checked here as well as in process_runner.py, and for the
    same reason it is checked there: it becomes part of a URL the screens
    fetch, so a name carrying a separator would read a file outside
    recipe/media/. Refusing at the point of writing means a bad name never
    reaches the database in the first place.
    """
    media = str(action.get("media_src") or "").strip()

    if not media:
        raise AdminError(
            f"Bước {step_no}: chưa chọn phim hướng dẫn."
        )

    if "/" in media or "\\" in media or media.startswith("."):
        raise AdminError(
            f"Bước {step_no}: tên phim không hợp lệ."
        )

    title = str(action.get("title_vi") or "").strip()

    if not title:
        raise AdminError(
            f"Bước {step_no}: bước thao tác phải có tiêu đề."
        )

    def text(key: str, limit: int) -> str:
        return str(action.get(key) or "").strip()[:limit]

    return (
        drink_id,
        step_no,
        media[:255],
        title[:120],
        text("title_en", 120),
        text("detail_vi", 400),
        text("detail_en", 400),
        text("confirm_vi", 40),
        text("confirm_en", 40),
        1 if action.get("cup_returns", True) else 0,
    )


def save_recipe(document: dict) -> dict:
    """Write one drink and its whole recipe, in a single transaction.

    The recipe is REPLACED, not merged. That is only safe because
    editor_payload() shows every ingredient the recipe can contain, so the
    editor cannot be holding a partial view of it -- see the note there.

    All of it commits or none of it does. A drink whose row was updated but
    whose recipe write failed would be a menu item the machine cannot pour,
    which is worse than the edit simply not happening.
    """
    drink = document.get("drink") or {}
    steps = document.get("steps") or []

    name = str(drink.get("name") or "").strip()

    if not name:
        raise AdminError("Tên món không được để trống.")

    price = float(drink.get("price") or 0)

    if not 0 <= price <= PRICE_MAX:
        raise AdminError(f"Giá phải nằm trong khoảng 0 - {PRICE_MAX}.")

    category_ids = [int(value) for value in (drink.get("category_ids") or [])]

    if not category_ids:
        raise AdminError("Món phải thuộc ít nhất một danh mục.")

    if not steps:
        raise AdminError("Công thức phải có ít nhất một bước.")

    drink_id = drink.get("drink_id")
    drink_id = int(drink_id) if drink_id is not None else None
    image = str(drink.get("image") or "").strip() or None
    available = bool(drink.get("available"))

    # Absent or empty means "no glass chosen", which is a legitimate state:
    # the drink still pours, the bartender screen just skips its glass step.
    # A bad id is rejected by the foreign key rather than guessed at here.
    raw_glass = drink.get("glass_id")
    glass_id = None

    if raw_glass not in (None, "", "null"):
        try:
            glass_id = int(raw_glass)
        except (TypeError, ValueError):
            raise AdminError("glass_id không hợp lệ.", 400)

    # The build method, read exactly like the glass: absent means nobody
    # has chosen one, and a bad id is the foreign key's business.
    raw_type = drink.get("drink_type_id")
    drink_type_id = None

    if raw_type not in (None, "", "null"):
        try:
            drink_type_id = int(raw_type)
        except (TypeError, ValueError):
            raise AdminError("drink_type_id không hợp lệ.", 400)

    # Free text, and the column is VARCHAR(120): trimmed here so a value
    # pasted with a trailing newline is not rejected by the database.
    garnish = str(drink.get("garnish") or "").strip()[:120] or None

    # The build method's description. It lives on drink_type, not on this
    # drink -- so it is written only when a type is actually selected, and
    # only when the editor sends the key at all. An absent key means "the
    # form did not offer it", which must not be read as "clear it".
    raw_detail = drink.get("drink_type_detail")
    type_detail = (
        None if raw_detail is None
        else str(raw_detail).strip()[:200] or None
    )

    connection = cursor = None

    try:
        connection = connect_database()
        connection.start_transaction()
        cursor = connection.cursor()

        if drink_id is None:
            cursor.execute(
                "INSERT INTO drink "
                "(drink_name, image, price, available, glass_id, "
                "drink_type_id, garnish) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (name, image, round(price, 2),
                 1 if available else 0, glass_id, drink_type_id, garnish),
            )
            drink_id = int(cursor.lastrowid)
        else:
            cursor.execute(
                "UPDATE drink SET drink_name = %s, image = %s, price = %s, "
                "available = %s, glass_id = %s, drink_type_id = %s, "
                "garnish = %s WHERE drink_id = %s",
                (name, image, round(price, 2),
                 1 if available else 0, glass_id, drink_type_id, garnish,
                 drink_id),
            )

            if cursor.rowcount == 0:
                cursor.execute(
                    "SELECT drink_id FROM drink WHERE drink_id = %s",
                    (drink_id,),
                )

                if cursor.fetchone() is None:
                    raise AdminError(f"Không có món id {drink_id}.", 404)

        # Shared reference data, written from a per-drink form. It is
        # guarded twice: only when a type is selected, and only when the
        # text actually differs from what is stored -- so saving a drink
        # without touching the field writes nothing at all.
        if drink_type_id is not None and raw_detail is not None:
            cursor.execute(
                "UPDATE drink_type SET detail = %s "
                "WHERE drink_type_id = %s "
                "  AND NOT (detail <=> %s)",
                (type_detail, drink_type_id, type_detail),
            )

        cursor.execute(
            "DELETE FROM drink_category_mapping WHERE drink_id = %s",
            (drink_id,),
        )
        cursor.executemany(
            "INSERT INTO drink_category_mapping (drink_id, category_id) "
            "VALUES (%s, %s)",
            [(drink_id, category_id)
             for category_id in dict.fromkeys(category_ids)],
        )

        cursor.execute("DELETE FROM recipe WHERE drink_id = %s", (drink_id,))
        cursor.execute(
            "DELETE FROM recipe_action WHERE drink_id = %s",
            (drink_id,),
        )

        rows = []
        action_rows = []

        for position, step in enumerate(steps, start=1):
            step_no = int(step.get("step_no") or position)
            action = step.get("action")

            # An action step pours nothing, so it is stored in its own
            # table and contributes no recipe row. `continue` rather than
            # falling through: an action carrying ingredients would write
            # a step that is two things at once, and export_data.py emits
            # them as separate steps in that case.
            if action:
                action_rows.append(
                    validated_action(action, step_no, drink_id)
                )
                continue

            for ingredient in step.get("ingredients") or []:
                target = float(ingredient.get("target_gram") or 0)

                if target <= 0:
                    raise AdminError(
                        f"Bước {step_no}: số gram phải lớn hơn 0."
                    )

                rows.append((
                    drink_id,
                    int(ingredient["ingredient_id"]),
                    step_no,
                    round(target, 2),
                ))

        if not rows:
            raise AdminError("Công thức phải có ít nhất một nguyên liệu.")

        cursor.executemany(
            "INSERT INTO recipe (drink_id, ingredient_id, step_no, "
            "target_gram) VALUES (%s, %s, %s, %s)",
            rows,
        )

        if action_rows:
            cursor.executemany(
                "INSERT INTO recipe_action (drink_id, step_no, media_src, "
                "title_vi, title_en, detail_vi, detail_en, confirm_vi, "
                "confirm_en, cup_returns) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                action_rows,
            )

        connection.commit()

        return {"drink_id": drink_id}
    except AdminError:
        if connection is not None:
            connection.rollback()
        raise
    except Exception as error:          # noqa: BLE001 - reported to the page
        if connection is not None:
            connection.rollback()

        # The two constraints an admin can actually trip, named plainly.
        text = str(error)

        if "drink_name" in text and "Duplicate" in text:
            raise AdminError(f"Đã có món tên \"{name}\".") from error

        if "fk_recipe_ingredient" in text:
            raise AdminError("Nguyên liệu không tồn tại.") from error

        raise AdminError(f"Không lưu được: {error}", 500) from error
    finally:
        close_database_resources(cursor, connection)



# --------------------------------------------------------------------------
# ingredients (the stock page)
#
# WHAT THIS SECTION DOES NOT DO
#   It never writes in_stock, and it never writes threshold_gram. Both are
#   derived, by two different mechanisms that already work:
#
#     in_stock       BEFORE INSERT/UPDATE triggers in database/database.sql
#                    set it to (amount >= threshold_gram), and an AFTER
#                    UPDATE trigger pushes the result out to every drink
#                    whose recipe names this ingredient. That is why a
#                    refill here can put drinks back on sale without this
#                    file containing the word "drink".
#
#     threshold_gram database/db_core.py recalculate_thresholds() sets it
#                    to 110% of the largest amount any recipe asks for,
#                    and inventory_service.check_inventory() runs that.
#                    Anything typed into it would be overwritten later, so
#                    the page shows it read-only and says where it is from.
#
#   Amount and max_gram are the two a person states, and they are stated
#   at different times by different people: max_gram when a bottle is
#   screwed on ("this size"), amount when one is filled ("this much is in
#   it now"). Neither can be derived -- only somebody standing at the
#   machine knows either -- which is why they are the two the pages write
#   and the other two are read-only on screen.
# --------------------------------------------------------------------------
# Set once the old capacity file has been dealt with, so the check costs
# an attribute lookup on every request after the first. The lock is real:
# this is a ThreadingHTTPServer, and two browsers opening the stock page
# together would otherwise both start the carry-over.
_capacity_adopted = False
_capacity_lock = threading.Lock()


def adopt_capacity_file() -> None:
    """Carry configuration/ingredient_capacity.json into max_gram, once.

    The figures used to live in that file (see LEGACY_MAX_GRAM_FILE). On a
    machine that has been running, they are the sizes of the bottles
    actually on the machine, measured by somebody -- so the ALTER that
    added the column must not be the moment they are lost.

    Only NULL rows are filled. A max_gram already in the column was typed
    after the move and is the newer of the two statements; the file gets
    to answer only for the containers nobody has spoken about since.
    That, plus the rename at the end, makes running this twice harmless.

    A database failure deliberately leaves the flag unset and propagates:
    the caller was about to touch the same database anyway, and a silent
    "well, we tried" here would quietly abandon the numbers.
    """
    global _capacity_adopted

    if _capacity_adopted:
        return

    with _capacity_lock:
        if _capacity_adopted:
            return

        try:
            with open(LEGACY_MAX_GRAM_FILE, encoding="utf-8") as handle:
                stored = json.load(handle)
        except (OSError, ValueError):
            # Absent is the normal case on a fresh install. Unreadable or
            # half-written is not worth guessing at either: the column
            # stays NULL, and NULL is exactly the true statement -- nobody
            # has declared how big these containers are.
            _capacity_adopted = True
            return

        carried = []

        for key, value in (stored or {}).items():
            try:
                ingredient_id = int(key)
                max_gram = float(value)
            except (TypeError, ValueError):
                continue

            # The same range the column accepts. An entry for an
            # ingredient that no longer exists simply matches no row --
            # which is the drift this move was made to end.
            if 0 < max_gram <= AMOUNT_MAX:
                carried.append((round(max_gram, 2), ingredient_id))

        if carried:
            connection = cursor = None

            try:
                connection = connect_database()
                cursor = connection.cursor()
                cursor.executemany(
                    "UPDATE ingredient SET max_gram = %s "
                    "WHERE ingredient_id = %s AND max_gram IS NULL",
                    carried,
                )
                connection.commit()
            finally:
                close_database_resources(cursor, connection)

        # Renamed rather than deleted, and only after the commit: if the
        # carry-over ever turns out to be wrong, the numbers somebody
        # measured are still on disk to read.
        try:
            LEGACY_MAX_GRAM_FILE.rename(
                LEGACY_MAX_GRAM_FILE.with_name(
                    LEGACY_MAX_GRAM_FILE.name + ".adopted"))
        except OSError:
            pass

        _capacity_adopted = True


def max_gram_or_default(raw) -> int | float:
    """One row's max_gram as a number a % bar and a refill can use.

    NULL in the column is not a size -- it is "nobody has declared one" --
    so it cannot be divided by or filled to. DEFAULT_MAX_GRAM stands in.

    Whether it stood in is a separate question, and every caller answers
    it the same way: `row["max_gram"] is not None`. Kept separate rather
    than returned as a pair, because that test is what the screen turns
    into the "?" beside a guessed percentage, and it reads better where it
    is used than as the second half of a tuple.
    """
    return DEFAULT_MAX_GRAM if raw is None else mysql_number(raw)


def pump_numbers() -> dict[int, int]:
    """Which pump each GPIO pin IS, keyed by pin, as pump_control names them.

    The ingredient table stores a pin. Nobody on the shop floor calls it a
    pin -- the pumps are numbered 1..10 down the manifold, and that
    numbering is what pump_control/pump_ml.py drives them by and what
    configuration/pump_calib.json is keyed on.

    Read from that module rather than copied into this one, because a
    second copy of a wiring table is a copy that goes stale silently the
    first time somebody moves a hose.

    machine.py holds the table and imports nothing -- no gpiozero, no lgpio
    -- so this console opens on a laptop with no GPIO on it without the
    import having to be allowed to fail. It used to come from pump_ml,
    which drags the hardware library in behind it; the try below survives
    from that arrangement and now essentially never fires. It is kept
    because a page that loses one label is better than a page that 500s.
    """
    try:
        from configuration.machine import PIN_TO_PUMP
    except Exception:       # noqa: BLE001 - a console without GPIO is fine
        return {}

    return dict(PIN_TO_PUMP)


def panel_positions() -> int:
    """How many slots the manual panel has.

    Same lazy import and same reason as pump_numbers(): panel_control
    talks to an I2C expander, and the console has to open on a machine
    that has none. PANEL_COUNT is a count of physical buttons, so the
    fallback is the number that board has always had rather than a guess.
    """
    try:
        from panel_control.panel import PANEL_COUNT
    except Exception:       # noqa: BLE001 - a console without I2C is fine
        return 16

    return int(PANEL_COUNT)


def stock_order(row: dict) -> tuple:
    """Down the machine, not down the id column.

    Pumps first in pump order, then the manual panel in panel order, then
    anything not plugged into either. Somebody holding a bottle reads this
    table against the hardware in front of them.
    """
    if row["type"] == "PUMP":
        return (0, row["pump_no"] if row["pump_no"] is not None else 900,
                row["ingredient_id"])

    # The number inside the slot, not the slot itself: gpio is text now
    # ("P01"), and sorting text against the 900 that stands for "not
    # plugged in anywhere" is a TypeError, not an ordering.
    return (1, row["gpio_number"] if row["gpio_number"] is not None else 900,
            row["ingredient_id"])


def ingredients_payload() -> dict:
    """Every ingredient, in the shape admin_gui/ingredient-store.js wants.

    used_in is counted here rather than worked out in the browser: it is
    what turns "cannot delete" into a sentence naming how many recipes
    stand in the way, and the browser has no recipe table to count.

    Ordered the way the machine is laid out -- pumps first, by pin -- so
    the PUMP # column reads down the panel rather than down the id column.
    """
    adopt_capacity_file()

    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT ingredient.ingredient_id, ingredient.ingredient_name, "
            "       ingredient.type, ingredient.data_type, "
            "       ingredient.amount, ingredient.threshold_gram, "
            "       ingredient.max_gram, "
            "       ingredient.gpio, ingredient.in_stock, "
            "       COUNT(DISTINCT recipe.drink_id) AS used_in "
            "FROM ingredient "
            "LEFT JOIN recipe "
            "  ON recipe.ingredient_id = ingredient.ingredient_id "
            "GROUP BY ingredient.ingredient_id"
        )
        rows = cursor.fetchall()
    finally:
        close_database_resources(cursor, connection)

    pumps = pump_numbers()

    ingredients = sorted(
        (
            {
                "ingredient_id": int(row["ingredient_id"]),
                "name": row["ingredient_name"],
                "type": row["type"],
                "data_type": row["data_type"],
                "amount": mysql_number(row["amount"]),
                "threshold_gram": mysql_number(row["threshold_gram"]),
                # What a full container holds: the level a refill fills
                # to, and what the % bar is a share of. NULL in the column
                # becomes the default here, and max_set says which of the
                # two the number came from, so the page can show a guessed
                # percentage as a guess rather than as a fact.
                "max_gram": max_gram_or_default(row["max_gram"]),
                "max_set": row["max_gram"] is not None,
                # The slot as stored ("G26"), so the screen can show it
                # verbatim, plus the number the pump table is keyed by.
                "gpio": row["gpio"],
                "gpio_number": gpio_number(row["gpio"]),
                # The pump the bottle is screwed onto, when the pin is one
                # pump_control drives. None for the manual panel, and None
                # for a pin nothing is wired to.
                "pump_no": (
                    pumps.get(gpio_number(row["gpio"]))
                    if row["type"] == "PUMP" and row["gpio"] is not None
                    else None
                ),
                "in_stock": bool(row["in_stock"]),
                "used_in": int(row["used_in"]),
            }
            for row in rows
        ),
        key=stock_order,
    )

    return {
        "ingredients": ingredients,
        "default_max_gram": DEFAULT_MAX_GRAM,
        # The two things a person is allowed to choose a position from.
        # Sent so the form can offer "Bơm #3" and keep the pin to itself:
        # which pin pump 3 is on is a fact about the loom, and nobody
        # standing at the machine with a bottle should have to know it.
        "pumps": [
            {"pump_no": number, "gpio": pin}
            for pin, number in sorted(pumps.items(), key=lambda item: item[1])
        ],
        "panel_count": panel_positions(),
    }


def gram_of(raw, field: str) -> float:
    """One weight from the page, validated into a number the column takes."""
    try:
        grams = float(str(raw).strip())
    except (TypeError, ValueError):
        raise AdminError(f"{field} không hợp lệ: {raw!r}.") from None

    if grams != grams or grams in (float("inf"), float("-inf")):
        raise AdminError(f"{field} không hợp lệ.")

    if not 0 <= grams <= AMOUNT_MAX:
        raise AdminError(f"{field} phải nằm trong khoảng 0 - {AMOUNT_MAX}.")

    return grams


def ingredient_id_of(body: dict) -> int:
    try:
        return int(body.get("ingredient_id"))
    except (TypeError, ValueError):
        raise AdminError("Thiếu ingredient_id.") from None


def refill_ingredient(ingredient_id: int, body: dict) -> dict:
    """Put stock back into one container.

    Three ways of saying it, because three different things happen in a
    shop: fill=true for "I put a new bottle on", add_gram for "I poured
    some in", set_gram for "the scale says this much is left". They all
    end in one UPDATE of amount, and the triggers do the rest.

    The row is read back AFTER the commit rather than assumed, because
    in_stock is decided by a trigger and this is the only way to report
    what the database actually concluded.
    """
    adopt_capacity_file()

    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor(dictionary=True)
        # max_gram comes back with the row it belongs to, so "fill this
        # bottle" and "which bottle" are one question asked once.
        cursor.execute(
            "SELECT ingredient_name, amount, max_gram FROM ingredient "
            "WHERE ingredient_id = %s",
            (ingredient_id,),
        )
        row = cursor.fetchone()

        if row is None:
            raise AdminError(f"Không có nguyên liệu id {ingredient_id}.", 404)

        max_gram = max_gram_or_default(row["max_gram"])

        if body.get("fill"):
            amount = max_gram
        elif body.get("set_gram") is not None:
            amount = gram_of(body.get("set_gram"), "Lượng tồn")
        elif body.get("add_gram") is not None:
            amount = (float(row["amount"])
                      + gram_of(body.get("add_gram"), "Lượng nạp thêm"))
        else:
            raise AdminError("Thiếu lượng cần nạp.")

        if amount > AMOUNT_MAX:
            raise AdminError(
                f"Tổng lượng sau khi nạp vượt quá {AMOUNT_MAX}g.")

        cursor.execute(
            "UPDATE ingredient SET amount = %s WHERE ingredient_id = %s",
            (round(amount, 2), ingredient_id),
        )
        connection.commit()

        cursor.execute(
            "SELECT amount, in_stock FROM ingredient WHERE ingredient_id = %s",
            (ingredient_id,),
        )
        saved = cursor.fetchone()

        return {
            "ingredient_id": ingredient_id,
            "name": row["ingredient_name"],
            "amount": mysql_number(saved["amount"]),
            "in_stock": bool(saved["in_stock"]),
            "max_gram": max_gram,
            # Said out loud for the same reason the list says it: a bottle
            # filled to the fallback was filled to a guess.
            "max_set": row["max_gram"] is not None,
        }
    except AdminError:
        if connection is not None:
            connection.rollback()
        raise
    finally:
        close_database_resources(cursor, connection)


def refill_all_ingredients(body: dict) -> dict:
    """Fill every container to its max in one write.

    The end of a delivery: bottles come off the trolley, every one of them
    goes back on the machine full, and doing that one modal at a time is
    thirteen dialogs to say one thing.

    NOT a loop over refill_ingredient(). Two reasons, and both are about
    what a half-finished restock leaves behind:

      · One transaction. If the seventh row fails, the six before it roll
        back too, so the answer to "did the restock happen" is yes or no
        rather than "partly, and you work out which".
      · One read of the max file, one publish_to_pos() by the caller.
        Thirteen separate refills would rewrite the customer's menu
        thirteen times over.

    `only` narrows it to a list of ids -- what the page sends when the
    person un-ticked some rows in the confirmation. Absent means all of
    them. Rows already at their max are still written: setting a value to
    what it already is costs nothing and keeps the reply honest about what
    the machine now holds.
    """
    wanted = body.get("only")
    chosen: set[int] | None = None

    if wanted is not None:
        if not isinstance(wanted, list):
            raise AdminError("Danh sách nguyên liệu cần nạp không hợp lệ.")

        try:
            chosen = {int(value) for value in wanted}
        except (TypeError, ValueError):
            raise AdminError(
                "Danh sách nguyên liệu cần nạp có id không hợp lệ.") from None

        if not chosen:
            raise AdminError("Chưa chọn nguyên liệu nào để nạp.")

    adopt_capacity_file()

    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT ingredient_id, ingredient_name, amount, max_gram "
            "FROM ingredient ORDER BY ingredient_id"
        )
        rows = cursor.fetchall()

        filled = []

        for row in rows:
            ingredient_id = int(row["ingredient_id"])

            if chosen is not None and ingredient_id not in chosen:
                continue

            max_gram = max_gram_or_default(row["max_gram"])

            if max_gram > AMOUNT_MAX:
                raise AdminError(
                    f"Mức tối đa của {row['ingredient_name']} vượt quá "
                    f"{AMOUNT_MAX}g.")

            filled.append({
                "ingredient_id": ingredient_id,
                "name": row["ingredient_name"],
                "before": mysql_number(row["amount"]),
                "amount": round(max_gram, 2),
                # Said out loud so the page can warn that this row was
                # filled to a guess rather than to a declared figure.
                "max_set": row["max_gram"] is not None,
            })

        if not filled:
            raise AdminError("Không có nguyên liệu nào để nạp.")

        cursor.executemany(
            "UPDATE ingredient SET amount = %s WHERE ingredient_id = %s",
            [(row["amount"], row["ingredient_id"]) for row in filled],
        )
        connection.commit()

        # Read back after the commit, exactly as refill_ingredient() does:
        # in_stock is a trigger's conclusion, not this file's.
        cursor.execute(
            "SELECT ingredient_id, in_stock FROM ingredient "
            "WHERE ingredient_id IN ({})".format(
                ",".join(["%s"] * len(filled))),
            [row["ingredient_id"] for row in filled],
        )
        in_stock = {int(r["ingredient_id"]): bool(r["in_stock"])
                    for r in cursor.fetchall()}

        for row in filled:
            row["in_stock"] = in_stock.get(row["ingredient_id"], False)

        return {
            "filled": filled,
            "count": len(filled),
            # How many were topped up to the fallback rather than to a
            # figure somebody actually declared.
            "guessed": sum(1 for row in filled if not row["max_set"]),
        }
    except AdminError:
        if connection is not None:
            connection.rollback()
        raise
    except Exception as error:          # noqa: BLE001 - reported to the page
        if connection is not None:
            connection.rollback()
        raise AdminError(f"Không nạp được: {error}", 500) from error
    finally:
        close_database_resources(cursor, connection)


def ingredient_fields(body: dict) -> dict:
    """What an ingredient IS, checked before any of it reaches the table.

    The CHECK constraints in database.sql say the same things, but a
    constraint failure arrives as one line of driver text with a
    constraint name in it. These sentences name the field.
    """
    name = str(body.get("name") or "").strip()

    if not name:
        raise AdminError("Tên nguyên liệu không được để trống.")

    if len(name) > 100:
        raise AdminError("Tên nguyên liệu tối đa 100 ký tự.")

    kind = str(body.get("type") or "").strip().upper()

    if kind not in ("PUMP", "MANUAL"):
        raise AdminError("Loại phải là PUMP hoặc MANUAL.")

    data_type = str(body.get("data_type") or "").strip().lower()

    if data_type not in ("boolean", "percentage", "weight"):
        raise AdminError("Kiểu dữ liệu phải là weight, percentage hoặc "
                         "boolean.")

    # The form sends the position as a plain number -- it offers "Bơm #3",
    # not a pin -- but the column stores a slot: "G26" for a pump pin,
    # "P01" for a panel position. The number is what gets range-checked,
    # the slot is what gets written, and which prefix it takes is decided
    # by the row's type rather than by anything the page sent.
    raw_gpio = body.get("gpio")
    gpio = None

    if raw_gpio not in (None, ""):
        number = gpio_number(raw_gpio)

        if number is None:
            raise AdminError(f"GPIO không hợp lệ: {raw_gpio!r}.")

        if not 0 <= number <= GPIO_MAX:
            raise AdminError(f"GPIO phải nằm trong khoảng 0 - {GPIO_MAX}.")

        gpio = gpio_slot(number, kind)

    return {"name": name, "type": kind, "data_type": data_type, "gpio": gpio}


def max_gram_of(body: dict) -> float | None:
    """The full level, or None for "not declared, use the default"."""
    raw = body.get("max_gram")

    if raw in (None, ""):
        return None

    max_gram = gram_of(raw, "Mức tối đa")

    if max_gram <= 0:
        raise AdminError("Mức tối đa phải lớn hơn 0.")

    return max_gram


def save_ingredient(body: dict) -> dict:
    """Add an ingredient, or change what an existing one is.

    NOT its amount. Topping up a bottle and re-wiring a pump are done by
    different people at different times, and one form doing both is one
    form in which a refill can quietly rewrite a GPIO pin. Amount is
    accepted only when the row is being created, where it means "what came
    with it".
    """
    fields = ingredient_fields(body)
    max_gram = max_gram_of(body)
    raw_id = body.get("ingredient_id")
    ingredient_id = None if raw_id in (None, "") else int(raw_id)

    adopt_capacity_file()

    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor()

        if ingredient_id is None:
            cursor.execute(
                "INSERT INTO ingredient (ingredient_name, type, data_type, "
                "amount, max_gram, gpio) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    fields["name"], fields["type"], fields["data_type"],
                    round(gram_of(body.get("amount") or 0, "Lượng tồn"), 2),
                    max_gram, fields["gpio"],
                ),
            )
            ingredient_id = int(cursor.lastrowid)
        else:
            # max_gram goes in with the rest of what this ingredient IS,
            # in the one statement, so a save either changes all of it or
            # none of it. It used to be written to a separate file after
            # the commit, which meant a crash in between left a container
            # whose declared size belonged to the version before the edit.
            cursor.execute(
                "UPDATE ingredient SET ingredient_name = %s, type = %s, "
                "data_type = %s, max_gram = %s, gpio = %s "
                "WHERE ingredient_id = %s",
                (
                    fields["name"], fields["type"], fields["data_type"],
                    max_gram, fields["gpio"], ingredient_id,
                ),
            )

            # rowcount 0 is also "saved the same values again", which is not
            # an error. Only a row that is not there is.
            if cursor.rowcount == 0:
                cursor.execute(
                    "SELECT 1 FROM ingredient WHERE ingredient_id = %s",
                    (ingredient_id,),
                )

                if cursor.fetchone() is None:
                    raise AdminError(
                        f"Không có nguyên liệu id {ingredient_id}.", 404)

        connection.commit()
    except AdminError:
        if connection is not None:
            connection.rollback()
        raise
    except Exception as error:          # noqa: BLE001 - reported to the page
        if connection is not None:
            connection.rollback()

        # The two uniqueness rules an admin can actually trip, named as
        # what they mean rather than as the index that caught them.
        text = str(error)

        if "ingredient_name" in text and "Duplicate" in text:
            raise AdminError(
                f"Đã có nguyên liệu tên \"{fields['name']}\".") from error

        if "uq_ingredient_type_gpio" in text:
            raise AdminError(
                f"GPIO {fields['gpio']} đã được gán cho một nguyên liệu "
                f"{fields['type']} khác.") from error

        raise AdminError(f"Không lưu được: {error}", 500) from error
    finally:
        close_database_resources(cursor, connection)

    return {"ingredient_id": ingredient_id, "name": fields["name"]}


def delete_ingredient(ingredient_id: int) -> dict:
    """Remove an ingredient the machine no longer has.

    Refused while any recipe still names it. The foreign key would refuse
    anyway, one step later and in driver language; counted here instead so
    the answer says how many drinks have to be edited first.

    There is no recycle bin for ingredients, unlike drinks. A binned drink
    still has to come back exactly as it was, recipe and all; an
    ingredient that no recipe uses is carrying nothing.
    """
    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT ingredient_name FROM ingredient WHERE ingredient_id = %s",
            (ingredient_id,),
        )
        row = cursor.fetchone()

        if row is None:
            raise AdminError(f"Không có nguyên liệu id {ingredient_id}.", 404)

        cursor.execute(
            "SELECT COUNT(DISTINCT drink_id) AS drinks FROM recipe "
            "WHERE ingredient_id = %s",
            (ingredient_id,),
        )
        used_in = int(cursor.fetchone()["drinks"])

        if used_in:
            raise AdminError(
                f"\"{row['ingredient_name']}\" đang nằm trong công thức của "
                f"{used_in} món. Sửa các công thức đó trước rồi mới xóa "
                f"được nguyên liệu.")

        cursor.execute(
            "DELETE FROM ingredient WHERE ingredient_id = %s",
            (ingredient_id,),
        )
        connection.commit()
    except AdminError:
        if connection is not None:
            connection.rollback()
        raise
    finally:
        close_database_resources(cursor, connection)

    # No capacity to sweep up afterwards: max_gram is part of the row and
    # went with it. While it lived in a file keyed by ingredient_id, a
    # forgotten sweep here left a size behind for the next ingredient to
    # be handed that auto-increment id to inherit.
    return {"ingredient_id": ingredient_id, "name": row["ingredient_name"]}


# --------------------------------------------------------------------------
# dispatch
#
# Written as two plain functions rather than inside the handler class,
# because store_gui/serve.py mounts the same endpoints on the store port
# and there must be exactly one copy of the rule about who may call them.
# A second implementation is a second place to forget the auth check.
#
# Both return None when the path is not ours, which is how each server
# tells "not an admin endpoint" from "an admin endpoint that refused".
# --------------------------------------------------------------------------
def drink_id_of(body: dict) -> int:
    try:
        return int(body.get("drink_id"))
    except (TypeError, ValueError):
        raise AdminError("Thiếu drink_id.") from None


def price_of(body: dict) -> float:
    """Validate here, not only in the browser.

    The number arrives as whatever was typed into a text box, and an empty
    cell reads as "". Refusing it with a sentence is what stops a drink
    quietly becoming free.
    """
    raw = body.get("price")

    try:
        price = float(str(raw).strip())
    except (TypeError, ValueError):
        raise AdminError(f"Giá không hợp lệ: {raw!r}.") from None

    if price != price or price in (float("inf"), float("-inf")):
        raise AdminError("Giá không hợp lệ.")

    if not 0 <= price <= PRICE_MAX:
        raise AdminError(f"Giá phải nằm trong khoảng 0 - {PRICE_MAX}.")

    return price


# --------------------------------------------------------------------------
# WHO MAY REACH WHAT
#
# Every endpoint belongs to exactly one AREA, and every role is a set of
# areas. Two tables rather than a check written into each handler, because
# a permission written thirty times is a permission that will be thirty
# different things by next year -- and the one that gets forgotten is not
# a bug you see, it is a door left open.
#
# THE SCREEN DOES NOT DECIDE ANY OF THIS.
#   admin-guard.js hides the pages a role cannot use, which is courtesy,
#   not security: it saves somebody clicking into a screen that would only
#   refuse them. What actually stops the request is dispatch_get() and
#   dispatch_post() consulting this map on every call, from the role read
#   out of the database row -- not from the token, so a demotion lands on
#   the next request rather than the next login.
# --------------------------------------------------------------------------

# The areas, the defaults and the page map now live in
# admin_gui/permissions.py, because they became editable and so grew a
# database, a cache and a set of refusals -- more than a constant's worth
# of behaviour to leave sitting in the middle of this file.
AREA_SHELL = permissions.AREA_SHELL
AREA_USERS = permissions.AREA_USERS
AREA_CATALOGUE = permissions.AREA_CATALOGUE
AREA_STOCK = permissions.AREA_STOCK
AREA_REFILL = permissions.AREA_REFILL
AREA_REPORT = permissions.AREA_REPORT
AREA_TICKETS = permissions.AREA_TICKETS
AREA_ERRORS = permissions.AREA_ERRORS
AREA_ERRORS_PURGE = permissions.AREA_ERRORS_PURGE

# WHICH AREA EACH ENDPOINT BELONGS TO.
#
# This one stays in code and is NOT editable from the screen, deliberately.
# Moving an endpoint between areas is a claim about what that endpoint
# does -- it needs reading the handler, and getting it wrong is a door
# left open rather than a screen somebody cannot reach. What the screen
# edits is which areas a ROLE holds, which is the shop's decision to make.
PATH_AREA = {
    # The menu payload is read by menu-store.js, which every admin page
    # loads for the mode chip in its topbar. Gating it by role would blank
    # the shell of every page a staff account is allowed to open.
    MENU_PATH: AREA_SHELL,
    WHOAMI_PATH: AREA_SHELL,
    MY_PASSWORD_PATH: AREA_SHELL,
    # Read by the refill screen to list what is in the machine, so it is
    # not catalogue work. Writing an ingredient is -- see below.
    INGREDIENTS_PATH: AREA_SHELL,

    USERS_PATH: AREA_USERS,
    USER_SAVE_PATH: AREA_USERS,
    USER_PASSWORD_PATH: AREA_USERS,
    USER_ROLE_PATH: AREA_USERS,
    USER_ACTIVE_PATH: AREA_USERS,
    USER_DELETE_PATH: AREA_USERS,
    PERMISSIONS_PATH: AREA_USERS,
    PERMISSIONS_SAVE_PATH: AREA_USERS,

    EDITOR_PATH: AREA_CATALOGUE,
    RECIPE_PATH: AREA_CATALOGUE,
    AVAILABLE_PATH: AREA_CATALOGUE,
    PRICE_PATH: AREA_CATALOGUE,
    FEATURED_PATH: AREA_CATALOGUE,
    FEATURED_CONFIG_PATH: AREA_CATALOGUE,
    BESTSELLER_CONFIG_PATH: AREA_CATALOGUE,
    LAYOUT_PATH: AREA_CATALOGUE,
    DELETE_PATH: AREA_CATALOGUE,
    RESTORE_PATH: AREA_CATALOGUE,
    PURGE_PATH: AREA_CATALOGUE,
    BIN_PATH: AREA_CATALOGUE,
    IMAGES_PATH: AREA_CATALOGUE,
    IMAGE_UPLOAD_PATH: AREA_CATALOGUE,
    MEDIA_LIST_PATH: AREA_CATALOGUE,
    MEDIA_UPLOAD_PATH: AREA_CATALOGUE,

    INGREDIENT_SAVE_PATH: AREA_STOCK,
    INGREDIENT_DELETE_PATH: AREA_STOCK,

    INGREDIENT_REFILL_PATH: AREA_REFILL,
    INGREDIENT_REFILL_ALL_PATH: AREA_REFILL,

    REPORT_PATH: AREA_REPORT,
    ORDERS_PATH: AREA_REPORT,

    ERRORS_PATH: AREA_ERRORS,
    # NOT AREA_ERRORS. Reading the log and pruning it are different
    # powers, and the whole point of the log is that the second one is
    # rare and deliberate.
    ERRORS_DELETE_PATH: AREA_ERRORS_PURGE,

    TICKETS_PATH: AREA_TICKETS,
    TICKET_STATUS_PATH: AREA_TICKETS,
    TICKET_REPRINT_PATH: AREA_TICKETS,

    # Gated like the page it lives on: AREA_REFILL is what unlocks "mode"
    # in permissions.AREA_PAGES. Only the POST ever reaches this table --
    # the GET is answered above require_login(), for the customer screen.
    ORDER_MODE_PATH: AREA_REFILL,

    # The screen's resolution rides with the operation mode: both are
    # "how this machine is set up to sell", both live on the same rail,
    # and neither is business data. AREA_REFILL is what already opens
    # that page, so this needs no new permission to administer.
    DISPLAY_PATH: AREA_REFILL,
    DISPLAY_APPLY_PATH: AREA_REFILL,
    DISPLAY_KEEP_PATH: AREA_REFILL,
}

pages_for_role = permissions.pages_for_role


def require_login(token: str | None) -> dict:
    """Every endpoint below this line needs a real session.

    Returns the account -- username, role and id -- read fresh from the
    row, not from the token.

    401 rather than 403, because the page acts on it: menu-store.js sends
    the customer back to the login screen on a 401 instead of showing a
    toast about a menu it was never going to get.
    """
    if not auth.is_configured():
        raise AdminError(
            "Chưa có tài khoản admin nào. Chạy trên máy: "
            "python3 -m admin_gui.auth --set-password --user <tên>",
            401,
        )

    try:
        return auth.check_token(token)
    except auth.AuthError as error:
        raise AdminError(str(error), 401) from error


def require_permission(path: str, account: dict) -> dict:
    """Refuse a signed-in account that may not reach this endpoint.

    403, not 401: the session is perfectly good and logging in again would
    not help. The page keeps its session and says so.

    A path missing from PATH_AREA is refused rather than allowed. A new
    endpoint should not become world-readable by having been forgotten --
    the failure that costs an afternoon is far cheaper than the one that
    does not fail at all.
    """
    area = PATH_AREA.get(path)

    if area is None:
        raise AdminError(
            f"Endpoint {path} chưa được phân quyền.", 403,
        )

    # 503, không phải 403 hay 500.
    #
    # Không đọc được bảng phân quyền thì server KHÔNG BIẾT người này được
    # làm gì. Đoán bừa theo mặc định là nới quyền cho họ vì một sự cố hạ
    # tầng -- xem admin_gui/permissions.py, _read_overrides(). Nên từ chối.
    #
    # 403 sẽ nói dối ("bạn không có quyền" -- chưa chắc), 500 nói đây là
    # lỗi lập trình. 503 nói đúng cái đang xảy ra: tạm thời không phục vụ
    # được, thử lại sau.
    try:
        held = permissions.role_areas(account.get("role", ""))
    except permissions.PermissionReadError as error:
        raise AdminError(
            "Không đọc được phân quyền từ database nên console tạm khoá. "
            "Đây gần như luôn là MySQL đang trục trặc; thử lại sau ít phút.",
            503,
        ) from error

    if area not in held:
        raise AdminError(
            f"Tài khoản {account.get('role_label', '')} không có quyền dùng "
            "chức năng này.", 403,
        )

    return account


def login(body: dict) -> tuple[int, dict]:
    """Check a username and password, and hand back a session token.

    The same sentence for a wrong username and a wrong password, on
    purpose: telling them apart tells a stranger which half they got right.
    """
    user = str(body.get("user") or "").strip()
    password = str(body.get("password") or "")

    if not auth.is_configured():
        return 503, {
            "ok": False,
            "error": "Chưa đặt mật khẩu admin trên máy này. Chạy: "
                     "python3 -m admin_gui.auth --set-password",
        }

    if not user or not password:
        return 400, {"ok": False,
                     "error": "Vui lòng nhập đủ tên đăng nhập và mật khẩu."}

    try:
        account = auth.verify_password(user, password)
    except auth.AuthError as error:
        # A deactivated account. Said plainly rather than as "sai mật
        # khẩu": the password WAS right, and sending somebody away to
        # hunt for a typo they did not make wastes their evening.
        return 403, {"ok": False, "error": str(error)}

    if account is None:
        return 401, {"ok": False,
                     "error": "Sai tên đăng nhập hoặc mật khẩu."}

    auth.note_login(account["user_id"])

    # The role AND the page list travel to the page so the console can hide
    # what this person cannot use. Neither GRANTS anything -- every request
    # is re-checked against the row; see require_permission().
    #
    # `pages` is sent here, not just from /api/admin/whoami, because the
    # browser has to draw the rail before whoami can answer. Without it
    # admin-guard.js had to keep its own copy of the matrix, and that copy
    # had already drifted: it listed `report` for staff, which this server
    # does not grant, so a staff console painted "Báo cáo" and then took it
    # away a moment later. A matrix the owner can edit at runtime (see
    # /api/permissions/save) can never be mirrored in a constant.
    # Cùng lý do với require_permission(): không biết người này mở được
    # trang nào thì không phát token, vì cái token đó sẽ đi kèm một danh
    # sách trang đoán bừa.
    try:
        pages = pages_for_role(account["role"])
    except permissions.PermissionReadError:
        return 503, {
            "ok": False,
            "error": "Không đọc được phân quyền từ database nên chưa đăng "
                     "nhập được. Thử lại sau ít phút.",
        }

    return 200, {
        "ok": True,
        **auth.issue_token(account["username"]),
        "role": account["role"],
        "role_label": auth.ROLE_LABEL.get(account["role"], account["role"]),
        "display_name": account["display_name"] or "",
        "pages": pages,
    }



# --------------------------------------------------------------------------
# the fault log, and the tickets
#
# Both of these are windows onto a table the machine writes and nothing on
# the admin side owns. They are read-only with one exception -- a ticket's
# status, which staff sometimes have to correct by hand when a label is
# lost or a drink is made without one.
# --------------------------------------------------------------------------

def _day_bounds(from_text: str, to_text: str) -> tuple[str, str]:
    """Turn two YYYY-MM-DD strings into an inclusive-day range.

    The `to` date is pushed to the START of the following day rather than
    23:59:59: error_log.created_at is DATETIME(3), so a fault at 23:59:59.4
    on the last day is inside the range the user asked for and a <= on
    seconds would drop it.
    """
    today = datetime.now().date()

    def parse(text: str, fallback):
        try:
            return datetime.strptime(str(text)[:10], "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return fallback

    start = parse(from_text, today - timedelta(days=7))
    end = parse(to_text, today)

    if end < start:
        start, end = end, start

    return (start.strftime("%Y-%m-%d 00:00:00"),
            (end + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00"))


# The severities the log is allowed to hold, mirrored from
# database/error_log.py. A severity outside this list is a typo or a
# crafted request, and either way it must not reach the SQL.
ERROR_SEVERITIES = ("info", "warning", "error")


def _error_filter(from_text: str, to_text: str, severity: str,
                  ticket: str = "") -> tuple[str, list[Any]]:
    """The WHERE clause behind both reading the log and deleting from it.

    ONE FUNCTION ON PURPOSE
        The delete acts on exactly what the page was showing, which is
        only true while the two are built by the same code. Two copies of
        this would agree today and disagree the first time a filter is
        added to one of them -- and the failure mode there is deleting
        rows the person never saw listed.

    A date range and a severity. It also took a category until
    2026-09-07, when that column was dropped.

    `ticket` REPLACES the date range rather than narrowing inside it.
    The tickets page links here with one serial, and a link from a row
    has to land on that row's faults -- an empty page because the range
    happened to say "today" would make the link useless on exactly the
    ticket somebody is investigating. It matches on the tag at the head
    of the message, which is where a fault records its ticket now that
    error_log.ticket_key is gone; see database/error_log.py.

    Only delete_errors() is affected by that swap, and it refuses a
    ticket outright -- there is no date range to scope it to, and
    "delete this ticket's faults" is the tidying the log exists to
    survive.
    """
    if ticket:
        where = ["message LIKE %s"]
        params: list[Any] = [error_log.ticket_like(ticket)]
    else:
        start, end = _day_bounds(from_text, to_text)
        where = ["created_at >= %s", "created_at < %s"]
        params = [start, end]

    if severity in ERROR_SEVERITIES:
        where.append("severity = %s")
        params.append(severity)

    return " AND ".join(where), params


def _ticket_serial(text: str) -> str:
    """A ticket serial from the query string, or "" if it is not one.

    Cleaned here and nowhere else. error_log.ticket_like() puts the value
    through int(), which would raise on anything else -- and a query
    string is the one input a stranger writes, so it is checked before it
    gets that far rather than caught afterwards. 0 and negatives are not
    serials either: order_ticket.serial is AUTO_INCREMENT from 1.
    """
    try:
        serial = int(str(text).strip())
    except (TypeError, ValueError):
        return ""

    return str(serial) if serial > 0 else ""


def errors_payload(from_text: str, to_text: str,
                   severity: str = "", ticket: str = "") -> dict:
    """Faults in a date range, newest first. Or one ticket's, at any date.

    `ticket` is a serial the tickets page linked here with. It ignores
    the date range -- see _error_filter().
    """
    ticket = _ticket_serial(ticket)
    clause, params = _error_filter(from_text, to_text, severity, ticket)
    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT error_id, created_at, severity, "
            "       drink_id, drink_name, step_label, step_type, message "
            f"FROM error_log WHERE {clause} "
            "ORDER BY created_at DESC, error_id DESC LIMIT %s",
            tuple(params) + (LOG_PAGE_LIMIT,),
        )

        rows = []

        for row in cursor.fetchall():
            # The serial comes out of the head of the message, which is
            # where the machine wrote it. Taken OFF the sentence at the
            # same time: the page shows it as its own column with a link
            # to the ticket, and leaving the tag in place would repeat it
            # on every row. Rows written before 2026-09-07 have no tag
            # and come back with serial None, which is the truth about
            # them -- nothing backfills what the dropped column knew.
            serial, message = error_log.split_ticket(row["message"])

            rows.append({
                "error_id": int(row["error_id"]),
                "created_at": row["created_at"].isoformat(sep=" ",
                                                          timespec="milliseconds")
                if row["created_at"] else None,
                "severity": row["severity"],
                "drink_id": row["drink_id"],
                "drink_name": row["drink_name"],
                "step_label": row["step_label"],
                "step_type": row["step_type"],
                "ticket_serial": serial,
                "message": message,
            })

        # No dropdown data left to gather: the categories list was built
        # from a column dropped on 2026-09-07, and severity is a fixed
        # vocabulary the page already knows.
        return {
            "errors": rows,
            # Echoed back as the server read it, not as the browser sent
            # it. The page says "showing one ticket" from this, so it has
            # to be the value that actually filtered the query -- a
            # rejected serial must not leave a banner claiming a
            # narrowing that is not in force.
            "ticket": int(ticket) if ticket else None,
            "truncated": len(rows) >= LOG_PAGE_LIMIT,
            "limit": LOG_PAGE_LIMIT,
        }
    finally:
        close_database_resources(cursor, connection)


def delete_errors(body: dict) -> dict:
    """Delete fault-log rows in a date range. With preview, only count them.

    WHY THIS EXISTS AT ALL
        The fault log used to be read-only, and the reasoning still holds:
        a log somebody can tidy is not evidence, and "had this gone wrong
        before?" stops being answerable the first time an inconvenient
        entry is removed. What broke that rule in practice is volume --
        a machine with a flaky load cell writes thousands of rows a week,
        and a log nobody can face opening is not evidence either.

        So the delete is deliberately narrow: it takes a DATE RANGE and
        the filters the page is showing, never "everything". Clearing one
        week of resolved load-cell noise is a different act from emptying
        the table, and only the first one has an interface.

    THE TWO THINGS THAT KEEP IT HONEST
        1.  Its own permission area (AREA_ERRORS_PURGE, owner-only by
            default). Reading the log and pruning it are not one power.
        2.  A required date range. `from` and `to` are not optional and
            not defaulted -- _day_bounds() would happily invent "the last
            seven days" from two empty strings, which is exactly the
            silent deletion this must not do. Since the category column
            was dropped on 2026-09-07 the range and the severity are the
            only narrowing there is, which makes that requirement carry
            more weight than it did.

        A deletion is NOT recorded back into the log. That was here and
        was taken out deliberately: on a log pruned down to nothing, the
        record of the pruning was the only row left, which made the
        screen read as though the delete had failed.

    WHY PREVIEW IS A SEPARATE ROUND TRIP
        The list on screen is capped at LOG_PAGE_LIMIT rows, so what the
        person can see is not what the filter matches. The dialog has to
        say a real number, and the only thing that knows it is the same
        COUNT(*) this runs. Same shape as /api/ticket's `preview`.

        The count is not re-checked at delete time. A machine mid-fault
        writes rows while the dialog is open, and refusing the delete
        because the number moved would make the button unusable on
        exactly the machine that needs it. The response reports what was
        actually removed instead of promising what was counted.
    """
    from_text = str(body.get("from") or "").strip()
    to_text = str(body.get("to") or "").strip()

    # Both dates required, and parsed strictly here rather than left to
    # _day_bounds()'s fallbacks -- see rule 2 above.
    for label, text in (("Từ ngày", from_text), ("Đến ngày", to_text)):
        try:
            datetime.strptime(text[:10], "%Y-%m-%d")
        except (TypeError, ValueError):
            raise AdminError(
                f"Phải chọn {label} trước khi xoá nhật ký.", 400,
            ) from None

    # Refused rather than ignored. The page hides the button while the
    # list is narrowed to one ticket, but that is courtesy; this is the
    # boundary. A ticket-scoped delete has no date range to bound it, and
    # "remove this order's faults" is precisely the tidying the log
    # exists to survive -- so it is not something this endpoint can be
    # talked into doing.
    if str(body.get("ticket") or "").strip():
        raise AdminError(
            "Không xoá được khi đang xem sự cố của một vé. "
            "Quay lại toàn bộ nhật ký và chọn khoảng ngày.", 400,
        )

    severity = str(body.get("severity") or "").strip()
    preview = bool(body.get("preview"))

    clause, params = _error_filter(from_text, to_text, severity)
    start, end = _day_bounds(from_text, to_text)

    # _day_bounds() hands back a HALF-OPEN range: `end` is midnight of the
    # day after the last one included. Reporting that raw would put a date
    # in the confirmation dialog -- and in the audit entry -- that is not
    # among the days being deleted, which is the one thing this dialog
    # exists to state correctly. Read back from the bounds rather than
    # from the input, so a reversed range (_day_bounds swaps it) is
    # described the way it will actually be applied.
    shown_from = start[:10]
    shown_to = (datetime.strptime(end[:10], "%Y-%m-%d")
                - timedelta(days=1)).strftime("%Y-%m-%d")
    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor()

        cursor.execute(f"SELECT COUNT(*) FROM error_log WHERE {clause}",
                       tuple(params))
        matched = int((cursor.fetchone() or [0])[0])

        if preview:
            return {"preview": True, "count": matched,
                    "from": shown_from, "to": shown_to}

        if matched:
            cursor.execute(f"DELETE FROM error_log WHERE {clause}",
                           tuple(params))
            connection.commit()

        deleted = int(cursor.rowcount) if matched else 0
    finally:
        close_database_resources(cursor, connection)

    return {"deleted": deleted, "from": shown_from, "to": shown_to}


def _fault_counts(cursor, serials: list[int], since: str) -> dict[int, int]:
    """How many faults each of these tickets recorded. {} if none did.

    HOW A TICKET IS MATCHED TO ITS FAULTS
        By the tag at the head of error_log.message, which is where a
        fault records its ticket now that error_log.ticket_key has been
        dropped. Nothing is joined and no column was added -- see HOW A
        FAULT STILL NAMES ITS TICKET in database/error_log.py.

    ONE QUERY FOR THE PAGE, NOT ONE PER ROW
        The obvious shape is a correlated subquery counting each ticket's
        faults inside the ticket SELECT. With no column to index, that is
        a LIKE against the whole fault log per ticket row, up to
        LOG_PAGE_LIMIT of them -- the same scan repeated hundreds of
        times for one screen. This reads the log once instead.

    WHY LEFT(message, ...)
        So the tag can be split in Python, by the same function that
        wrote it, without dragging every fault's full sentence across the
        wire -- and without a second, SQL-flavoured spelling of the tag
        living here to drift from the first.

    `since` is the oldest ticket on the page, and it is a real bound
    rather than an optimisation: a fault tagged with a serial was written
    after that ticket was claimed, which is after it was created, so no
    fault belonging to these tickets can predate the oldest of them. It
    is also what lets this use idx_error_log_time instead of reading the
    table back to the first row it ever held. There is no upper bound on
    purpose -- a drink poured just after midnight still belongs to the
    ticket sold the evening before.
    """
    if not serials or not since:
        return {}

    wanted = set(serials)
    counts: dict[int, int] = {}

    cursor.execute(
        "SELECT LEFT(message, %s) AS head FROM error_log "
        "WHERE created_at >= %s AND message LIKE %s",
        (error_log.TICKET_TAG_CHARS, since, error_log.ANY_TICKET_LIKE),
    )

    for row in cursor.fetchall():
        serial, _ = error_log.split_ticket(row["head"])

        if serial in wanted:
            counts[serial] = counts.get(serial, 0) + 1

    return counts


def tickets_payload(from_text: str, to_text: str, status: str,
                    serial: str = "") -> dict:
    """Tickets issued in a date range, newest first. Or one, at any date.

    `serial` is the mirror of errors_payload()'s `ticket`: the fault
    screen links here with the ticket a fault named, and that link has to
    land on the ticket whenever it was sold, not on an empty page because
    the range happened to say "today". So it REPLACES the date range,
    exactly as the other direction does.
    """
    serial = _ticket_serial(serial)
    start, end = _day_bounds(from_text, to_text)

    if serial:
        where = ["t.serial = %s"]
        params: list[Any] = [serial]
    else:
        where = ["t.created_at >= %s", "t.created_at < %s"]
        params = [start, end]

    if status:
        where.append("t.status = %s")
        params.append(status)

    clause = " AND ".join(where)
    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT t.serial, t.drink_id, t.price, t.status, t.note, "
            "       t.created_at, t.scanned_at, t.completed_at, "
            "       t.payload_hash, "
            # The ticket's own copy first: it is the name as sold, and it
            # survives the drink being renamed or taken off the menu.
            # The fault count is NOT a subquery here -- see
            # _fault_counts() below for why one query for the page beats
            # one per row.
            "       COALESCE(t.drink_name, d.drink_name) AS drink_name "
            "FROM order_ticket t "
            "LEFT JOIN drink d ON d.drink_id = t.drink_id "
            f"WHERE {clause} "
            "ORDER BY t.serial DESC LIMIT %s",
            tuple(params) + (LOG_PAGE_LIMIT,),
        )

        rows = [
            {
                "serial": int(row["serial"]),
                "drink_id": row["drink_id"],
                "drink_name": row["drink_name"],
                "price": float(row["price"]) if row["price"] is not None else None,
                "status": row["status"],
                "note": row["note"],
                "created_at": str(row["created_at"]) if row["created_at"] else None,
                "scanned_at": str(row["scanned_at"]) if row["scanned_at"] else None,
                "completed_at": str(row["completed_at"]) if row["completed_at"] else None,
                "payload_hash": row["payload_hash"],
            }
            for row in cursor.fetchall()
        ]

        counts = _fault_counts(
            cursor,
            [row["serial"] for row in rows],
            # The oldest ticket ON THE PAGE, not the start of the filter:
            # it is a tighter bound, and it is the only one there is when
            # the page was opened on one serial and no date range applied.
            min((row["created_at"] for row in rows if row["created_at"]),
                default=""),
        )

        for row in rows:
            row["fault_count"] = counts.get(row["serial"], 0)

        return {
            "tickets": rows,
            # As the server read it, for the same reason errors_payload()
            # echoes its own: the banner has to describe the narrowing
            # actually in force, not the one the URL asked for.
            "serial": int(serial) if serial else None,
            "statuses": list(TICKET_STATUSES),
            "settable": list(STATUS_SETTABLE),
            "locked": list(STATUS_LOCKED),
            "truncated": len(rows) >= LOG_PAGE_LIMIT,
            "limit": LOG_PAGE_LIMIT,
        }
    finally:
        close_database_resources(cursor, connection)


def set_ticket_status(serial: int, status: str) -> dict:
    """Correct one ticket's status by hand.

    WHAT MAY BE WRITTEN
        'unused' and 'used', and nothing else. The other three are the
        machine's to write and each is a claim about a moment:
        'in_progress' says a runner is holding this ticket right now,
        'expired' is reached by age, 'noqr_err' says a run ended with no
        label left to scan. A desk asserting any of them would have the
        console inventing machine state.

        The two that are allowed are the two a person can actually know:
        the drink was handed over, or it was not.

    WHAT MAY NOT BE MOVED
        A ticket already in an error state. It is a dead end on purpose --
        there is no label to scan again -- so reopening it would put a row
        back in the pool that no customer can ever redeem, and mark it
        'used' would count a drink nobody was sold. Its record stands.

    The timestamps are left exactly as they are, in every case. They record
    what actually happened to the machine, and a correction made at a desk
    did not make any of it happen. Writing them would turn the audit trail
    into a guess -- so a released ticket keeps its scanned_at, and the two
    fields are allowed to disagree. The status says what to believe; the
    timestamps say what was observed.
    """
    if status not in STATUS_SETTABLE:
        allowed = "', '".join(STATUS_SETTABLE)
        raise AdminError(
            f"Chỉ có thể đổi sang '{allowed}'.", 400,
        )

    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor()

        # Read first: the refusal depends on what the ticket IS, and a
        # rowcount of 0 cannot tell "no such ticket" from "already that
        # status" apart.
        cursor.execute(
            "SELECT status FROM order_ticket WHERE serial = %s",
            (int(serial),),
        )
        row = cursor.fetchone()

        if row is None:
            raise AdminError(f"Không có vé số {serial}.", 404)

        current = str(row[0])

        if current in STATUS_LOCKED:
            raise AdminError(
                f"Vé lỗi ({current}) không đổi trạng thái được.", 409,
            )

        cursor.execute(
            "UPDATE order_ticket SET status = %s WHERE serial = %s",
            (status, int(serial)),
        )
        connection.commit()
        return {"serial": int(serial), "status": status, "was": current}
    finally:
        close_database_resources(cursor, connection)


def reprint_ticket(serial: int) -> dict:
    """Print another copy of one ticket's label.

    ANOTHER COPY, NEVER ANOTHER CODE
        This reads the payload minted when the drink was sold and sends
        those same digits back to the printer. It never calls
        order_ticket.issue(), and that distinction is the entire safety of
        the feature: a payload is claimed atomically by its hash, so any
        number of copies of ONE label still buy exactly one drink, while a
        newly issued payload would be a second live code -- a second sale
        for a drink paid for once.

    ONLY A TICKET THAT CAN STILL BE SCANNED
        'unused' and inside its 24 hours. Every other row would print a
        label that is already dead: order_ticket.claim() refuses a used
        one, expires an old one in the same transaction it would have
        claimed it, and a 'noqr_err' row is a dead end by design. Handing
        a customer paper that cannot work is worse than telling the person
        at the desk why -- they can still put the drink through with
        "Start on the machine (no scan)" on the store screen.

        The age is checked against the same TICKET_LIFETIME_HOURS claim()
        uses, read from that module rather than repeated here, because a
        second copy of the number is a second chance to disagree with the
        one that actually decides.
    """
    from database.order_ticket import STATUS_UNUSED, TICKET_LIFETIME_HOURS

    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor(dictionary=True)

        # Read the whole answer in one go: the refusals below each need a
        # different field, and three round trips to say no is three
        # chances for the row to change underneath them.
        cursor.execute(
            "SELECT payload, status, drink_name, "
            "       created_at < NOW() - INTERVAL %s HOUR AS stale "
            "FROM order_ticket WHERE serial = %s",
            (TICKET_LIFETIME_HOURS, int(serial)),
        )
        row = cursor.fetchone()
    finally:
        close_database_resources(cursor, connection)

    if row is None:
        raise AdminError(f"Không có vé số {serial}.", 404)

    status = str(row["status"])

    if status != STATUS_UNUSED:
        raise AdminError(
            f"Vé số {serial} đang ở trạng thái '{status}', "
            "in lại cũng không quét được.", 409,
        )

    if row["stale"]:
        raise AdminError(
            f"Vé số {serial} đã quá {TICKET_LIFETIME_HOURS} giờ, "
            "máy sẽ từ chối khi quét.", 409,
        )

    payload = str(row["payload"] or "")

    if not payload:
        # Rows issued before the payload column existed. Nothing to print
        # and nothing to reconstruct -- the digits were never kept.
        raise AdminError(
            f"Vé số {serial} không lưu mã QR nên không in lại được.", 409,
        )

    try:
        printed, output = spool.send_payload(payload)
    except spool.PrinterUnavailable as error:
        raise AdminError(str(error), 500) from error
    except spool.PrinterTimeout as error:
        raise AdminError(str(error), 504) from error

    if not printed:
        raise AdminError(output or "Máy in không in được.", 500)

    return {
        "serial": int(serial),
        "drink_name": row["drink_name"],
        "message": output,
    }


# --------------------------------------------------------------------------
# accounts
#
# Every one of these is already behind require_permission(AREA_USERS), so
# only an owner reaches them. What is checked HERE is the second question:
# not "may you manage accounts" but "may you do this to THIS account".
# --------------------------------------------------------------------------

def _target_user(body: dict) -> dict:
    try:
        return auth.get_user(int(body.get("user_id") or 0))
    except auth.AuthError as error:
        raise AdminError(str(error), 404) from error


def _refuse_acting_on_peer(actor: dict, target: dict, verb: str) -> None:
    """An owner may not do this to another owner.

    Two owners able to remove each other is a race whose losing state is a
    shop locked out of its own console. The way to change an owner is the
    CLI on the machine, where standing in front of it is the check.

    Acting on YOURSELF is allowed for the things that are yours to decide
    -- your own password -- and refused for the ones that would remove
    your own way back in; each caller says which it is.
    """
    if target["role"] == auth.ROLE_OWNER and target["user_id"] != actor["user_id"]:
        raise AdminError(
            f"Không thể {verb} một tài khoản Chủ khác. Dùng lệnh trên máy: "
            "python3 -m admin_gui.auth", 409,
        )


def create_account(actor: dict, body: dict) -> dict:
    """Add an account."""
    try:
        return auth.create_user(
            str(body.get("username") or ""),
            str(body.get("password") or ""),
            str(body.get("role") or auth.ROLE_STAFF),
            str(body.get("display_name") or ""),
        )
    except auth.AuthError as error:
        raise AdminError(str(error), 400) from error


def set_account_password(actor: dict, body: dict) -> dict:
    """Reset somebody else's password."""
    target = _target_user(body)
    _refuse_acting_on_peer(actor, target, "đổi mật khẩu")

    try:
        auth.set_password(target["username"], str(body.get("password") or ""))
    except auth.AuthError as error:
        raise AdminError(str(error), 400) from error

    return {"username": target["username"]}


def set_account_role(actor: dict, body: dict) -> dict:
    target = _target_user(body)
    _refuse_acting_on_peer(actor, target, "đổi vai trò")

    if target["user_id"] == actor["user_id"]:
        # Demoting yourself is the one press that cannot be undone from
        # this screen: the moment it lands, this page is not yours to use.
        raise AdminError(
            "Không thể tự đổi vai trò của chính mình.", 409,
        )

    try:
        auth.set_role(target["user_id"], str(body.get("role") or ""))
    except auth.AuthError as error:
        raise AdminError(str(error), 409) from error

    return {"user_id": target["user_id"], "role": body.get("role")}


def set_account_active(actor: dict, body: dict) -> dict:
    target = _target_user(body)
    _refuse_acting_on_peer(actor, target, "bật/tắt")
    active = bool(body.get("active"))

    if target["user_id"] == actor["user_id"] and not active:
        raise AdminError("Không thể tự khoá tài khoản của chính mình.", 409)

    try:
        auth.set_active(target["user_id"], active)
    except auth.AuthError as error:
        raise AdminError(str(error), 409) from error

    return {"user_id": target["user_id"], "active": active}


def delete_account(actor: dict, body: dict) -> dict:
    target = _target_user(body)
    _refuse_acting_on_peer(actor, target, "xoá")

    if target["user_id"] == actor["user_id"]:
        raise AdminError("Không thể tự xoá tài khoản của chính mình.", 409)

    try:
        return auth.delete_user(target["user_id"])
    except auth.AuthError as error:
        raise AdminError(str(error), 409) from error


def save_permissions(actor: dict, body: dict) -> dict:
    """Replace one role's areas.

    One role per call, not the whole grid. A save that carried every role
    could take a right away from the role making the call as a side effect
    of a stale form -- two owners with the screen open, one saves, the
    other saves a minute later and silently undoes it. One role at a time
    makes each save say exactly what it means.
    """
    role = str(body.get("role") or "")

    try:
        stored = permissions.save_role_areas(
            role, body.get("areas") or [], actor.get("user", ""),
        )
    except permissions.PermissionError_ as error:
        raise AdminError(str(error), 400) from error

    # Reported back so the screen can redraw from what was ACTUALLY saved
    # rather than from what it sent -- the two differ whenever an
    # invariant added something, and a grid that shows the request rather
    # than the result is a grid that lies until the next reload.
    return {
        "role": role,
        "areas": sorted(permissions.role_areas(role)
                        - {permissions.AREA_SHELL}),
        "stored": sorted(stored),
    }


def change_my_password(actor: dict, body: dict) -> dict:
    """Change your own password, having proved you know the current one.

    The current password is required even though the session already
    proves who this is. A session is a tablet left unlocked on a counter;
    a password is the person. Without this, walking past an open console
    would be enough to take an account over.
    """
    current = str(body.get("current_password") or "")
    fresh = str(body.get("password") or "")

    try:
        if auth.verify_password(actor["user"], current) is None:
            raise AdminError("Mật khẩu hiện tại không đúng.", 403)

        auth.set_password(actor["user"], fresh)
    except auth.AuthError as error:
        raise AdminError(str(error), 400) from error

    # The change signs every session out, this one included, so the page
    # is told to send them back to the login screen rather than let them
    # discover it on their next click.
    return {"username": actor["user"], "signed_out": True}


def dispatch_get(path: str, raw_query: str,
                 token: str | None) -> tuple[int, dict] | None:
    """Answer an admin GET, or None if the path belongs to somebody else."""
    if path not in GET_PATHS:
        return None

    # The one GET that needs no session, answered before require_login()
    # rather than exempted inside it. The customer screen is a tablet
    # nobody signs in to, and it has to know which buttons to draw before
    # it can show an order at all -- so a 401 here would be a shop that
    # cannot sell. Nothing is given away: the answer is the buttons on
    # screen, visible to whoever is standing there. Writing it still needs
    # a session and AREA_REFILL -- see dispatch_post().
    if path == ORDER_MODE_PATH:
        return 200, {"ok": True, **order_mode.read()}

    try:
        account = require_permission(path, require_login(token))

        if path == WHOAMI_PATH:
            # What the console paints its shell from. Answered from the
            # row, so a role changed since login arrives here.
            return 200, {"ok": True, **account,
                         "pages": pages_for_role(account["role"])}

        if path == PERMISSIONS_PATH:
            return 200, {"ok": True, **permissions.current_matrix()}

        # NOT exempt from the session the way ORDER_MODE_PATH above is.
        # That one is read by the customer's tablet, which nobody signs
        # in to; nothing unauthenticated has any reason to know what
        # modes this machine's panel accepts.
        if path == DISPLAY_PATH:
            return 200, {"ok": True, **display_state()}

        if path == USERS_PATH:
            return 200, {"ok": True,
                         "users": auth.list_users(),
                         "roles": [{"id": r, "label": auth.ROLE_LABEL[r]}
                                   for r in auth.ROLES],
                         "me": account["user_id"],
                         "min_password": auth.MIN_PASSWORD_LENGTH}

        if path == MENU_PATH:
            return 200, {"ok": True, **menu_payload()}

        query = parse_qs(raw_query)

        if path == REPORT_PATH:
            return 200, {"ok": True, **report_payload(
                (query.get("from") or [""])[0],
                (query.get("to") or [""])[0],
                (query.get("category") or [""])[0],
            )}

        if path == IMAGES_PATH:
            return 200, {"ok": True, **list_images()}

        if path == MEDIA_LIST_PATH:
            return 200, {"ok": True, **list_media()}

        if path == BIN_PATH:
            return 200, {"ok": True, **binned_drinks()}

        if path == INGREDIENTS_PATH:
            return 200, {"ok": True, **ingredients_payload()}

        if path == ERRORS_PATH:
            # may_delete is answered here rather than left to the browser
            # to work out from a role name: the server is what knows, and
            # the page gets one answer instead of a second round trip that
            # could arrive after it has already drawn itself.
            return 200, {"ok": True, **errors_payload(
                (query.get("from") or [""])[0],
                (query.get("to") or [""])[0],
                (query.get("severity") or [""])[0],
                (query.get("ticket") or [""])[0],
            ), "may_delete": AREA_ERRORS_PURGE in permissions.role_areas(
                account.get("role", ""))}

        if path == TICKETS_PATH:
            return 200, {"ok": True, **tickets_payload(
                (query.get("from") or [""])[0],
                (query.get("to") or [""])[0],
                (query.get("status") or [""])[0],
                (query.get("serial") or [""])[0],
            )}

        if path == ORDERS_PATH:
            return 200, {"ok": True, **orders_payload(
                (query.get("from") or [""])[0],
                (query.get("to") or [""])[0],
                (query.get("category") or [""])[0],
                (query.get("page") or ["1"])[0],
            )}

        raw = (query.get("drink_id") or [""])[0].strip()
        drink_id = int(raw) if raw else None
        return 200, {"ok": True, **editor_payload(drink_id)}
    except AdminError as error:
        return error.status, {"ok": False, "error": error.message}
    except ValueError:
        return 400, {"ok": False, "error": "drink_id sai."}
    except Exception as error:          # noqa: BLE001 - reported to the page
        return 500, {"ok": False, "error": f"Lỗi database: {error}"}


# ============================================================
# KIOSK SCREEN RESOLUTION
# ============================================================
#
# How long a newly applied mode is given before it undoes itself. The
# customer panel has no keyboard and no mouse: a mode it cannot display
# leaves a black screen that nobody standing in the shop can get out of,
# and the machine sells nothing until somebody arrives with a monitor.
#
# So a change is applied on probation. The admin walks to the kiosk, sees
# that it is readable, and presses Keep. Saying nothing is a refusal --
# which is the correct default, because the most likely reason for saying
# nothing is that there is nothing to read.
DISPLAY_REVERT_SECONDS = 20

# The probation in progress, if any. One machine, one panel, one change
# at a time -- so one slot, under a lock, rather than a registry.
_display_pending: dict = {}
_display_lock = threading.Lock()


def display_state() -> dict:
    """What the panel can do, what it is doing, and what was chosen."""
    state = display_mode.query()
    native = next((row["pixels"] for row in state["modes"]
                   if row["preferred"]), 0)

    for row in state["modes"]:
        # What the admin actually wants to compare is not the pixel count
        # but the work: this is how much less there is to composite per
        # frame than at the panel's own mode.
        row["lighter"] = round(native / row["pixels"], 2) if native else 1.0

    with _display_lock:
        pending = dict(_display_pending)

    return {
        **state,
        "saved": display_mode.read()["mode"],
        "revertSeconds": DISPLAY_REVERT_SECONDS,
        "pending": pending.get("mode", None) if pending else None,
        "hasPending": bool(pending),
    }


def _display_revert(previous: str | None) -> None:
    """Put the old mode back because nobody confirmed the new one."""
    with _display_lock:
        _display_pending.clear()

    try:
        display_mode.apply(previous)
    except Exception as error:                      # noqa: BLE001 - logged
        # Nothing is left to report to: the request that started this
        # returned long ago. The fault log is the only place a failed
        # automatic revert can still be seen, and log_error() never
        # raises -- see THE ONE RULE in database/error_log.py.
        error_log.log_error(
            f"Màn hình: không quay lại được chế độ "
            f"{previous or 'mặc định'}: {error}")


def handle_display_apply(body: dict) -> tuple[int, dict]:
    """Switch the panel now, on probation, and save nothing yet.

    Returns the deadline rather than blocking on it: the page counts down
    on its own and the connection is free the whole time. If the admin
    closes the tab, walks away, or the browser they were holding loses
    the network, the timer still fires and the screen still comes back.
    """
    mode = body.get("mode")

    if mode is not None and not isinstance(mode, str):
        raise AdminError("Chế độ không hợp lệ.", 400)

    live = display_mode.query()["current"]

    with _display_lock:
        # A second change while one is on probation: the mode to come
        # back to is the one from BEFORE the first change, never the
        # unconfirmed one in between.
        previous = _display_pending.get("previous", live)
        timer = _display_pending.get("timer")

        if timer is not None:
            timer.cancel()

        _display_pending.clear()

    try:
        applied = display_mode.apply(mode)
    except display_mode.DisplayModeError as error:
        raise AdminError(str(error), 400) from error

    timer = threading.Timer(DISPLAY_REVERT_SECONDS,
                            _display_revert, args=(previous,))
    timer.daemon = True

    with _display_lock:
        _display_pending.update({"mode": mode, "previous": previous,
                                 "timer": timer})

    timer.start()

    return 200, {"ok": True, **applied, "previous": previous,
                 "revertSeconds": DISPLAY_REVERT_SECONDS}


def handle_display_keep() -> tuple[int, dict]:
    """Confirm the mode on probation and make it survive a reboot."""
    with _display_lock:
        pending = dict(_display_pending)
        timer = _display_pending.get("timer")

        if timer is not None:
            timer.cancel()

        _display_pending.clear()

    if not pending:
        raise AdminError("Không có thay đổi nào đang chờ xác nhận.", 400)

    try:
        saved = display_mode.write(pending["mode"])
    except display_mode.DisplayModeError as error:
        raise AdminError(str(error), 400) from error

    return 200, {"ok": True, **saved}


def dispatch_post(path: str, body: dict,
                  token: str | None) -> tuple[int, dict] | None:
    """Answer an admin POST, or None if the path belongs to somebody else."""
    if path == LOGIN_PATH:
        return login(body)

    if path not in POST_PATHS:
        return None

    try:
        account = require_permission(path, require_login(token))

        if path == ORDER_MODE_PATH:
            # OrderModeError is the "both switches off" refusal, and it is
            # the caller's mistake rather than the server's -- so it comes
            # back as a 400 carrying its own sentence, which the page shows
            # verbatim. See configuration/order_mode.py for why that is a
            # refusal and not a silent correction.
            try:
                return 200, {"ok": True, **order_mode.write(body)}
            except order_mode.OrderModeError as error:
                raise AdminError(str(error), 400) from error

        if path == DISPLAY_APPLY_PATH:
            return handle_display_apply(body)
        if path == DISPLAY_KEEP_PATH:
            return handle_display_keep()

        if path == USER_SAVE_PATH:
            return 200, {"ok": True, **create_account(account, body)}
        if path == USER_PASSWORD_PATH:
            return 200, {"ok": True, **set_account_password(account, body)}
        if path == USER_ROLE_PATH:
            return 200, {"ok": True, **set_account_role(account, body)}
        if path == USER_ACTIVE_PATH:
            return 200, {"ok": True, **set_account_active(account, body)}
        if path == USER_DELETE_PATH:
            return 200, {"ok": True, **delete_account(account, body)}
        if path == PERMISSIONS_SAVE_PATH:
            return 200, {"ok": True, **save_permissions(account, body)}
        if path == MY_PASSWORD_PATH:
            return 200, {"ok": True, **change_my_password(account, body)}

        if path == AVAILABLE_PATH:
            set_available(drink_id_of(body), bool(body.get("available")))
            saved = {}
        elif path == FEATURED_PATH:
            saved = set_featured(drink_id_of(body),
                                 bool(body.get("featured")))
        elif path == FEATURED_CONFIG_PATH:
            saved = save_featured_config(body)
        elif path == BESTSELLER_CONFIG_PATH:
            saved = save_bestseller_config(body)
        elif path == LAYOUT_PATH:
            saved = save_layout_order(body)
        elif path == PRICE_PATH:
            set_price(drink_id_of(body), price_of(body))
            saved = {}
        elif path == DELETE_PATH:
            saved = delete_drink(drink_id_of(body))
        elif path == RESTORE_PATH:
            saved = restore_drink(drink_id_of(body))
        elif path == PURGE_PATH:
            saved = purge_drink(drink_id_of(body))
        elif path == INGREDIENT_REFILL_PATH:
            saved = refill_ingredient(ingredient_id_of(body), body)
        elif path == INGREDIENT_REFILL_ALL_PATH:
            saved = refill_all_ingredients(body)
        elif path == TICKET_STATUS_PATH:
            answer = set_ticket_status(
                int(body.get("serial") or 0),
                str(body.get("status") or "").strip(),
            )
            return 200, {"ok": True, **answer}

        elif path == TICKET_REPRINT_PATH:
            answer = reprint_ticket(int(body.get("serial") or 0))
            return 200, {"ok": True, **answer}

        elif path == ERRORS_DELETE_PATH:
            # Returns before publish_to_pos() below: the fault log is not
            # part of the menu, and republishing it would be a write to
            # the customer screen for a change it cannot see.
            answer = delete_errors(body)
            return 200, {"ok": True, **answer}

        elif path == INGREDIENT_SAVE_PATH:
            saved = save_ingredient(body)
        elif path == INGREDIENT_DELETE_PATH:
            saved = delete_ingredient(ingredient_id_of(body))
        else:
            saved = save_recipe(body)

        # Every one of these changed the menu, so the customer screen's
        # copy is now wrong -- the ingredient writes included, because the
        # triggers turn a stock change into drink.in_stock, which is what
        # the POS reads as "sold out". Rewritten here rather than left to a
        # timer -- see publish_to_pos(). A failure is reported, not raised:
        # the database write already happened.
        warning = publish_to_pos()

        return 200, {"ok": True, **saved,
                     **({"warning": warning} if warning else {})}
    except AdminError as error:
        return error.status, {"ok": False, "error": error.message}
    except Exception as error:          # noqa: BLE001 - reported to the page
        return 500, {"ok": False, "error": f"Lỗi database: {error}"}


def handle_image_upload(handler) -> tuple[int, dict]:
    """Store one drink photo. See handle_upload() for the mechanics."""
    return handle_upload(
        handler,
        path=IMAGE_UPLOAD_PATH,
        max_bytes=IMAGE_MAX_BYTES,
        saver=save_image,
        noun="Ảnh",
    )


def handle_media_upload(handler) -> tuple[int, dict]:
    """Store one action step's clip. See handle_upload() for the mechanics."""
    return handle_upload(
        handler,
        path=MEDIA_UPLOAD_PATH,
        max_bytes=MEDIA_MAX_BYTES,
        saver=save_media,
        noun="Tệp",
    )


def handle_upload(handler, *, path, max_bytes, saver, noun) -> tuple[int, dict]:
    """Store an uploaded photo. The request BODY is the file itself.

    Not multipart and not JSON: the page sends the bytes raw with the
    filename in the query string. Python's standard library has no
    multipart parser worth the trouble here, and base64 inside JSON would
    inflate every upload by a third for nothing.

    The body is always read, even when the request is going to be
    refused. Leaving it unread desynchronises a keep-alive connection and
    the NEXT request is what appears broken.
    """
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError:
        return 400, {"ok": False, "error": "Content-Length không hợp lệ."}

    if length <= 0:
        return 400, {"ok": False, "error": f"Không có dữ liệu {noun.lower()}."}

    if length > max_bytes:
        # Refused -- but the body still has to come off the socket, or the
        # browser sees its connection break mid-send and reports a network
        # error instead of the sentence explaining what was wrong. Read
        # and discard it, up to a ceiling; past that the sender is not
        # worth waiting for and the connection closes.
        remaining = min(length, IMAGE_DRAIN_LIMIT)

        while remaining > 0:
            chunk = handler.rfile.read(min(65536, remaining))

            if not chunk:
                break

            remaining -= len(chunk)

        if length > IMAGE_DRAIN_LIMIT:
            handler.close_connection = True

        return 413, {
            "ok": False,
            "error": f"{noun} quá lớn ({length / 1_048_576:.1f} MB). "
                     f"Tối đa {max_bytes // 1_048_576} MB.",
        }

    data = handler.rfile.read(length)

    try:
        # These two do not go through dispatch_post() -- the body is a file,
        # so store_gui/serve.py answers them before it reads any JSON --
        # which means the permission check has to be made here or not at
        # all. `path` exists on this function for exactly that reason.
        require_permission(path, require_login(bearer_token(handler.headers)))
    except AdminError as error:
        return error.status, {"ok": False, "error": error.message}

    query = parse_qs(urlparse(handler.path).query)
    name = (query.get("name") or [""])[0]

    try:
        return 200, {"ok": True, **saver(name, data)}
    except AdminError as error:
        return error.status, {"ok": False, "error": error.message}
    except Exception as error:          # noqa: BLE001 - reported to the page
        return 500, {"ok": False,
                     "error": f"Không lưu được {noun.lower()}: {error}"}


def sniff_media(data: bytes) -> str:
    """The clip's real type as an extension, or "" if it is not one.

    GIF is delegated to sniff_image() -- it is a picture format the image
    path already recognises, and an action step is happy to loop one.
    """
    if data[4:8] == b"ftyp" and data[8:12] in MEDIA_MP4_BRANDS:
        return ".mp4"

    # EBML header. Shared with Matroska, which browsers will not play, so
    # the extension says webm and a .mkv renamed by hand simply will not
    # start -- the same failure it would have had under any other name.
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return ".webm"

    extension = sniff_image(data)

    return extension if extension == ".gif" else ""


def save_media(filename: str, data: bytes) -> dict:
    """Store one uploaded clip and return where it went."""
    if not data:
        raise AdminError("Tệp rỗng.")

    if len(data) > MEDIA_MAX_BYTES:
        raise AdminError(
            f"Tệp quá lớn ({len(data) / 1_048_576:.1f} MB). "
            f"Tối đa {MEDIA_MAX_BYTES // 1_048_576} MB.")

    extension = sniff_media(data)

    if not extension:
        raise AdminError(
            "Tệp này không phải phim hướng dẫn (chỉ nhận MP4, WEBM, GIF).")

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    name = safe_image_name(filename, extension, fallback="clip")
    target = MEDIA_DIR / name

    # Never silently replace another step's clip -- the same rule, and for
    # the same reason, as save_image().
    if target.exists():
        stem, suffix = target.stem, target.suffix
        number = 2

        while (MEDIA_DIR / f"{stem} {number}{suffix}").exists():
            number += 1

        target = MEDIA_DIR / f"{stem} {number}{suffix}"

    temporary = target.with_name(f".{target.name}.part")
    temporary.write_bytes(data)
    temporary.replace(target)

    answer = {
        "name": target.name,
        "path": f"recipe/media/{target.name}",
        "url": "../" + quote(f"recipe/media/{target.name}", safe="/"),
        "bytes": len(data),
    }

    if extension == ".gif" and len(data) > MEDIA_GIF_WARN_BYTES:
        answer["warning"] = (
            f"GIF này nặng {len(data) / 1_048_576:.1f} MB. "
            "Một đoạn MP4 cùng thời lượng thường chỉ khoảng 2 MB "
            "và cho màu đẹp hơn.")

    return answer


def bearer_token(headers) -> str | None:
    """Pull the session token out of an Authorization header."""
    value = headers.get("Authorization") or ""
    prefix = "Bearer "
    return value[len(prefix):].strip() if value.startswith(prefix) else None


def read_json_body(handler) -> dict:
    """Read a JSON request body, or {} if there is not one."""
    length = int(handler.headers.get("Content-Length", "0"))
    body = json.loads(handler.rfile.read(length) or b"{}")
    return body if isinstance(body, dict) else {}


def send_json(handler, status: int, payload: dict) -> None:
    """Write one JSON response. Shared so both servers answer alike."""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


# --------------------------------------------------------------------------
# http
# --------------------------------------------------------------------------
class AdminHandler(SimpleHTTPRequestHandler):
    """Serve the project directory, plus the admin API."""

    def translate_path(self, path: str) -> str:
        """Refuse anything outside the served directories -- 404, not 403.

        The whole project directory is this server's document root, so
        without this a browser can ask for .env or configuration/ and get
        them. See configuration/served_paths.py.
        """
        return served_paths.guard(super().translate_path(path))


    def end_headers(self) -> None:
        if self.path.split("?")[0].endswith(NEVER_CACHE_SUFFIXES):
            self.send_header("Cache-Control", "no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")

        super().end_headers()

    def do_GET(self) -> None:
        answer = dispatch_get(
            self.path.split("?")[0],
            urlparse(self.path).query,
            bearer_token(self.headers),
        )

        if answer is None:
            super().do_GET()
            return

        send_json(self, *answer)

    def do_POST(self) -> None:
        # The upload's body is a file, so it is handled before anything
        # tries to parse the body as JSON.
        route = self.path.split("?")[0]

        if route == IMAGE_UPLOAD_PATH:
            send_json(self, *handle_image_upload(self))
            return

        if route == MEDIA_UPLOAD_PATH:
            send_json(self, *handle_media_upload(self))
            return

        try:
            body = read_json_body(self)
        except (ValueError, OSError):
            send_json(self, 400, {"ok": False, "error": "Body khong hop le."})
            return

        answer = dispatch_post(
            self.path.split("?")[0], body, bearer_token(self.headers),
        )

        if answer is None:
            self.send_error(404, "Unknown endpoint")
            return

        send_json(self, *answer)


# Tailscale hands out addresses from the CGNAT block. A machine reached on
# one of these is on a private, authenticated network rather than whatever
# Wi-Fi the shop has -- which is the difference between "the admin API is
# exposed" and "the admin API is exposed to my own devices".
# Both of these used to be written out here, and a second, weaker copy
# lived in store_gui/serve.py -- one that could not see a Tailscale address
# because it lacked the branch that asks the kernel. They share one
# implementation now; see configuration/net_addresses.py for why three
# different ways of asking are all needed.
TAILSCALE_PREFIX = net_addresses.TAILSCALE_PREFIX
tailscale_address = net_addresses.tailscale_address
local_addresses = net_addresses.local_addresses


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a shell-friendly exit code."""
    parser = argparse.ArgumentParser(
        description="Chạy máy chủ cho màn hình quản lý (admin).",
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT,
        help=f"Cổng phục vụ (mặc định {DEFAULT_PORT}).",
    )
    parser.add_argument(
        "--local", action="store_true",
        help="Chỉ cho máy này truy cập (127.0.0.1).",
    )
    parser.add_argument(
        "--tailscale", action="store_true",
        help="Chỉ nghe trên địa chỉ Tailscale, không mở ra mạng LAN.",
    )
    parser.add_argument(
        "--host", default=None, metavar="ĐỊA_CHỈ",
        help="Địa chỉ để nghe (mặc định 0.0.0.0 - mọi mạng).",
    )
    args = parser.parse_args(argv)

    # Most specific wins, because binding wider than asked is the mistake
    # that matters here -- this port rewrites the menu.
    if args.host:
        host = args.host
    elif args.local:
        host = "127.0.0.1"
    elif args.tailscale:
        host = tailscale_address()

        if host is None:
            print("LỖI: không tìm thấy địa chỉ Tailscale trên máy này.",
                  file=sys.stderr)
            return 1
    else:
        # Mặc định LOOPBACK, không phải 0.0.0.0.
        #
        # Server này gắn toàn bộ API quản trị. Bản trước mặc định mọi mạng,
        # nên ai chạy `python3 -m admin_gui.serve` để sửa giao diện là vô
        # tình phơi console ra Wi-Fi. main.py không mở cổng này nên máy bán
        # hàng không bị, nhưng tài liệu bảo người phát triển chạy nó bằng
        # tay -- và mặc định nguy hiểm thì quên là thủng.
        #
        # store_gui/serve.py đã đổi mặc định từ trước; để hai server còn lại
        # ở 0.0.0.0 chính là kiểu lệch mà cả đợt dọn này đang chữa.
        # --host và --tailscale vẫn còn nguyên cho ai thật sự cần.
        host = net_addresses.LOOPBACK_HOST

    handler = partial(AdminHandler, directory=str(PROJECT_DIR))

    try:
        server = ThreadingHTTPServer((host, args.port), handler)
    except OSError as error:
        print(
            f"LỖI: không mở được cổng {args.port}: {error}\n"
            f"Kiểm tra bằng: ss -ltnp | grep {args.port}",
            file=sys.stderr,
        )
        return 1

    # The banner lists only what this bind can actually answer. Printing
    # localhost while listening on one interface, or the LAN address while
    # listening on loopback, sends somebody to a URL that cannot connect --
    # and "the page can not be reached" says nothing about which of the two
    # went wrong.
    print(f"Đang phục vụ {PROJECT_DIR} trên {host}:{args.port}.")
    print("Mở màn hình quản lý tại:")

    if host == "0.0.0.0":
        reachable = [f"localhost", *local_addresses()]
    elif host == "127.0.0.1":
        reachable = ["localhost"]
    else:
        reachable = [host]

    for address in reachable:
        print(f"  http://{address}:{args.port}{ADMIN_PAGE}")

    if host not in ("127.0.0.1", "localhost"):
        print("\n  CẢNH BÁO: cổng này sửa được database và CHƯA có xác thực "
              "phía máy chủ.")

        if host == "0.0.0.0":
            print("  Đang mở ra MỌI mạng. Dùng --tailscale hoặc --local "
                  "để thu hẹp lại.")

    print("\nCtrl+C để dừng.", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng.")
    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
