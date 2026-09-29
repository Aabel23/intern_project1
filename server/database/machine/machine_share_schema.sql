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
