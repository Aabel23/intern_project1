-- ============================================================
-- MIGRATION: admin_user
--
-- Adds the accounts table to an installation created before it existed.
-- Safe to run twice: the CREATE is IF NOT EXISTS and nothing here writes
-- a row.
--
-- IT DOES NOT CREATE THE FIRST ACCOUNT.
--   That happens on the next server start, in admin_gui/auth.py:
--   adopt_legacy_account() copies whatever is in
--   configuration/admin_account.json into this table as the first
--   'owner', hash and salt unchanged, so the password nobody has written
--   down still works. Doing it here instead would mean a SQL file that
--   has to read a JSON file, and an install whose account depended on
--   which of the two ran first.
--
--   With no legacy file and no rows, the console says so and points at
--   `python3 -m admin_gui.auth --set-password`, exactly as it did when
--   there was no account at all.
--
-- Run:  mysql -u <user> -p <database> < database/migrate_admin_user.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS admin_user (
    user_id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(32) NOT NULL,
    display_name VARCHAR(64) NULL,
    password_hash VARCHAR(64) NOT NULL,
    password_salt VARCHAR(32) NOT NULL,
    kdf_rounds INT UNSIGNED NOT NULL DEFAULT 240000,
    role VARCHAR(16) NOT NULL DEFAULT 'staff',
    active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    last_login_at DATETIME NULL,
    sessions_valid_from DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_admin_user_username (username),

    CONSTRAINT ck_admin_user_role
        CHECK (role IN ('owner', 'manager', 'staff'))
) ENGINE=InnoDB;
