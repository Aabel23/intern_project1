"""Serve the store screen.

WHAT THIS FILE IS
    The store screen is static files, so anything can serve them -- this
    replaces `python3 -m http.server 8080` with something that has the port
    written down in one place and that does not let browsers cache the
    generated menu.

    It is NOT the bartender screen's server. That one is started by
    order/process_runner.py on its own port, because it also answers
    /api/confirm and /api/process/* -- requests that release the machine's
    gates, which no file server can do. This one only hands out files.

WHY IT SERVES THE PROJECT ROOT
    The page lives in store_gui/ but its drink photos are in recipe/image/,
    reached as ../recipe/image/... Serving store_gui/ alone would put those
    above the root and they would 404.

WHAT IT DOES BESIDES SERVE FILES
    POST /api/ticket    the customer's choices in, one single-use QR
                        payload out. This is where an order becomes a
                        label.
    GET  /api/qr        renders a payload as an SVG QR for the screen.
    POST /api/print     sends a payload to the label printer, because a
                        browser has no way to reach a printer on the Pi.
    POST /api/start     runs the order without a scan, for a dead scanner
                        or a printer out of paper.

    ... and the admin console's endpoints (/api/menu, /api/drink/*,
    /api/recipe*, /api/admin/login), so the whole machine answers on one
    port. Those are NOT open by virtue of being here: each one requires a
    session token issued by admin_gui/auth.py, checked inside the shared
    dispatcher in admin_gui/serve.py. The customer's tablet can reach the
    URL and gets 401.

WHY THE PAYLOAD IS BUILT HERE AND NOT IN THE BROWSER
    The page used to encode the payload itself, which meant two
    implementations of one wire format -- and they had already drifted
    once, on the QR's encoding mode, producing a symbol on screen that did
    not match the one on the label.

    Encryption settles it now, harder than the serial ever did: a payload
    needs the deployment's shared AES-256 key (qrproto), which a browser
    must never hold, so the payload cannot be finished client-side even in
    principle. The page sends what the customer picked and gets digits
    back; qrproto.create() is the only encoder left, and order_ticket
    stores the exact string that was printed, keyed by its own hash (see
    database/order_ticket.py). The browser's copy of the CRC, the field
    widths and the length rule are gone, and with them any way for the
    screen and the machine to disagree about what was ordered.

WHY IT SENDS no-store
    http.server sends no cache headers at all, which leaves browsers free
    to guess how long a file stays fresh. menu-data.js is rewritten every
    time the menu is rebuilt, and drinks-pos.js changes whenever the screen
    does, so a browser holding an old copy shows stock and prices that are
    not true any more -- and the only cure is a hard refresh nobody thinks
    to do. Photos and CSS are left cacheable: they are large and rarely
    change.

RUNNING IT
    python3 -m store_gui.serve              # on DEFAULT_PORT
    python3 -m store_gui.serve --port 9090
    python3 -m store_gui.serve --local      # this machine only

    Ctrl+C stops it.
"""

from __future__ import annotations

import argparse
import fcntl
import io
import json
import os
import sys
import threading
import urllib.error
import urllib.request
import time
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


STORE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = STORE_DIR.parent

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# The admin console's endpoints, mounted on this port too. Imported rather
# than reimplemented so the login check exists once -- see its do_GET below.
from admin_gui import serve as admin_api                          # noqa: E402
from printer import spool                                        # noqa: E402
from store_gui import kiosk_watchdog                             # noqa: E402
from database import order_ticket                                # noqa: E402
from configuration import net_addresses                          # noqa: E402
from configuration import machine                               # noqa: E402
from configuration import served_paths                           # noqa: E402
from configuration.qrproto_config import MACHINE_ID, get_key      # noqa: E402
import qrproto                                                    # noqa: E402
from qrproto import Grams, Instruction, ProtocolError             # noqa: E402
from qrproto import constants as qr_constants                     # noqa: E402

# THE port. Every screen in this system is served from here: the shop
# screen, the bartender screen, the manual test screen. It is up for as long
# as main.py is, which is what makes it safe for a page to be sent to it.
#
# There used to be three. The bartender screen had its own on 8000, opened by
# each order's process_runner and closed again when that order finished -- so
# a browser sent to it a moment too early or a moment too late got "this site
# can't be reached", with no way back. The manual test screen had a third on
# 8090. Both are served from this port now; the runner still listens, but on
# loopback only, and this server relays to it (see RUNNER_API_PATHS).
DEFAULT_PORT = machine.STORE_PORT

# The one address that is always bound. The kiosk, the bartender screen and
# the test screen all reach this server through it -- deploy/kiosk's
# autostart opens http://localhost:8080/... -- so it is what makes the
# machine work with no network at all.
LOOPBACK_HOST = net_addresses.LOOPBACK_HOST

# Escape hatch for a development machine that wants to be reached over the
# LAN. Read here rather than invented at the call site so there is exactly
# one name to grep for. Unset on a shop machine, which is the point.
BIND_ENV = "FLEXMIX_BIND"

# How often to look again for a Tailscale address that was not there yet at
# startup. tailscaled often finishes after this service does -- the unit
# only orders itself After=network.target -- and a machine that came up in
# the wrong order should not need a restart to be administrable.
TAILNET_RETRY_SECONDS = 20

STORE_PAGE = "/store_gui/drinks-pos.html"

# Rewritten by sync_menu.py, or edited while working on the screen. A stale
# copy of any of these shows the customer something untrue.
# Everything the screen is built from. CSS belongs here too: it changes
# whenever the screen does, and a cached copy showed a half-styled page
# that looked like broken markup rather than a stale file.
NEVER_CACHE_SUFFIXES = (".js", ".json", ".html", ".css")

# The one thing this server does besides hand out files. A browser cannot
# reach the label printer on the Pi, so the page posts the payload here and
# this shells out to printer/printer_qr.py.
PRINT_PATH = "/api/print"

# The screen's QR, rendered here rather than in the browser. qrcodejs (the
# CDN library the page used) always encodes in Byte mode, so the same
# payload came out as a version 5 symbol on screen and a version 3 on the
# label -- two visibly different codes for one order. Rendering both from
# the same library removes the possibility.
QR_PATH = "/api/qr"

# Where an order becomes a label. Every payload the machine will ever
# accept is minted here, one per press of the QR button.
TICKET_PATH = "/api/ticket"

# Start the order on this screen without the handheld scanner.
#
# WHY THIS EXISTS
#     The normal path is print a label, scan it at the machine. Two pieces
#     of hardware, either of which can fail: a printer out of paper or a
#     scanner that will not read leaves a machine that works perfectly
#     unable to take an order at all.
#
# HOW IT WORKS
#     It writes the payload into scan/raw_qr.json in the exact shape
#     scan/scanner.py writes -- so from order/run_flow.py's point of view a
#     code was scanned, and nothing downstream needs to know the
#     difference. The ticket is issued and claimed as usual, so the order
#     is still single-use and still recorded.
START_PATH = "/api/start"

# The bartender screen's controls. They act on hardware the runner owns --
# pumps, the panel, the load cell -- and the runner is a separate process on
# purpose, so that a crash mid-pour cannot take this server down with it.
# That means these cannot be handled here; they are relayed to whichever
# runner is currently pouring, over loopback.
#
# The runner's port is read from the handoff file the runner itself writes,
# so there is one source of truth for it rather than a constant in two files.
RUNNER_API_PATHS = (
    "/api/confirm",
    "/api/pause",
    "/api/resume",
    "/api/cancel",
    "/api/process/button",
    "/api/process/detect",
)

# How long to wait on the runner before giving up. /api/process/detect asks
# for a cup check and blocks until the load cell answers, so this is well
# past anything the quicker calls need.
RUNNER_TIMEOUT_SECONDS = 30.0

# The customer screen reads store_gui/menu-data.js, a snapshot of the menu.
# Anything that changes stock changes the database, and the database keeps
# itself right on its own -- the triggers in database.sql recompute
# drink.in_stock whenever an ingredient crosses its threshold, with no
# Python involved. That is the problem: a snapshot rebuilt only by Python
# goes stale the moment somebody edits a level directly in MySQL, and the
# screen keeps selling a drink the machine cannot make.
#
# So the file is rebuilt HERE, on the way out, whenever it is older than
# this. The page already polls it every 30 s for its timestamp, so one
# poll always gets fresh data whatever route the change arrived by.
# Rebuilding costs about 80 ms and only happens while somebody is
# actually looking at the screen.
MENU_DATA_PATH = "/store_gui/menu-data.js"

# Written by run_flow while an order runs, deleted when it ends. It carries
# the runner's loopback port, which is how the relay above finds it.
HANDOFF_FILE = PROJECT_DIR / "order" / "handoff.json"
MENU_MAX_AGE_SECONDS = 20.0

# Files the screens poll on a timer, and the answers that mean nothing
# happened. A 404 here is not a fault: handoff.json exists only while an
# order is running and scan_notice.json only when a scan was refused, so
# "missing" is the normal state for most of the day and the page is
# written to read it that way.
#
# Two open screens polling twice a second put four lines a second into
# the terminal, which is how a real 500 goes unnoticed. These are counted
# instead, and the count is printed occasionally so the quiet is
# visibly deliberate rather than a server that has stopped answering.
QUIET_POLL_PATHS = (
    "/order/handoff.json",
    "/order/scan_notice.json",
    "/order/current_recipe.json",
    MENU_DATA_PATH,
)
QUIET_POLL_STATUSES = ("200", "304", "404")
QUIET_SUMMARY_SECONDS = 300.0

# Written here, read by order/run_flow.py.
RAW_QR_FILE = PROJECT_DIR / "scan" / "raw_qr.json"
FLOW_LOCK_FILE = PROJECT_DIR / "order" / ".run_flow.lock"

# A payload is digits and nothing else, at one of the lengths qrproto's
# size table actually produces (protocol v1.4, section 2.3) -- 109, 118,
# 128, ... 224, not a contiguous range like v1.3's, so a MIN-MAX regex
# would wrongly accept an in-between length that no encoder ever
# produces. Checked before it becomes a command argument or a database
# key: the value arrives from the network, and refusing anything
# unexpected is cheaper than reasoning about what a stray character
# might do downstream.
def valid_payload_shape(payload: str) -> bool:
    return (
        qr_constants.is_digits_only(payload)
        and len(payload) in qr_constants.OUTER_LEN_TO_ENTRY
    )


PAYLOAD_SHAPE = "Payload không đúng định dạng QR Payload Protocol v1.4."


def build_instruction(entry: dict) -> Instruction:
    """Turn one {ingredient, type, data} object from the page into a pair.

    The page sends the encoded data field -- 0/1 or whole grams -- rather
    than a value plus a unit, because that is what the protocol's four
    digits mean and translating twice is one more place to lose a factor
    of ten. What it does NOT send is the type subfield's meaning: that is
    decided here by wrapping the number in Grams, which is what makes
    qrproto emit the right type code. There is no percentage type any
    more -- see qrproto/constants.py for why.
    """
    ingredient = int(entry["ingredient"])
    type_code = str(entry["type"])
    data = int(entry["data"])

    if type_code == qr_constants.TYPE_WEIGHT:
        return Instruction(ingredient=ingredient, value=Grams(data))

    if type_code == qr_constants.TYPE_BOOLEAN:
        if data not in (0, 1):
            raise ProtocolError(f"boolean data {data} must be 0 or 1")
        return Instruction(ingredient=ingredient, value=bool(data))

    raise ProtocolError(f"unknown type {type_code}")


def flow_running() -> bool:
    """Is order/run_flow.py up? It is what reads raw_qr.json."""
    try:
        handle = open(FLOW_LOCK_FILE, "a")
    except OSError:
        return False

    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(handle, fcntl.LOCK_UN)
        return False        # nobody held it, so nothing is running
    except OSError:
        return True
    finally:
        handle.close()


def write_raw_qr(payload: str) -> None:
    """Write one payload where the scanner would have put it.

    The same shape and the same atomic replace scan/scanner.py uses: the
    flow polls this file and must never read it half-written. Deliberately
    identical rather than a second "injected order" channel -- one path
    into the machine means one path to get wrong.
    """
    RAW_QR_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = RAW_QR_FILE.with_name(f".{RAW_QR_FILE.name}.tmp")

    document = {
        "qr_code": payload,
        "timestamp": datetime.now().astimezone().isoformat(
            timespec="milliseconds"),
        # So a scan that never touched the scanner is identifiable later.
        "source": "store_screen",
    }

    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())

    os.replace(temporary, RAW_QR_FILE)


def render_qr_svg(payload: str) -> bytes:
    """Render one payload as an SVG QR, matching the printed label exactly.

    SVG rather than PNG because this runs in the project venv, which has
    qrcode but not Pillow -- and a vector symbol is sharper on a screen at
    any size anyway. The module grid is what matters, and it is produced by
    the same library, mode and error-correction level that
    printer/printer_qr.py uses, so screen and label agree module for
    module.
    """
    import qrcode
    from qrcode.constants import ERROR_CORRECT_H
    from qrcode.image.svg import SvgPathImage

    code = qrcode.QRCode(
        error_correction=ERROR_CORRECT_H,
        border=4,
        image_factory=SvgPathImage,
    )
    code.add_data(payload)
    code.make(fit=True)

    buffer = io.BytesIO()
    code.make_image().save(buffer)
    return buffer.getvalue()


class StoreHandler(SimpleHTTPRequestHandler):
    """Serve the project directory, refusing to let the page go stale."""

    def translate_path(self, path: str) -> str:
        """Refuse anything outside the served directories -- 404, not 403.

        The whole project directory is this server's document root, so
        without this a browser can ask for .env or configuration/ and get
        them. See configuration/served_paths.py.
        """
        return served_paths.guard(super().translate_path(path))

    def end_headers(self) -> None:
        """Add cache headers before the response is closed off."""
        if self.path.split("?")[0].endswith(NEVER_CACHE_SUFFIXES):
            self.send_header("Cache-Control", "no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")

        super().end_headers()

    def refresh_menu_if_stale(self) -> None:
        """Rebuild the menu snapshot if it has aged out.

        Never raises. A menu that could not be rebuilt is a menu that is a
        little out of date; a store screen that will not load at all is a
        shop that cannot sell anything.
        """
        try:
            menu_file = PROJECT_DIR / "store_gui" / "menu-data.js"
            age = (time.time() - menu_file.stat().st_mtime
                   if menu_file.exists() else float("inf"))

            if age < MENU_MAX_AGE_SECONDS:
                return

            # publish_menu() rewrites the file ONLY if the menu really
            # changed. Rewriting it every time would move generatedAt,
            # and the page treats a moved stamp as a changed menu -- so
            # the customer's screen would reload itself every 20 seconds,
            # for ever, showing the same drinks each time.
            from store_gui.sync_menu import publish_menu
            publish_menu()
        except Exception as error:      # noqa: BLE001 - never block a page
            sys.stderr.write(f"[menu] could not rebuild snapshot: {error}\n")
            sys.stderr.flush()

    def do_GET(self) -> None:
        # Every request is a heartbeat from a live page. Both screens poll
        # this server without needing a customer -- the store page every
        # second, the bartender screen every 120ms -- so silence here is
        # how kiosk_watchdog knows a tab has died.
        kiosk_watchdog.note_request()

        # The manual test screen is served from this port too, so its one
        # GET endpoint is answered here. Imported lazily: test_gui.hardware
        # opens the panel and the load cell, and a shop screen with no
        # machine attached must still start.
        if self.path.split("?")[0] in test_api_get_paths():
            from test_gui.serve import handle_get

            answer = handle_get(self.path.split("?")[0])

            if answer is not None:
                self._send_json(*answer)
                return

        """Serve the QR endpoint, the admin API, or a file."""
        if self.path.split("?")[0] == MENU_DATA_PATH:
            self.refresh_menu_if_stale()

        # The admin console is served from this port too, so its endpoints
        # are answered here. They are NOT open because they are here: every
        # one of them goes through require_login() inside the dispatcher,
        # which is why there is one dispatcher and not a copy of it. See
        # admin_gui/serve.py.
        answer = admin_api.dispatch_get(
            self.path.split("?")[0],
            urlparse(self.path).query,
            admin_api.bearer_token(self.headers),
        )

        if answer is not None:
            admin_api.send_json(self, *answer)
            return

        if self.path.split("?")[0] != QR_PATH:
            super().do_GET()
            return

        query = parse_qs(urlparse(self.path).query)
        payload = (query.get("payload") or [""])[0].strip()

        if not valid_payload_shape(payload):
            self._send_json(400, {"ok": False, "error": PAYLOAD_SHAPE})
            return

        try:
            body = render_qr_svg(payload)
        except Exception as error:      # noqa: BLE001 - reported to the page
            self._send_json(500, {"ok": False, "error": str(error)})
            return

        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _relay_to_runner(self, path: str, raw_body: bytes) -> None:
        """Hand one bartender-screen control to the running order.

        The browser only ever knows this port. Whether a runner is up, and
        on which port, is this server's problem -- not something a page
        should have to discover, and certainly not something it should be
        redirected to and left stranded on when the answer is "none".
        """
        port = current_runner_port()

        if port is None:
            # Not an error in the page: an order simply is not running. Said
            # plainly so the screen can show it rather than a bare failure.
            self._send_json(503, {
                "ok": False,
                "error": "Khong co don nao dang chay.",
            })
            return

        target = f"http://127.0.0.1:{port}{path}"
        request = urllib.request.Request(
            target,
            data=raw_body or b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request, timeout=RUNNER_TIMEOUT_SECONDS,
            ) as answer:
                payload = answer.read()
                status = answer.status
        except urllib.error.HTTPError as error:
            # The runner answered, and refused. Its own words are more use
            # to the screen than anything invented here.
            payload = error.read() or b'{"ok": false}'
            status = error.code
        except (urllib.error.URLError, OSError, TimeoutError) as error:
            # It was there when the port was read and is gone now: the order
            # finished, or the runner died mid-pour.
            self._send_json(502, {
                "ok": False,
                "error": f"Khong lien lac duoc voi tien trinh pha: {error}",
            })
            return

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:
        """Route the POST endpoints. Everything else is not found."""
        kiosk_watchdog.note_request()      # see do_GET
        path = self.path.split("?")[0]

        # Relayed before the body is parsed as JSON: these are the runner's
        # endpoints and its own reading of the body is the one that counts.
        if path in RUNNER_API_PATHS:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length > 0 else b""
            except (ValueError, OSError):
                raw = b""
            self._relay_to_runner(path, raw)
            return

        # Test-screen endpoints, handled in this process: test_gui/serve.py
        # runs in the same main.py as this server, so its hardware helpers
        # are a function call away rather than another port.
        if path in test_api_post_paths():
            from test_gui.serve import handle_post

            try:
                length = int(self.headers.get("Content-Length", "0"))
                sent = json.loads(self.rfile.read(length) or b"{}")
            except (ValueError, OSError):
                self._send_json(400, {"ok": False, "error": "Body khong hop le."})
                return

            answer = handle_post(path, sent if isinstance(sent, dict) else {})

            if answer is not None:
                self._send_json(*answer)
                return

            self.send_error(404, "Unknown endpoint")
            return

        # An upload carries the file as its body, so it is answered before
        # the JSON read below -- see admin_gui/serve.py. BOTH kinds have to
        # be listed: a path that misses this branch reaches json.loads()
        # with a GIF in its hands and the browser is told 400 Bad Request,
        # which says nothing about what actually went wrong.
        if path == admin_api.IMAGE_UPLOAD_PATH:
            admin_api.send_json(self, *admin_api.handle_image_upload(self))
            return

        if path == admin_api.MEDIA_UPLOAD_PATH:
            admin_api.send_json(self, *admin_api.handle_media_upload(self))
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, OSError):
            self._send_json(400, {"ok": False, "error": "Body khong hop le."})
            return

        # Admin endpoints first, and behind a session -- see do_GET.
        answer = admin_api.dispatch_post(
            path,
            body if isinstance(body, dict) else {},
            admin_api.bearer_token(self.headers),
        )

        if answer is not None:
            admin_api.send_json(self, *answer)
            return

        if path not in (PRINT_PATH, TICKET_PATH, START_PATH):
            self.send_error(404, "Unknown endpoint")
            return

        if path == TICKET_PATH:
            self._issue_ticket(body or {})
            return

        if path == START_PATH:
            self._start_order(body or {})
            return

        self._print_label(body or {})

    def _issue_ticket(self, body: dict) -> None:
        """Turn the order the page describes into a payload.

        With "preview": true this only ENCRYPTS -- order_ticket.issue()
        is never called, so nothing is written. That is what the QR modal
        asks for while it is merely showing the customer what they
        ordered. Opening and closing that modal used to burn a serial
        every time and leave an unused ticket behind for a drink nobody
        bought; a preview payload now simply never becomes a row, so
        there is nothing to leave behind. If it is ever scanned anyway,
        order_ticket.claim() refuses it as an unknown payload -- the same
        outcome the old SERIAL_NONE sentinel produced by name, reached
        here for free because a preview payload's hash was never issued.

        Without "preview", qrproto.create() builds the payload first --
        it needs nothing from the database, unlike the old serial-based
        protocol -- and order_ticket.issue() records it, keyed by its own
        hash. If encoding raises -- a duplicate ingredient, a value out
        of range -- issue() is never reached and nothing is written.
        """
        try:
            drink_id = int(body.get("drink_id"))
            entries = list(body.get("pairs") or [])
            instructions = [build_instruction(e) for e in entries]
            preview = bool(body.get("preview"))
            # Free text, so it is bounded here rather than trusted. The
            # column is 200 and this arrives from the network.
            note = str(body.get("note") or "").strip()[:200]
        except ProtocolError as error:
            self._send_json(400, {"ok": False, "error": str(error)})
            return
        except (TypeError, ValueError, KeyError) as error:
            self._send_json(400, {
                "ok": False,
                "error": f"Don hang khong hop le: {error}",
            })
            return

        try:
            payload = qrproto.create(
                sku=drink_id,
                instructions=instructions,
                machine_id=MACHINE_ID,
                key=get_key(),
            )
        except ProtocolError as error:
            self._send_json(400, {"ok": False, "error": str(error)})
            return
        except (KeyError, ValueError) as error:
            # get_key() raises these when QRPROTO_KEY is unset or is not
            # valid hex -- a deployment fault, not something the customer
            # typed wrong.
            sys.stderr.write(f"[ticket] QR key not configured: {error}\n")
            sys.stderr.flush()
            self._send_json(500, {
                "ok": False,
                "error": "May chua cau hinh khoa QR (QRPROTO_KEY).",
            })
            return

        if preview:
            self._send_json(200, {
                "ok": True,
                "preview": True,
                "payload": payload,
            })
            return

        try:
            issued = order_ticket.issue(drink_id, payload, note=note)
        except Exception as error:      # noqa: BLE001 - reported to the page
            sys.stderr.write(f"[ticket] issue failed: {error}\n")
            sys.stderr.flush()
            self._send_json(500, {
                "ok": False,
                "error": f"Khong tao duoc ma QR: {error}",
            })
            return

        # Recorded because a label in a customer's hand has to be traceable
        # to the moment it was issued, not just to the row it left behind.
        sys.stderr.write(
            f"[ticket] serial {issued['serial']:06d} drink {drink_id} "
            f"-> {issued['payload']}\n"
        )
        sys.stderr.flush()

        self._send_json(200, {"ok": True, **issued})

    def _start_order(self, body: dict) -> None:
        """Hand a payload to the machine as though it had been scanned."""
        payload = str(body.get("payload", "")).strip()

        if not valid_payload_shape(payload):
            self._send_json(400, {"ok": False, "error": PAYLOAD_SHAPE})
            return

        if not flow_running():
            # Without run_flow nothing reads raw_qr.json, so the button
            # would silently do nothing. Say so rather than leave staff
            # pressing it again.
            self._send_json(409, {
                "ok": False,
                "error": "Máy chưa chạy (order/run_flow.py). "
                         "Khởi động máy rồi thử lại.",
            })
            return

        if test_mode_open():
            # run_flow refuses orders while the machine is in test mode, and
            # it refuses them AFTER reading the file -- so writing the
            # payload here would have the screen report success for an order
            # that is then dropped with nothing shown to the person who
            # pressed the button. Refused up front instead, in words that
            # say which switch to undo.
            self._send_json(409, {
                "ok": False,
                "error": "Máy đang ở chế độ test (nút bảng 15). "
                         "Tắt chế độ test rồi thử lại.",
            })
            return

        try:
            write_raw_qr(payload)
        except OSError as error:
            self._send_json(500, {
                "ok": False,
                "error": f"Không ghi được lệnh cho máy: {error}",
            })
            return

        sys.stderr.write(f"[start] payload {payload} -> {RAW_QR_FILE.name}\n")
        sys.stderr.flush()
        self._send_json(200, {"ok": True})

    def _print_label(self, body: dict) -> None:
        """Send one already-issued payload to the label printer.

        The subprocess handling lives in printer/spool.py, shared with the
        console's reprint endpoint -- see the note there on why it is not
        copied into both.
        """
        payload = str(body.get("payload", "")).strip()

        if not valid_payload_shape(payload):
            self._send_json(400, {"ok": False, "error": PAYLOAD_SHAPE})
            return

        try:
            printed, output = spool.send_payload(payload)
        except spool.PrinterUnavailable as error:
            self._send_json(500, {"ok": False, "error": str(error)})
            return
        except spool.PrinterTimeout as error:
            self._send_json(504, {"ok": False, "error": str(error)})
            return

        self._send_json(200 if printed else 500, {
            "ok": printed,
            "error": "" if printed else output,
            "message": output,
        })

    def _send_json(self, status: int, payload: dict) -> None:
        """Answer one request with a JSON body."""
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    # Shared by every request thread, so the count is guarded.
    _quiet_lock = threading.Lock()
    _quiet_count = 0
    _quiet_since = time.time()

    def log_message(self, fmt: str, *args: object) -> None:
        """Print what happened, and stay quiet about what did not.

        Always printed:
            anything that failed, ANYWHERE except a polled file, and both
            endpoints that change something. A print that silently never
            arrives is indistinguishable from one that arrived and
            failed, and an issued ticket is money.

        Never printed:
            a polled file answering normally -- including its 404. That
            404 was the bug in the previous version of this filter: it
            logged every 4xx, and "missing" is exactly what handoff.json
            says while the machine is idle, so an idle machine produced
            four lines a second for ever.
        """
        status = str(args[1]) if len(args) > 1 else ""
        request = str(args[0]) if args else ""

        polled = any(path in request for path in QUIET_POLL_PATHS)

        if polled and status in QUIET_POLL_STATUSES:
            self._note_quiet_request()
            return

        if status.startswith(("4", "5")) or PRINT_PATH in request \
                or TICKET_PATH in request:
            self._flush_quiet_summary()
            super().log_message(fmt, *args)

    def _note_quiet_request(self) -> None:
        """Count a suppressed poll, and report the total now and then."""
        with StoreHandler._quiet_lock:
            StoreHandler._quiet_count += 1

        self._flush_quiet_summary()

    def _flush_quiet_summary(self) -> None:
        """Report suppressed polls, but only once the interval is up.

        Deliberately NOT printed alongside every real log line. A burst of
        genuine requests would then be interleaved with a summary after
        each one, which is the noise this was meant to remove.
        """
        now = time.time()

        with StoreHandler._quiet_lock:
            count = StoreHandler._quiet_count
            since = StoreHandler._quiet_since

            if not count or now - since < QUIET_SUMMARY_SECONDS:
                return

            StoreHandler._quiet_count = 0
            StoreHandler._quiet_since = now

        elapsed = now - since
        span = (f"{elapsed / 60:.0f} min" if elapsed >= 90
                else f"{elapsed:.0f} s")
        sys.stderr.write(
            f"[poll] {count} routine screen requests in the last {span} "
            f"(handoff / notice / menu) — not shown\n")
        sys.stderr.flush()


# Both live in configuration/net_addresses.py now. This copy could not see
# a Tailscale address -- it lacked the one branch that asks the kernel --
# and bind_hosts() below decides what to listen on from these answers, so
# the blind copy would have silently dropped remote administration.
local_addresses = net_addresses.local_addresses
tailscale_address = net_addresses.tailscale_address


# Cùng lý do: ba server dùng chung hàm này. Xem net_addresses.bind_hosts()
# để biết vì sao LAN không bao giờ nằm trong danh sách.
bind_hosts = net_addresses.bind_hosts


def test_api_get_paths() -> tuple[str, ...]:
    """The test screen's GET endpoints, or none if that screen is absent."""
    try:
        from test_gui.serve import TEST_GET_PATHS
    except Exception:
        return ()

    return TEST_GET_PATHS


def test_api_post_paths() -> tuple[str, ...]:
    """The test screen's POST endpoints, or none if that screen is absent."""
    try:
        from test_gui.serve import TEST_POST_PATHS
    except Exception:
        return ()

    return TEST_POST_PATHS


def test_mode_open() -> bool:
    """True while the machine is held in manual test mode.

    Panel button 15 toggles it, and run_flow pauses order intake for as long
    as it is on. Read from the same file button_watch writes, so there is no
    second idea of what "test mode" means.
    """
    try:
        from panel_control.button_watch import read_mode
    except Exception:
        return False

    return bool(read_mode().get("open"))


def current_runner_port() -> int | None:
    """The loopback port of the order being poured, or None if none is.

    Read from order/handoff.json every time rather than cached: the runner
    is a separate process with its own lifetime, and a port remembered from
    the last order is a port that answers for the wrong drink -- or, more
    often, does not answer at all.

    The file is written atomically by run_flow.write_handoff(), so a partial
    read is not possible; a missing file simply means nothing is running.
    """
    try:
        with open(HANDOFF_FILE, "r", encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, ValueError):
        return None

    port = document.get("gui_port")

    return port if isinstance(port, int) else None


def open_server(host: str, port: int, handler) -> ThreadingHTTPServer | None:
    """Bind one address, or return None and say why.

    None rather than an exception: binding the tailnet address is allowed
    to fail -- tailscaled may be on its way up, or gone -- and that must
    not stop the shop screen coming up on loopback.
    """
    try:
        server = ThreadingHTTPServer((host, port), handler)
    except OSError as error:
        print(f"[bind] khong mo duoc {host}:{port}: {error}",
              file=sys.stderr, flush=True)
        return None

    threading.Thread(
        target=server.serve_forever,
        name=f"http-{host}",
        daemon=True,
    ).start()

    return server


def watch_for_tailnet(port: int, handler, servers: list,
                      lock: threading.Lock) -> None:
    """Bind the Tailscale address once it appears, then stop looking.

    systemd orders this service After=network.target, which says nothing
    about tailscaled. Coming up first is normal, and the cost of not
    handling it would be a machine that is unreachable over the tailnet
    until somebody restarts the service -- exactly when they cannot,
    because reaching it is what they were trying to do.

    Polling stops the moment it succeeds, so the steady state is one
    thread asleep for ever, not a subprocess every twenty seconds.
    """
    while True:
        time.sleep(TAILNET_RETRY_SECONDS)
        address = tailscale_address()

        if address is None:
            continue

        with lock:
            if any(s.server_address[0] == address for s in servers):
                return

            server = open_server(address, port, handler)

            if server is None:
                continue

            servers.append(server)

        print(f"[bind] tailnet len sau khi khoi dong, da mo "
              f"http://{address}:{port}{STORE_PAGE}", flush=True)
        return


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a shell-friendly exit code."""
    parser = argparse.ArgumentParser(
        description="Chạy máy chủ cho màn hình bán hàng.",
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT,
        help=f"Cổng phục vụ (mặc định {DEFAULT_PORT}).",
    )
    parser.add_argument(
        "--local", action="store_true",
        help="Chỉ máy này, kể cả khi có Tailscale.",
    )
    parser.add_argument(
        "--host", default=None, metavar="ĐỊA_CHỈ",
        help="Nghe trên đúng địa chỉ này (0.0.0.0 = mọi mạng, kể cả Wi-Fi "
             "quán). Chỉ dùng khi phát triển.",
    )
    args = parser.parse_args(argv)

    # The flag wins over the variable: somebody typing --host meant it more
    # recently than whoever set the environment.
    explicit = args.host or os.getenv(BIND_ENV, "").strip() or None

    if explicit == "all":
        explicit = "0.0.0.0"

    hosts = bind_hosts(explicit=explicit, loopback_only=args.local)
    handler = partial(StoreHandler, directory=str(PROJECT_DIR))

    servers: list[ThreadingHTTPServer] = []
    lock = threading.Lock()

    for host in hosts:
        server = open_server(host, args.port, handler)

        if server is not None:
            servers.append(server)
        elif host == LOOPBACK_HOST:
            # Loopback is the one that must work: without it the kiosk on
            # this very machine cannot load, so there is nothing to serve.
            print(
                f"LỖI: không mở được cổng {args.port} trên {host}.\n"
                f"Có thể một máy chủ khác đang dùng cổng này. "
                f"Kiểm tra bằng: ss -ltnp | grep {args.port}",
                file=sys.stderr,
            )
            return 1

    # Started here rather than at import: this module is also imported by
    # admin_gui/serve.py and by the test suite, and neither of those is a
    # kiosk that wants its browser restarted.
    kiosk_watchdog.start()

    if explicit is None and not args.local and tailscale_address() is None:
        threading.Thread(
            target=watch_for_tailnet,
            args=(args.port, handler, servers, lock),
            name="tailnet-watch",
            daemon=True,
        ).start()

    print(f"Đang phục vụ {PROJECT_DIR} trên cổng {args.port}.")
    print("Đang nghe trên: " + ", ".join(s.server_address[0]
                                         for s in servers))
    print("Mở màn hình bán hàng tại:")
    print(f"  http://localhost:{args.port}{STORE_PAGE}")

    for server in servers:
        address = server.server_address[0]

        if not address.startswith("127."):
            print(f"  http://{address}:{args.port}{STORE_PAGE}")

    if explicit:
        print(f"\nCẢNH BÁO: đang nghe trên {explicit} theo yêu cầu. "
              f"0.0.0.0 mở cả Wi-Fi quán ra ngoài.")

    print("\nCtrl+C để dừng.", flush=True)

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\nĐã dừng.")
    finally:
        with lock:
            for server in servers:
                server.shutdown()
                server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
