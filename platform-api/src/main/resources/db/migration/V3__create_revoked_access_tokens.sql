CREATE TABLE revoked_access_tokens (
    jti VARCHAR(36) NOT NULL,
    expires_at TIMESTAMP(6) NOT NULL,
    PRIMARY KEY (jti),
    INDEX idx_revoked_access_tokens_expires_at (expires_at)
) ENGINE=InnoDB;
