-- 0003 · Nền dữ liệu của agent server mẹ
--
-- VÌ SAO CÓ FILE NÀY
-- Agent cần nhớ epoch/menu/con trỏ đồng bộ và kết quả lệnh qua mất điện.
-- Ledger tách riêng để lệnh đã chạy không bị chạy lại sau khi mất response.
-- CREATE IF NOT EXISTS cho phép chạy lại nếu migration dừng sau DDL đầu tiên.
--
-- CÁCH ÁP VÀ KIỂM
-- Chạy theo luồng migration hiện có: python3 -m database.main update
-- Chạy lệnh đó lần hai: migration 0003 phải được bỏ qua theo checksum.
-- Trên MySQL, kiểm SHOW TABLES LIKE 'agent_%'; và SHOW CREATE TABLE cho
-- agent_state, agent_ledger. Không chạy riêng file SQL này bằng tay.
CREATE TABLE IF NOT EXISTS agent_state (
    id TINYINT UNSIGNED NOT NULL PRIMARY KEY,
    install_uuid CHAR(36) NOT NULL,
    credential_kid VARCHAR(32) NULL,
    server_epoch BINARY(16) NULL,
    applied_epoch BINARY(16) NULL,
    applied_version BIGINT UNSIGNED NULL,
    applied_sha256 BINARY(32) NULL,
    ticket_cursor_at DATETIME(6) NULL,
    ticket_cursor_serial INT UNSIGNED NOT NULL DEFAULT 0,
    error_cursor BIGINT UNSIGNED NOT NULL DEFAULT 0,
    stock_acked_hash BINARY(32) NULL,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT chk_agent_state_singleton CHECK (id = 1),
    CONSTRAINT chk_agent_applied_tuple CHECK (
        (applied_epoch IS NULL AND applied_version IS NULL AND applied_sha256 IS NULL)
        OR (applied_epoch IS NOT NULL AND applied_version IS NOT NULL AND applied_sha256 IS NOT NULL)
    )
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS agent_ledger (
    command_id BINARY(16) NOT NULL PRIMARY KEY,
    fingerprint BINARY(32) NOT NULL,
    kind VARCHAR(32) NOT NULL,
    state ENUM('claimed', 'done', 'failed') NOT NULL,
    result_json JSON NULL,
    acked BOOLEAN NOT NULL DEFAULT FALSE,
    server_epoch BINARY(16) NOT NULL,
    created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    INDEX idx_agent_ledger_ack (acked, updated_at),
    CONSTRAINT chk_agent_ledger_result CHECK (
        (state = 'claimed' AND result_json IS NULL)
        OR (state IN ('done', 'failed') AND result_json IS NOT NULL)
    )
) ENGINE=InnoDB;
