# ============================================================
# CENTRAL DATABASE CONFIGURATION
# ============================================================

import os
from pathlib import Path

from configuration.env_files import load_env_files


DATABASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = DATABASE_DIR.parent

SQL_FILE = DATABASE_DIR / "database.sql"

DB_NAME = os.getenv("BEVERAGE_DB_NAME", "beveragepos")

# Nạp .env và /etc/flexmix/qrproto.env cho các lệnh chạy tay. Biến systemd
# đã truyền vào luôn thắng — xem configuration/env_files.py.
load_env_files()

# The password has no default on purpose: a fallback baked into the source is
# a password published to everyone who can read the repository. Set it in
# /etc/flexmix/qrproto.env (systemd reads that), or in a local .env file --
# see .env.example.
DB_PASSWORD = os.getenv("BEVERAGE_DB_PASSWORD")

if DB_PASSWORD is None:
    raise RuntimeError(
        "Chua dat bien moi truong BEVERAGE_DB_PASSWORD.\n"
        "Tao file .env o thu muc goc (xem .env.example), hoac chay:\n"
        "    export BEVERAGE_DB_PASSWORD='mat_khau_mysql_cua_ban'"
    )

SERVER_CONFIG = {
    "host": os.getenv("BEVERAGE_DB_HOST", "localhost"),
    "port": int(os.getenv("BEVERAGE_DB_PORT", "3306")),
    "user": os.getenv("BEVERAGE_DB_USER", "root"),
    "password": DB_PASSWORD,
}

DB_CONFIG = {
    **SERVER_CONFIG,
    "database": DB_NAME,
}
