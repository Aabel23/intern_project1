ALTER TABLE sessions
 ADD COLUMN created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 ADD COLUMN absolute_expires_at DATETIME(6) NOT NULL DEFAULT '2000-01-01 00:00:00';
CREATE TABLE refresh_tokens (
 hash BINARY(32) PRIMARY KEY,
 session_id CHAR(36) NOT NULL,
 created_at DATETIME(6) NOT NULL,
 used_at DATETIME(6) NULL,
 FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
CREATE TABLE devices (
 id CHAR(36) PRIMARY KEY,
 serial CHAR(16) NOT NULL,
 name VARCHAR(64) NOT NULL,
 public_key BINARY(65) NOT NULL,
 key_id VARCHAR(32) NOT NULL,
 owner_user_id CHAR(36) NULL,
 created_at DATETIME(6) NOT NULL,
 UNIQUE KEY device_serial (serial),
 UNIQUE KEY device_key (key_id),
 FOREIGN KEY (owner_user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
CREATE TABLE claim_challenges (
 id CHAR(36) PRIMARY KEY,
 device_id CHAR(36) NOT NULL,
 user_id CHAR(36) NOT NULL,
 nonce BINARY(32) NOT NULL,
 expires_at_ms BIGINT NOT NULL,
 consumed_at DATETIME(6) NULL,
 local_session_binding CHAR(36) NULL,
 KEY claim_device (device_id),
 FOREIGN KEY (device_id) REFERENCES devices(id),
 FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
CREATE TABLE device_audit (
 id BIGINT AUTO_INCREMENT PRIMARY KEY,
 device_id CHAR(36) NOT NULL,
 action VARCHAR(32) NOT NULL,
 actor VARCHAR(64) NOT NULL,
 at DATETIME(6) NOT NULL,
 KEY audit_device (device_id),
 FOREIGN KEY (device_id) REFERENCES devices(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
