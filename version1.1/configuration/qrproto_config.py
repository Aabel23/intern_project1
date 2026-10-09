"""Deployment configuration for qrproto: this machine's AES-256 key and
its MID (machine ID), both loaded from the environment.

DEPLOYMENT SHAPE: STANDALONE, NOT ONE SERVER PLUS MANY SCANNERS
    Each machine runs main.py whole -- store_gui.serve (which prints a
    label) and order.run_flow (which scans and pours it) in the same
    process, on the same physical unit. A label created here is never
    read anywhere but here. There is no separate central server handing
    out MIDs to dumb pour stations; printer/printer_qr.py has no key at
    all, it only draws whatever already-encrypted string it is given.

    That shape is what makes QRPROTO_KEY a PER-MACHINE secret, not a
    shared deployment-wide one: give every machine its own independently
    generated key. Two machines never need to read each other's labels,
    so there is nothing to keep in sync between them -- generate one at
    setup, keep it on that machine, done. Sharing a single key across
    multiple machines would only make sense under a different topology
    (one central order-taking server encrypting for several separate
    pour stations), which is not what this project runs.

WHY ENVIRONMENT VARIABLES, NOT A FILE
    Matches database/config.py's convention (BEVERAGE_DB_* env vars) --
    one place secrets are expected to come from, rather than a second
    convention invented just for this key. A key checked into a JSON
    file next to pump_calib.json would end up in every backup and every
    git history this project ever has.

WHAT EACH VALUE IS
    QRPROTO_KEY          64 hex characters (32 bytes) -- THIS machine's
                          own AES-256 key, used for both create() and
                          verify() since both run here. Generate it once,
                          on this machine, and never copy it to another:

                            python3 -c "from qrproto.keys import generate_key; print(generate_key().hex())"
                            export QRPROTO_KEY=<64 hex generated>

                          qrproto has no key rotation yet, so changing it
                          later invalidates every label THIS machine has
                          already printed but not yet scanned -- but,
                          per the standalone shape above, has no effect
                          on any other machine.

    QRPROTO_MACHINE_ID   An integer 1-999999 naming THIS machine. Every
                          payload created here is bound to it (the MID
                          field), and every payload scanned here is
                          checked against it. Since this machine's own
                          key is not shared with any other machine, a
                          mismatched MID can only happen from a label
                          hand-carried or replayed from elsewhere on
                          purpose -- MID is defense in depth here, not
                          the primary boundary between machines the way
                          it would be if a key were ever shared.

WHY get_key() IS LAZY AND MACHINE_ID IS NOT
    MACHINE_ID has a safe default (1, matching the single-machine
    deployment this project runs today) and reading it can never fail,
    so it is resolved once at import time like every other constant in
    configuration/.

    KEY has no safe default -- there is no value that is right to fall
    back to -- so get_key() resolves it lazily, on first call, instead
    of at import time. Importing this module (or anything that imports
    it) must not require QRPROTO_KEY to already be set; only actually
    creating or verifying a payload should. The result is cached so the
    environment is only read once per process.
"""

import os

from configuration.env_files import load_env_files
from qrproto.keys import load_key_from_env

# Cùng lý do như database/config.py: lệnh chạy tay không đi qua systemd,
# nên phải tự đọc file cấu hình thay vì bắt người gõ `set -a; . ...`.
load_env_files()

QRPROTO_KEY_ENV_VAR = "QRPROTO_KEY"

# Matches the single machine this deployment runs today (see
# project_gui_is_sole_controller). A second machine must set its own
# QRPROTO_MACHINE_ID before going live -- sharing this value between two
# scanners would let a label meant for one machine run on the other.
MACHINE_ID = int(os.getenv("QRPROTO_MACHINE_ID", "1"))

_key_cache: bytes | None = None


def get_key() -> bytes:
    """Return the shared deployment key, reading it from the
    environment on first call and caching the result.

    Raises KeyError if QRPROTO_KEY is not set, ValueError if it is set
    but is not valid 64-character hex -- both from
    qrproto.keys.load_key_from_env, uncaught here so the real cause
    reaches whoever is trying to print or scan a label.
    """
    global _key_cache

    if _key_cache is None:
        _key_cache = load_key_from_env(QRPROTO_KEY_ENV_VAR)

    return _key_cache
