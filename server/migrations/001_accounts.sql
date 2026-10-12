CREATE TABLE users (
 id CHAR(36) PRIMARY KEY,
 email VARCHAR(254) NOT NULL,
 password_hash TEXT NOT NULL,
 verified_at DATETIME(6) NULL,
 registration_attempts INT NOT NULL DEFAULT 0,
 registration_locked_until DATETIME(6) NULL,
 UNIQUE KEY users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
CREATE TABLE otp_generations (
 id CHAR(36) PRIMARY KEY,
 email VARCHAR(254) NOT NULL,
 purpose VARCHAR(16) NOT NULL,
 hash BINARY(32) NOT NULL,
 expires_at DATETIME(6) NOT NULL,
 consumed_at DATETIME(6) NULL,
 generation INT NOT NULL,
 status ENUM('sending','active','consumed','failed') NOT NULL,
 UNIQUE KEY otp_generation (email,purpose,generation),
 KEY otp_expiry (expires_at),
 CHECK (generation > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
CREATE TABLE sessions (
 id CHAR(36) PRIMARY KEY,
 user_id CHAR(36) NOT NULL,
 refresh_hash BINARY(32) NOT NULL,
 refresh_expires_at DATETIME(6) NOT NULL,
 revoked_at DATETIME(6) NULL,
 UNIQUE KEY session_refresh (refresh_hash),
 KEY session_expiry (refresh_expires_at),
 FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
CREATE TABLE access_tokens (
 hash BINARY(32) PRIMARY KEY,
 session_id CHAR(36) NOT NULL,
 expires_at DATETIME(6) NOT NULL,
 KEY access_expiry (expires_at),
 FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
