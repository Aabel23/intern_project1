-- ============================================================
-- MIGRATION: role_permission
--
-- Adds the per-role permission override table. Safe to run twice, and
-- safe to run on a busy machine: it creates an EMPTY table, and an empty
-- table means every role keeps the defaults compiled into
-- admin_gui/permissions.py. Nothing changes until somebody saves on the
-- Người dùng screen.
--
-- Run:  mysql -u <user> -p <database> < database/migrate_role_permission.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS role_permission (
    role VARCHAR(16) NOT NULL PRIMARY KEY,
    areas VARCHAR(255) NOT NULL DEFAULT '',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    updated_by VARCHAR(32) NULL,

    CONSTRAINT ck_role_permission_role
        CHECK (role IN ('owner', 'manager', 'staff'))
) ENGINE=InnoDB;
