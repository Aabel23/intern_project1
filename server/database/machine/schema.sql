CREATE TABLE IF NOT EXISTS machines (
    machine_id TEXT PRIMARY KEY NOT NULL CHECK (length(trim(machine_id)) > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    product_key_hash TEXT,
    store_id INTEGER,
    model TEXT,
    serial_number TEXT UNIQUE,
    firmware_version TEXT,
    location TEXT,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'maintenance', 'disabled')),
    last_seen REAL CHECK (last_seen IS NULL OR last_seen >= 0),
    heartbeat_interval_seconds INTEGER NOT NULL DEFAULT 5
        CHECK (heartbeat_interval_seconds > 0),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_machines_store_id ON machines(store_id);

CREATE TRIGGER IF NOT EXISTS machines_updated_at
AFTER UPDATE OF machine_id, name, store_id, model, serial_number,
    firmware_version, location, status, last_seen, heartbeat_interval_seconds, notes
ON machines
BEGIN
    UPDATE machines SET updated_at = datetime('now')
    WHERE machine_id = NEW.machine_id;
END;

-- Liên kết máy với tài khoản quản lý; một máy có thể có nhiều người, một người nhiều máy.
CREATE TABLE IF NOT EXISTS machine_managers (
    machine_id TEXT NOT NULL REFERENCES machines(machine_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'manager' CHECK (role IN ('owner', 'manager')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (machine_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_machine_managers_user_id ON machine_managers(user_id);

-- Mỗi máy chỉ có tối đa một chủ sở hữu.
CREATE UNIQUE INDEX IF NOT EXISTS machine_managers_one_owner
    ON machine_managers(machine_id) WHERE role = 'owner';

-- Mã mời chủ máy tạo để nhân viên quét QR nhận quản lý máy; dùng một lần.
CREATE TABLE IF NOT EXISTS machine_invites (
    code_hash TEXT PRIMARY KEY NOT NULL,
    machine_id TEXT NOT NULL REFERENCES machines(machine_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at REAL NOT NULL,
    used_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    used_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_machine_invites_machine_id ON machine_invites(machine_id);
