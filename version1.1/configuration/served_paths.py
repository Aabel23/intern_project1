"""Which parts of the project are web content, and which are not.

WHY THIS EXISTS
    Every one of this project's four HTTP servers hands the PROJECT
    DIRECTORY to SimpleHTTPRequestHandler:

        store_gui/serve.py      StoreHandler
        admin_gui/serve.py      AdminHandler
        test_gui/serve.py       TestHandler
        order/process_runner.py GuiHandler

    That class blocks `..` and nothing else. It has no notion of a private
    file, and it does not skip dotfiles -- so with the repository root as
    its document root, `GET /.env` returns the MySQL password and
    `GET /configuration/admin_account.json` returns the key every session
    token is signed with. Both were confirmed answering 200 on the live
    machine before this file existed.

    Nothing served a page ever needed them. They were reachable only
    because they happen to sit in the same parent folder as the HTML.

AN ALLOWLIST, NOT A DENYLIST
    The tempting version is a list of what to block -- `.env`,
    `configuration/`, `database/`. That version breaks the second time
    somebody adds a secret: a new file nobody remembered to list is
    published, and nothing anywhere reports it. The failure is silent, and
    a silent failure in this direction is the expensive kind.

    An allowlist fails the other way. Forget to list a directory and its
    images stop loading -- visible immediately, ten seconds to fix. Loud
    and cheap beats silent and expensive.

WHAT IS ON THE LIST
    Derived from what the pages actually request (`src=`/`href=` across the
    four GUIs, plus the resource paths built in their JavaScript), not from
    what looked plausible:

        store_gui/       the shop screen
        admin_gui/       the console
        bartender_gui/   the preparation screen, incl. images/guide/
        test_gui/        the manual hardware screen
        recipe/          drink photos, and the clips an `action` step loops

    Everything else in the root -- configuration/, database/, order/,
    scan/, qrproto/, printer/, loadcell/, pump_control/, panel_control/,
    docs/, deploy/, and .env -- is machine code and machine secrets. No
    page has ever asked for any of it.

HOW A BLOCKED PATH IS REFUSED
    translate_path() returns a path that cannot exist, so the handler's own
    send_head() fails to open it and answers 404 -- the same answer as a
    genuine typo. It is deliberately not 403: "this is here but you may not
    have it" tells a stranger the file is worth coming back for.

SYMLINKS ARE RESOLVED FIRST
    posixpath.normpath, which SimpleHTTPRequestHandler uses, collapses
    `..` textually and does not follow links. A symlink inside an allowed
    directory pointing at ../.env would survive that and be served. The
    check below resolves the real path before judging it, so it does not.
"""

from __future__ import annotations

from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent

# The only top-level directories that are web content. See the note above
# before adding one -- everything added here becomes downloadable by
# anyone who can reach the port.
SERVE_DIRS = frozenset({
    "store_gui",
    "admin_gui",
    "bartender_gui",
    "test_gui",
    "recipe",
})

# Individual files outside SERVE_DIRS that a screen genuinely polls.
#
# These three are how the machine talks to the browser, and they are the
# reason this list exists at all rather than just SERVE_DIRS:
#
#   handoff.json         store_gui/drinks-pos.js:2048 -- exists for exactly
#                        as long as an order does, and is what moves the
#                        customer screen to the bartender screen
#   scan_notice.json     store_gui/drinks-pos.js:2229 -- the popup shown
#                        when a scan is refused, and the "restarting" warning
#                        panel button 14 puts up before it pulls the service
#   current_recipe.json  bartender_gui/js/guide.js:58 -- the drink being
#                        poured, step by step, which is the whole bartender
#                        screen
#
# The rest of order/ is NOT served: run_flow.py, process_runner.py,
# qr_to_recipe.py, flow.log and .run_flow.lock have no business being
# downloadable, which is why this is a file list and not another entry in
# SERVE_DIRS.
#
# WHY THIS ALMOST SHIPPED BROKEN
#     The first version of this file listed only SERVE_DIRS, and the check
#     that was supposed to catch it -- load every page, compare every
#     resource against the old server -- passed. It read src=/href= out of
#     the HTML and never saw these three, because nothing links them: they
#     are fetched by JavaScript, from constants. Worse, the miss was
#     invisible in the log too: store_gui/serve.py counts 404 among
#     QUIET_POLL_STATUSES, since a missing handoff.json is the normal state
#     of an idle machine, so a blocked file and an idle machine looked
#     exactly alike.
#
#     Anything added here later needs checking the same way this was found:
#     grep the front-end for '../' URL constants, not just the markup.
SERVE_FILES = frozenset({
    "order/handoff.json",
    "order/scan_notice.json",
    "order/current_recipe.json",
})

# Returned in place of anything refused. Inside the project directory so no
# handler's own bounds check trips on it, and named so that it shows up for
# what it is if it ever appears in a log.
BLOCKED_PATH = str(PROJECT_DIR / ".blocked-by-allowlist")


def is_served(path: str | Path) -> bool:
    """May this filesystem path be sent to a browser?

    False for the project root itself: a bare GET / would otherwise return
    a directory listing of the whole repository, which is the same leak by
    a different route.
    """
    try:
        resolved = Path(path).resolve()
    except OSError:
        return False

    try:
        relative = resolved.relative_to(PROJECT_DIR)
    except ValueError:
        # Outside the project entirely -- a symlink pointing away, or a
        # traversal that got past the handler's own normalisation.
        return False

    if not relative.parts:
        return False

    if relative.parts[0] in SERVE_DIRS:
        return True

    return relative.as_posix() in SERVE_FILES


def guard(path: str) -> str:
    """A handler's translate_path() result, or an unopenable path.

    Written to be the whole body of an override:

        def translate_path(self, path):
            return served_paths.guard(super().translate_path(path))
    """
    return path if is_served(path) else BLOCKED_PATH
