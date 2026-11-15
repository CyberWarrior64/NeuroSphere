CREATE TABLE platform_cases (
    id BIGINT NOT NULL AUTO_INCREMENT,
    case_key VARCHAR(20) NOT NULL,
    title VARCHAR(160) NOT NULL,
    description VARCHAR(4000) NOT NULL,
    status VARCHAR(24) NOT NULL,
    priority VARCHAR(16) NOT NULL,
    source_type VARCHAR(32) NOT NULL,
    source_reference VARCHAR(128) NULL,
    created_by VARCHAR(64) NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_platform_cases_case_key (case_key),
    INDEX ix_platform_cases_updated_at (updated_at),
    INDEX ix_platform_cases_status_updated_at (status, updated_at)
);

CREATE TABLE platform_case_activity (
    id BIGINT NOT NULL AUTO_INCREMENT,
    case_id BIGINT NOT NULL,
    actor VARCHAR(64) NOT NULL,
    action VARCHAR(32) NOT NULL,
    details VARCHAR(2000) NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    PRIMARY KEY (id),
    INDEX ix_platform_case_activity_case_created (case_id, created_at),
    CONSTRAINT fk_platform_case_activity_case
        FOREIGN KEY (case_id) REFERENCES platform_cases (id) ON DELETE CASCADE
);
