ALTER TABLE platform_password_reset_tokens
    MODIFY COLUMN token_hash VARCHAR(64) NOT NULL;
