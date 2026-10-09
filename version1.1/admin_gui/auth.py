"""Who may sign in to the console, what they may do, and how the server knows.

WHY THIS EXISTS
    admin_gui/login.js compares nothing. That was not always true: the
    check used to be in the browser, which was fine while the admin API
    sat on its own port -- the port was the real fence. Serving the admin
    endpoints from the store server takes the fence away, so every
    decision has to be made somewhere the browser cannot be asked
    politely to skip. Nothing here trusts the page.

ACCOUNTS LIVE IN MySQL, THE SIGNING SECRET LIVES IN A FILE
    Two different kinds of thing, so two different homes.

    An account is about a person: it is created, renamed, demoted,
    switched off, and it wants to be listed and audited. That is a table
    -- see admin_user in database/database.sql.

    The signing secret is about the machine: it is what proves a token
    came from this server. It stays in configuration/admin_account.json
    at mode 0600, because verifying a signature must not need a database
    round trip, and because a secret that never changes per person has no
    business in a per-person table.

THE PASSWORD
    PBKDF2-HMAC-SHA256 with a per-account random salt, never plaintext
    and never a bare SHA-256 -- a plain digest of a short password is a
    lookup away from being reversed, which is the entire reason for a
    slow KDF with a salt. The round count is stored WITH each row, so
    raising the cost for new passwords does not lock out everyone whose
    hash was made at the old cost. hashlib only; no new dependency on a
    machine that has to keep running with no internet.

THE SESSION
    A signed token, not a row: user, issue time, expiry and a nonce, with
    an HMAC over all four. The server can verify one without remembering
    it, which matters because this process gets restarted a lot and staff
    being logged out every time the machine is poked is how a password
    ends up on a sticky note.

    A stateless token cannot be deleted, and "cannot be deleted" is
    unacceptable once accounts can be switched off -- otherwise removing
    somebody means removing them in up to TOKEN_LIFETIME_HOURS. So the
    token carries when it was issued, and check_token() refuses one older
    than that account's sessions_valid_from. Changing a password or
    deactivating an account moves that column forward, and the session
    dies on the next request rather than at its own convenience.

    The role is NOT in the token. It is read from the row on every
    request, so a demotion takes effect at once instead of when the
    holder next logs in.

RUNNING IT
    python3 -m admin_gui.auth --list                      # who exists
    python3 -m admin_gui.auth --set-password --user NAME  # create/change
    python3 -m admin_gui.auth --role owner --user NAME    # change a role
    python3 -m admin_gui.auth --new-secret                # log everybody out
"""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import time
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
ACCOUNT_FILE = PROJECT_DIR / "configuration" / "admin_account.json"

# PBKDF2 rounds. Chosen by measuring on this Pi: enough that guessing is
# expensive, small enough that a login still feels instant.
PBKDF2_ROUNDS = 240_000
SALT_BYTES = 16
SECRET_BYTES = 32

# How long a login lasts. Still short -- a token that has not yet expired
# is one more thing that can be stolen -- but no longer the only way to
# end a session; see sessions_valid_from above.
TOKEN_LIFETIME_HOURS = 12

MIN_PASSWORD_LENGTH = 8

# What a username may be. Deliberately narrow: it is typed at a login box
# on a tablet, it is compared lower-cased, and it appears in a URL query
# nowhere -- so the useful shapes are short and boring.
USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{1,31}$")

# The three roles, most powerful first. Order matters: outranks() reads
# it, and that is what stops a manager editing an owner.
ROLE_OWNER = "owner"
ROLE_MANAGER = "manager"
ROLE_STAFF = "staff"
ROLES = (ROLE_OWNER, ROLE_MANAGER, ROLE_STAFF)

ROLE_LABEL = {
    ROLE_OWNER: "Chủ",
    ROLE_MANAGER: "Quản lý",
    ROLE_STAFF: "Nhân viên",
}


class AuthError(Exception):
    """A login, a token or an account change that cannot be accepted."""


# --------------------------------------------------------------------------
# the machine's signing secret
# --------------------------------------------------------------------------

def _read_secret_file() -> dict:
    try:
        with open(ACCOUNT_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, ValueError, OSError):
        return {}

    return data if isinstance(data, dict) else {}


def _write_secret_file(data: dict) -> None:
    """Write the secret file, readable only by this user.

    The mode is set on the temporary file BEFORE the rename, so the
    contents are never briefly world-readable -- a window that lasts
    microseconds is still a window, and this file is the one worth it.
    """
    ACCOUNT_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = ACCOUNT_FILE.with_name(f".{ACCOUNT_FILE.name}.tmp")

    handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)

    with os.fdopen(handle, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())

    os.replace(temporary, ACCOUNT_FILE)


def _signing_secret() -> bytes:
    """The key every token is signed with, minted on first use.

    Generated here rather than by a setup step because the alternative is
    a server that runs with no secret and finds out at the first login.
    """
    data = _read_secret_file()
    stored = data.get("secret")

    if not stored:
        stored = base64.b64encode(
            secrets.token_bytes(SECRET_BYTES)).decode("ascii")
        data["secret"] = stored
        _write_secret_file(data)

    return base64.b64decode(stored)


def new_secret() -> None:
    """Re-sign with a fresh secret, which invalidates every live token."""
    data = _read_secret_file()
    data["secret"] = base64.b64encode(
        secrets.token_bytes(SECRET_BYTES)).decode("ascii")
    _write_secret_file(data)


# --------------------------------------------------------------------------
# passwords
# --------------------------------------------------------------------------

def hash_password(password: str, salt: bytes,
                  rounds: int = PBKDF2_ROUNDS) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, rounds,
    )
    return base64.b64encode(digest).decode("ascii")


def _check_password_rules(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(
            f"Mật khẩu phải dài ít nhất {MIN_PASSWORD_LENGTH} ký tự."
        )


def _clean_username(user: str) -> str:
    user = str(user or "").strip().lower()

    if not USERNAME_PATTERN.match(user):
        raise AuthError(
            "Tên đăng nhập chỉ gồm chữ thường, số, dấu chấm, gạch ngang "
            "hoặc gạch dưới; dài 2–32 ký tự và bắt đầu bằng chữ hoặc số."
        )

    return user


def _clean_role(role: str) -> str:
    role = str(role or "").strip().lower()

    if role not in ROLES:
        raise AuthError(f"Vai trò không hợp lệ: {role!r}.")

    return role


def outranks(actor_role: str, target_role: str) -> bool:
    """May an actor of this role act on an account of that one?

    Strictly greater, never equal: an owner may not demote or delete
    another owner. Two owners who can remove each other is a race with a
    shop locked out of its own console at the end of it, and the fix --
    the CLI, on the machine -- is the one place where being physically
    present is already the check.
    """
    return ROLES.index(actor_role) < ROLES.index(target_role)


# --------------------------------------------------------------------------
# the accounts table
# --------------------------------------------------------------------------
#
# db_core is imported inside each function, not at module scope. This
# module is pulled in by admin_gui/serve.py, which store_gui/serve.py
# imports at start-up, and a database driver that cannot load must not be
# the reason the store screen fails to come up.

def _connect():
    from database.db_core import connect_database
    return connect_database()


def _close(cursor=None, connection=None) -> None:
    from database.db_core import close_database_resources
    close_database_resources(cursor, connection)


def _fetch_user(username: str) -> dict | None:
    connection = cursor = None

    try:
        connection = _connect()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT user_id, username, display_name, password_hash, "
            "       password_salt, kdf_rounds, role, active, "
            "       sessions_valid_from "
            "FROM admin_user WHERE username = %s",
            (username,),
        )
        return cursor.fetchone()
    finally:
        _close(cursor, connection)


def list_users() -> list[dict]:
    """Every account, most powerful first, then alphabetical."""
    connection = cursor = None

    try:
        connection = _connect()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT user_id, username, display_name, role, active, "
            "       created_at, updated_at, last_login_at "
            "FROM admin_user "
            "ORDER BY FIELD(role, 'owner', 'manager', 'staff'), username"
        )
        rows = cursor.fetchall()
    finally:
        _close(cursor, connection)

    return [
        {
            "user_id": int(row["user_id"]),
            "username": row["username"],
            "display_name": row["display_name"] or "",
            "role": row["role"],
            "role_label": ROLE_LABEL.get(row["role"], row["role"]),
            "active": bool(row["active"]),
            "created_at": str(row["created_at"]) if row["created_at"] else None,
            "updated_at": str(row["updated_at"]) if row["updated_at"] else None,
            "last_login_at": (str(row["last_login_at"])
                              if row["last_login_at"] else None),
        }
        for row in rows
    ]


def count_active_owners(exclude_user_id: int | None = None) -> int:
    """Active owners, optionally ignoring one row.

    Used before every change that could remove the last one. The console
    has no way back in without an owner -- the CLI on the machine is the
    only recovery -- so this is checked before demoting, deactivating,
    renaming a role, or deleting.
    """
    connection = cursor = None

    try:
        connection = _connect()
        cursor = connection.cursor()

        if exclude_user_id is None:
            cursor.execute(
                "SELECT COUNT(*) FROM admin_user "
                "WHERE role = %s AND active = 1",
                (ROLE_OWNER,),
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM admin_user "
                "WHERE role = %s AND active = 1 AND user_id <> %s",
                (ROLE_OWNER, int(exclude_user_id)),
            )

        return int(cursor.fetchone()[0])
    finally:
        _close(cursor, connection)


def get_user(user_id: int) -> dict:
    connection = cursor = None

    try:
        connection = _connect()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT user_id, username, display_name, role, active "
            "FROM admin_user WHERE user_id = %s",
            (int(user_id),),
        )
        row = cursor.fetchone()
    finally:
        _close(cursor, connection)

    if row is None:
        raise AuthError(f"Không có tài khoản id {user_id}.")

    return row


def create_user(username: str, password: str, role: str,
                display_name: str = "") -> dict:
    """Add an account. Raises if the name is taken."""
    username = _clean_username(username)
    role = _clean_role(role)
    _check_password_rules(password)

    salt = secrets.token_bytes(SALT_BYTES)
    connection = cursor = None

    try:
        connection = _connect()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO admin_user (username, display_name, password_hash, "
            "password_salt, kdf_rounds, role, active) "
            "VALUES (%s, %s, %s, %s, %s, %s, 1)",
            (username, str(display_name or "").strip()[:64] or None,
             hash_password(password, salt),
             base64.b64encode(salt).decode("ascii"),
             PBKDF2_ROUNDS, role),
        )
        connection.commit()
        user_id = int(cursor.lastrowid)
    except Exception as error:
        if "Duplicate" in str(error) or "1062" in str(error):
            raise AuthError(
                f"Tên đăng nhập '{username}' đã có rồi."
            ) from error
        raise
    finally:
        _close(cursor, connection)

    return {"user_id": user_id, "username": username, "role": role}


def set_password(username: str, password: str) -> None:
    """Replace one account's password and end its live sessions.

    The sessions go because a password is changed for two reasons and one
    of them is that somebody else knows it. Leaving the old token working
    for the rest of the day would mean the change did nothing about the
    only case that was urgent.
    """
    username = _clean_username(username)
    _check_password_rules(password)

    salt = secrets.token_bytes(SALT_BYTES)
    connection = cursor = None

    try:
        connection = _connect()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE admin_user SET password_hash = %s, password_salt = %s, "
            "kdf_rounds = %s, sessions_valid_from = NOW() "
            "WHERE username = %s",
            (hash_password(password, salt),
             base64.b64encode(salt).decode("ascii"),
             PBKDF2_ROUNDS, username),
        )
        changed = cursor.rowcount
        connection.commit()
    finally:
        _close(cursor, connection)

    if not changed:
        raise AuthError(f"Không có tài khoản '{username}'.")


def set_role(user_id: int, role: str) -> None:
    """Move one account to another role."""
    role = _clean_role(role)
    row = get_user(user_id)

    if row["role"] == ROLE_OWNER and role != ROLE_OWNER:
        if count_active_owners(exclude_user_id=user_id) == 0:
            raise AuthError(
                "Đây là chủ duy nhất còn hoạt động — đổi vai trò sẽ không "
                "còn ai quản lý được tài khoản."
            )

    connection = cursor = None

    try:
        connection = _connect()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE admin_user SET role = %s WHERE user_id = %s",
            (role, int(user_id)),
        )
        connection.commit()
    finally:
        _close(cursor, connection)


def set_active(user_id: int, active: bool) -> None:
    """Switch an account on or off. Switching off ends its sessions now."""
    row = get_user(user_id)

    if not active and row["role"] == ROLE_OWNER:
        if count_active_owners(exclude_user_id=user_id) == 0:
            raise AuthError(
                "Đây là chủ duy nhất còn hoạt động — tắt đi sẽ không còn ai "
                "quản lý được tài khoản."
            )

    connection = cursor = None

    try:
        connection = _connect()
        cursor = connection.cursor()
        # sessions_valid_from moves only on the way OFF. Turning an
        # account back on has no session to invalidate, and moving it
        # would silently sign out anyone who happened to be using it.
        if active:
            cursor.execute(
                "UPDATE admin_user SET active = 1 WHERE user_id = %s",
                (int(user_id),),
            )
        else:
            cursor.execute(
                "UPDATE admin_user SET active = 0, "
                "sessions_valid_from = NOW() WHERE user_id = %s",
                (int(user_id),),
            )
        connection.commit()
    finally:
        _close(cursor, connection)


def set_display_name(user_id: int, display_name: str) -> None:
    get_user(user_id)
    connection = cursor = None

    try:
        connection = _connect()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE admin_user SET display_name = %s WHERE user_id = %s",
            (str(display_name or "").strip()[:64] or None, int(user_id)),
        )
        connection.commit()
    finally:
        _close(cursor, connection)


def delete_user(user_id: int) -> dict:
    """Remove an account outright."""
    row = get_user(user_id)

    if row["role"] == ROLE_OWNER and count_active_owners(
            exclude_user_id=user_id) == 0:
        raise AuthError(
            "Đây là chủ duy nhất còn hoạt động — xoá đi sẽ không còn ai "
            "quản lý được tài khoản."
        )

    connection = cursor = None

    try:
        connection = _connect()
        cursor = connection.cursor()
        cursor.execute(
            "DELETE FROM admin_user WHERE user_id = %s", (int(user_id),),
        )
        connection.commit()
    finally:
        _close(cursor, connection)

    return {"user_id": int(user_id), "username": row["username"]}


# --------------------------------------------------------------------------
# first run
# --------------------------------------------------------------------------

def adopt_legacy_account() -> str | None:
    """Copy the single JSON account into the table, once.

    The hash and salt are carried over UNCHANGED, so the password that was
    working yesterday still works today -- an upgrade that silently
    required a new password would be an upgrade that locks the shop out of
    its own console.

    Returns the username adopted, or None if there was nothing to adopt or
    the table already has accounts. Safe to call on every start.
    """
    data = _read_secret_file()
    user = str(data.get("user") or "").strip().lower()

    if not user or not data.get("hash") or not data.get("salt"):
        return None

    try:
        if _fetch_user(user) is not None:
            return None

        connection = cursor = None

        try:
            connection = _connect()
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM admin_user")

            if int(cursor.fetchone()[0]):
                return None

            cursor.execute(
                "INSERT INTO admin_user (username, password_hash, "
                "password_salt, kdf_rounds, role, active) "
                "VALUES (%s, %s, %s, %s, %s, 1)",
                (user, str(data["hash"]), str(data["salt"]),
                 int(data.get("rounds", PBKDF2_ROUNDS)), ROLE_OWNER),
            )
            connection.commit()
        finally:
            _close(cursor, connection)
    except Exception:
        # A database that is not up yet must not stop the server starting.
        # The console will report "no account" until it is, which is the
        # truth as far as anything can tell.
        return None

    return user


def is_configured() -> bool:
    """Is there at least one account that can be logged into?"""
    try:
        connection = cursor = None

        try:
            connection = _connect()
            cursor = connection.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM admin_user WHERE active = 1")
            return int(cursor.fetchone()[0]) > 0
        finally:
            _close(cursor, connection)
    except Exception:
        return False


# --------------------------------------------------------------------------
# logging in
# --------------------------------------------------------------------------

def verify_password(user: str, password: str) -> dict | None:
    """Check one login. Returns the account row, or None.

    Constant-time on the hash, and slow on purpose. A missing account
    still pays for one PBKDF2 round trip against a throwaway salt, so the
    time taken does not say whether the username exists.
    """
    row = _fetch_user(str(user or "").strip().lower())

    if row is None:
        hash_password(password, b"absent-account-timing-decoy")
        return None

    digest = hash_password(
        password,
        base64.b64decode(row["password_salt"]),
        int(row["kdf_rounds"] or PBKDF2_ROUNDS),
    )

    if not hmac.compare_digest(str(row["password_hash"]), digest):
        return None

    if not row["active"]:
        raise AuthError("Tài khoản này đã bị khoá.")

    return row


def note_login(user_id: int) -> None:
    """Record that this account just signed in. Never fatal."""
    connection = cursor = None

    try:
        connection = _connect()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE admin_user SET last_login_at = NOW() WHERE user_id = %s",
            (int(user_id),),
        )
        connection.commit()
    except Exception:
        pass
    finally:
        _close(cursor, connection)


def _sign(payload: str, secret: bytes) -> str:
    return base64.urlsafe_b64encode(
        hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).digest()
    ).decode("ascii").rstrip("=")


def issue_token(user: str) -> dict:
    """Mint a session token for a login that has already been checked."""
    issued = int(time.time())
    expires = issued + TOKEN_LIFETIME_HOURS * 3600
    nonce = secrets.token_hex(8)
    payload = f"{user}|{issued}|{expires}|{nonce}"

    return {
        "token": f"{payload}|{_sign(payload, _signing_secret())}",
        "user": user,
        "expires": expires,
    }


def check_token(token: str | None) -> dict:
    """Return {user, role, user_id, display_name} for this token, or raise.

    Four things are checked, in this order and for a reason:

      1. the signature, because until it holds every other field is just
         something a stranger typed;
      2. the expiry;
      3. that the account still exists and is still switched on;
      4. that the token was issued after the account's
         sessions_valid_from -- which is how a password change or a
         deactivation ends a session that is otherwise still valid.

    The ROLE comes from the row, never from the token, so a demotion
    takes effect on the next request rather than the next login.
    """
    if not token:
        raise AuthError("Chưa đăng nhập.")

    parts = str(token).split("|")

    if len(parts) != 5:
        # A four-part token is the old format, from before sessions could
        # be ended. Refused rather than accepted-without-the-check: one
        # re-login is cheaper than a session nobody can revoke.
        raise AuthError("Phiên đăng nhập không hợp lệ, vui lòng đăng nhập lại.")

    user, issued, expires, nonce, signature = parts
    payload = f"{user}|{issued}|{expires}|{nonce}"

    if not hmac.compare_digest(_sign(payload, _signing_secret()), signature):
        raise AuthError("Phiên đăng nhập không hợp lệ.")

    try:
        issued_at = int(issued)
        deadline = int(expires)
    except ValueError:
        raise AuthError("Phiên đăng nhập không hợp lệ.") from None

    if deadline < time.time():
        raise AuthError("Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.")

    row = _fetch_user(user)

    if row is None:
        raise AuthError("Tài khoản không còn tồn tại.")

    if not row["active"]:
        raise AuthError("Tài khoản này đã bị khoá.")

    valid_from = row["sessions_valid_from"]

    if valid_from is not None and issued_at < valid_from.timestamp():
        raise AuthError(
            "Phiên đăng nhập đã kết thúc, vui lòng đăng nhập lại."
        )

    return {
        "user": row["username"],
        "user_id": int(row["user_id"]),
        "display_name": row["display_name"] or "",
        "role": row["role"],
        "role_label": ROLE_LABEL.get(row["role"], row["role"]),
    }


# --------------------------------------------------------------------------
# command line
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Manage accounts from the machine itself.

    This is the way back in when the console cannot be reached: no
    accounts yet, or the last owner locked out. It talks to the database
    directly and asks nobody's permission, which is exactly why it is on
    the machine and not on a web page.
    """
    parser = argparse.ArgumentParser(
        description="Quản lý tài khoản đăng nhập của màn hình admin.",
    )
    parser.add_argument("--user", help="Tên đăng nhập.")
    parser.add_argument(
        "--set-password", action="store_true",
        help="Tạo tài khoản mới hoặc đổi mật khẩu tài khoản đã có.",
    )
    parser.add_argument(
        "--role", choices=ROLES,
        help="Vai trò: dùng kèm --set-password khi tạo mới, "
             "hoặc một mình để đổi vai trò.",
    )
    parser.add_argument(
        "--list", action="store_true", help="Liệt kê tài khoản.",
    )
    parser.add_argument(
        "--new-secret", action="store_true",
        help="Đổi khóa ký, đăng xuất mọi phiên đang mở.",
    )
    parser.add_argument(
        "--reset-permissions", action="store_true",
        help="Xoá mọi tuỳ chỉnh phân quyền, trả các vai trò về mặc định.",
    )
    parser.add_argument(
        "--show-permissions", action="store_true",
        help="Xem vai trò nào đang có nhóm quyền nào.",
    )
    args = parser.parse_args(argv)

    try:
        adopt_legacy_account()

        if args.new_secret:
            new_secret()
            print("Đã đổi khóa ký. Mọi phiên đang mở phải đăng nhập lại.")
            return 0

        # The way back when a permission change has gone wrong. It is on
        # the machine, not on a web page, precisely because the failure it
        # exists for is "the web page cannot be reached any more".
        if args.reset_permissions:
            from admin_gui import permissions

            removed = permissions.reset_all()
            print(f"Đã xoá {removed} tuỳ chỉnh phân quyền. "
                  "Mọi vai trò trở về mặc định.")
            args.show_permissions = True

        if args.show_permissions:
            from admin_gui import permissions

            for role in ROLES:
                held = sorted(permissions.role_areas(role)
                              - {permissions.AREA_SHELL})
                print(f"{ROLE_LABEL[role] + ' (' + role + ')':<20}"
                      + (", ".join(held) or "(không có nhóm nào)"))
            return 0

        if args.set_password:
            if not args.user:
                print("Thiếu --user.", file=sys.stderr)
                return 1

            username = _clean_username(args.user)
            password = getpass.getpass("Mật khẩu mới: ")

            if password != getpass.getpass("Nhập lại: "):
                print("Hai lần nhập không khớp.", file=sys.stderr)
                return 1

            if _fetch_user(username) is None:
                # The first account is always an owner: an install whose
                # only account could not manage accounts would need this
                # CLI again immediately.
                role = args.role or (
                    ROLE_OWNER if not list_users() else ROLE_STAFF
                )
                create_user(username, password, role)
                print(f"Đã tạo '{username}' với vai trò "
                      f"{ROLE_LABEL[role]} ({role}).")
            else:
                set_password(username, password)
                print(f"Đã đổi mật khẩu cho '{username}'. "
                      "Các phiên đang mở của tài khoản này đã bị đăng xuất.")

                if args.role:
                    set_role(_fetch_user(username)["user_id"], args.role)
                    print(f"Vai trò giờ là {ROLE_LABEL[args.role]}.")

            return 0

        if args.role:
            if not args.user:
                print("Thiếu --user.", file=sys.stderr)
                return 1

            row = _fetch_user(_clean_username(args.user))

            if row is None:
                print(f"Không có tài khoản '{args.user}'.", file=sys.stderr)
                return 1

            set_role(row["user_id"], args.role)
            print(f"'{row['username']}' giờ là "
                  f"{ROLE_LABEL[args.role]} ({args.role}).")
            return 0

        users = list_users()

        if not users:
            print("Chưa có tài khoản nào.")
            print("Tạo bằng: python3 -m admin_gui.auth "
                  "--set-password --user <tên>")
            return 1

        print(f"{'TÀI KHOẢN':<20}{'VAI TRÒ':<20}{'TRẠNG THÁI':<12}ĐĂNG NHẬP CUỐI")
        for row in users:
            print(f"{row['username']:<20}"
                  f"{row['role_label'] + ' (' + row['role'] + ')':<20}"
                  f"{'bật' if row['active'] else 'tắt':<12}"
                  f"{row['last_login_at'] or '—'}")

        print(f"\nPhiên {TOKEN_LIFETIME_HOURS} giờ. "
              f"Khóa ký tại {ACCOUNT_FILE}")
        return 0
    except AuthError as error:
        print(f"LỖI: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
