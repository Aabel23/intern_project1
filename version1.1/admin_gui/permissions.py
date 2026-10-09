"""What each role may reach: the areas, the defaults, and the overrides.

WHY THIS IS ONE MODULE
    Permission rules were three tables sitting in the middle of a 3600
    line server. They are now editable from a screen, which means they
    also need loading, caching, validating and a way back when somebody
    saves something they should not have. That is a job, not a constant,
    and it belongs somewhere it can be read in one sitting.

THE SHAPE OF THE RULE
    Every endpoint belongs to exactly one AREA. Every role holds a set of
    areas. Two small tables rather than a check written into each handler,
    because a permission written thirty times will be thirty different
    things by next year -- and the one that gets forgotten is not a bug
    you see, it is a door left open.

DEFAULTS IN CODE, OVERRIDES IN THE DATABASE
    DEFAULT_ROLE_AREAS below is what the shop gets with an empty
    role_permission table: reviewable, versioned, and restored by a git
    revert. The table only holds what somebody has deliberately changed,
    and an ABSENT row is not an empty one -- no row means "nobody has
    touched this", an empty `areas` means "somebody took it all away".
    Collapsing those two would make a half-restored backup silently hand
    out the defaults.

TWO RULES THE SCREEN CANNOT BREAK
    shell   granted to every role, always, and never stored. It is what
            lets a signed-in page paint itself; a role without it could
            not render the screen telling it what it may not do.

    users   the owner role always keeps it. Everything else on this
            screen is allowed to be a mistake, because every other
            mistake can be undone from this screen. Taking account
            management away from the last role that has it cannot be --
            the way back would be the command line, which is exactly the
            thing the screen exists to avoid needing.

    Both are enforced HERE, on the way in and on the way out, so a
    crafted request is refused by the same code that refuses a misclick.
"""

from __future__ import annotations

import threading
import time

# --------------------------------------------------------------------------
# the areas
# --------------------------------------------------------------------------

AREA_SHELL = "shell"          # what every signed-in page needs to paint
AREA_USERS = "users"          # accounts and permissions
AREA_CATALOGUE = "catalogue"  # the menu, recipes, images, the bin
AREA_STOCK = "stock"          # creating and deleting ingredients
AREA_REFILL = "refill"        # topping the machine up
AREA_REPORT = "report"        # takings
AREA_TICKETS = "tickets"      # QR tickets: status, reprint
AREA_ERRORS = "errors"        # the fault log

# Deleting from the fault log, which is NOT the same power as reading it.
#
# error_log is the machine's account of what happened to it, and the
# question it exists to answer -- "did this go wrong before?" -- stops
# being answerable the first time an inconvenient entry is removed. So
# the delete lives in its own area rather than riding along with
# AREA_ERRORS: every role can read the log, only an owner can prune it,
# and a shop that wants it otherwise ticks a box rather than editing
# this file.
AREA_ERRORS_PURGE = "errors_purge"

# Ordered for the screen, most powerful first. AREA_SHELL is deliberately
# absent: it is not something anybody chooses. errors_purge sits beside
# the area it modifies rather than at its "power" rank, because the two
# are read together: one row grants the page, the next grants the broom.
AREAS = (AREA_USERS, AREA_CATALOGUE, AREA_STOCK,
         AREA_REFILL, AREA_REPORT, AREA_TICKETS,
         AREA_ERRORS, AREA_ERRORS_PURGE)

AREA_LABEL = {
    AREA_USERS: "Người dùng & phân quyền",
    AREA_CATALOGUE: "Menu · Trang chủ · Thùng rác",
    AREA_STOCK: "Nguyên liệu (thêm / xoá)",
    AREA_REFILL: "Nạp kho",
    AREA_REPORT: "Báo cáo doanh thu",
    AREA_TICKETS: "Vé QR (đổi trạng thái, in lại)",
    AREA_ERRORS: "Nhật ký lỗi (xem)",
    AREA_ERRORS_PURGE: "Nhật ký lỗi — XOÁ vĩnh viễn",
}

# Which admin pages each area unlocks. Sent to the browser so the sidebar
# is drawn from the server's answer instead of a second copy of these
# rules living in JavaScript -- two copies is how a page stays in the rail
# for a year after the endpoint behind it stopped allowing it.
AREA_PAGES = {
    AREA_USERS: ("users",),
    AREA_CATALOGUE: ("menu", "home", "bin"),
    AREA_STOCK: ("ingredients",),
    AREA_REFILL: ("refill", "mode", "display"),
    AREA_REPORT: ("report",),
    AREA_TICKETS: ("tickets",),
    AREA_ERRORS: ("errors",),
    # Unlocks no page of its own -- it adds a button to the errors page,
    # which AREA_ERRORS is what opens. Listed anyway so the permission
    # screen can say so instead of leaving a blank cell.
    AREA_ERRORS_PURGE: (),
}

# What a fresh install gets, and what --reset-permissions goes back to.
DEFAULT_ROLE_AREAS = {
    "owner": {AREA_USERS, AREA_CATALOGUE, AREA_STOCK,
              AREA_REFILL, AREA_REPORT, AREA_TICKETS, AREA_ERRORS,
              AREA_ERRORS_PURGE},
    "manager": {AREA_CATALOGUE, AREA_STOCK,
                AREA_REFILL, AREA_REPORT, AREA_TICKETS, AREA_ERRORS},
    "staff": {AREA_REFILL, AREA_REPORT, AREA_TICKETS, AREA_ERRORS},
}


class PermissionError_(Exception):
    """A permission change that must not be saved."""


# MySQL: bảng không tồn tại. Lý do CHÍNH ĐÁNG duy nhất để bỏ qua việc đọc
# role_permission -- xem _read_overrides().
ER_NO_SUCH_TABLE = 1146


class PermissionReadError(Exception):
    """Không đọc được role_permission, và đoán bừa thì không an toàn."""


# --------------------------------------------------------------------------
# the cache
#
# require_permission() runs on EVERY admin request, and the admin screens
# poll. Reading a table each time would put a query in front of every
# click for a row that changes a few times a year.
#
# Short TTL *and* explicit invalidation, not either alone: the write path
# clears it so a save is visible immediately in this process, and the TTL
# covers the case the write path cannot -- another process, or somebody
# editing the row in MySQL directly.
# --------------------------------------------------------------------------

CACHE_SECONDS = 10.0

_lock = threading.Lock()
_cache: dict[str, set[str]] | None = None
_cached_at = 0.0


def invalidate() -> None:
    global _cache, _cached_at
    with _lock:
        _cache = None
        _cached_at = 0.0


def _read_overrides() -> dict[str, set[str]]:
    """Rows from role_permission, or {} if the table is not there yet.

    MỘT LÝ DO ĐỂ TRẢ VỀ RỖNG, KHÔNG PHẢI MỌI LÝ DO
        Bảng chưa tồn tại là chuyện bình thường: một bản cài chưa chạy
        database/migrate_role_permission.sql thì đơn giản là không có tuỳ
        chỉnh nào, và mặc định là câu trả lời đầy đủ.

        Nhưng bản trước bắt `except Exception` -- gộp luôn mất kết nối,
        hết giờ chờ, sai mật khẩu vào cùng một rọ với "bảng chưa có". Cả
        ba đều trả về {} = "tiệm này không tuỳ chỉnh gì", và vai trò rơi
        về DEFAULT_ROLE_AREAS.

        Mặc định RỘNG HƠN cái một tiệm đã chọn. Trên chính máy này,
        role_permission ghi `staff -> errors, refill, tickets` -- chủ tiệm
        đã bỏ `report` khỏi nhân viên. Mặc định thì có `report`. Nên một
        lần database chớp là nhân viên xem được doanh thu, trong 10 giây
        (role_areas() cache kết quả), và không một dòng log nào ghi lại.

        Giờ thì chỉ 1146 trả về {}. Mọi lỗi khác ném PermissionReadError,
        và người gọi từ chối phục vụ -- xem admin_gui/serve.py,
        require_permission(). Đây là lựa chọn có đánh đổi: console khoá
        lại trong lúc database trục trặc. Đổi lấy việc không bao giờ nới
        quyền cho ai vì một sự cố hạ tầng.

        Cache KHÔNG bị nhiễm độc: hàm này ném lỗi thay vì trả về, nên
        role_areas() không ghi gì vào cache và request kế tiếp thử lại.
    """
    from database.db_core import connect_database, close_database_resources

    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT role, areas FROM role_permission")
        rows = cursor.fetchall()
    except Exception as error:
        if getattr(error, "errno", None) == ER_NO_SUCH_TABLE:
            return {}

        raise PermissionReadError(
            f"Không đọc được bảng role_permission: {error}") from error
    finally:
        try:
            close_database_resources(cursor, connection)
        except Exception:      # noqa: BLE001 - lỗi gốc ở trên quan trọng hơn
            pass

    return {
        str(row["role"]): {
            # An id that stopped existing after an upgrade is dropped
            # rather than fatal: the row was valid when it was written,
            # and refusing to answer would lock out the console over a
            # rename.
            part for part in str(row["areas"] or "").split(",")
            if part and part in AREAS
        }
        for row in rows
    }


def role_areas(role: str) -> set[str]:
    """Every area this role holds, overrides applied, invariants forced."""
    global _cache, _cached_at

    with _lock:
        fresh = _cache is not None and (time.monotonic() - _cached_at) < CACHE_SECONDS
        cached = dict(_cache) if fresh and _cache else None

    if cached is None:
        overrides = _read_overrides()
        cached = {
            name: set(overrides.get(name, default))
            for name, default in DEFAULT_ROLE_AREAS.items()
        }

        with _lock:
            _cache = dict(cached)
            _cached_at = time.monotonic()

    return _forced(role, cached.get(role, set()))


def _forced(role: str, areas: set[str]) -> set[str]:
    """Apply the two rules the screen is not allowed to break."""
    areas = set(areas)
    areas.add(AREA_SHELL)

    if role == "owner":
        areas.add(AREA_USERS)

    return areas


def pages_for_role(role: str) -> list[str]:
    """Every admin page this role may open, in sidebar order."""
    allowed = role_areas(role)
    return [page
            for area, pages in AREA_PAGES.items() if area in allowed
            for page in pages]


# --------------------------------------------------------------------------
# editing
# --------------------------------------------------------------------------

def current_matrix() -> dict:
    """Everything the permission screen needs to draw itself."""
    overrides = _read_overrides()

    return {
        "areas": [
            {"id": area, "label": AREA_LABEL[area],
             "pages": list(AREA_PAGES.get(area, ()))}
            for area in AREAS
        ],
        "roles": {
            role: {
                "areas": sorted(role_areas(role) - {AREA_SHELL}),
                "customised": role in overrides,
                # Told to the screen so it can grey the box rather than
                # let somebody tick it off and be refused.
                "locked": [AREA_USERS] if role == "owner" else [],
            }
            for role in DEFAULT_ROLE_AREAS
        },
        "defaults": {
            role: sorted(areas)
            for role, areas in DEFAULT_ROLE_AREAS.items()
        },
    }


def save_role_areas(role: str, areas, actor: str = "") -> set[str]:
    """Replace one role's areas. Returns what was actually stored.

    Validated here rather than at the endpoint, so the CLI, the screen and
    anything written later all pass through the same refusals.
    """
    role = str(role or "").strip().lower()

    if role not in DEFAULT_ROLE_AREAS:
        raise PermissionError_(f"Vai trò không hợp lệ: {role!r}.")

    wanted = {str(a).strip() for a in (areas or []) if str(a).strip()}
    unknown = sorted(wanted - set(AREAS))

    if unknown:
        raise PermissionError_(
            "Nhóm quyền không tồn tại: " + ", ".join(unknown) + "."
        )

    if role == "owner" and AREA_USERS not in wanted:
        raise PermissionError_(
            "Vai trò Chủ luôn phải giữ quyền “Người dùng & phân quyền” — "
            "bỏ đi thì không còn ai sửa được phân quyền nữa, kể cả trang này."
        )

    # Stored WITHOUT the forced areas. They are applied on read, so the row
    # says what somebody chose rather than what the code then insisted on
    # -- and a rule that changes later does not have to rewrite old rows.
    stored = sorted(wanted - {AREA_SHELL})

    from database.db_core import connect_database, close_database_resources

    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO role_permission (role, areas, updated_by) "
            "VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE areas = VALUES(areas), "
            "updated_by = VALUES(updated_by)",
            (role, ",".join(stored), str(actor or "")[:32] or None),
        )
        connection.commit()
    finally:
        close_database_resources(cursor, connection)

    invalidate()
    return set(stored)


def reset_all() -> int:
    """Throw every override away. Returns how many rows went.

    The way back when a permission change has gone wrong -- including the
    ones this module's invariants do not catch, like a manager role with
    nothing on it and no manager left who can see why.
    """
    from database.db_core import connect_database, close_database_resources

    connection = cursor = None

    try:
        connection = connect_database()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM role_permission")
        removed = cursor.rowcount
        connection.commit()
    finally:
        close_database_resources(cursor, connection)

    invalidate()
    return int(removed)
