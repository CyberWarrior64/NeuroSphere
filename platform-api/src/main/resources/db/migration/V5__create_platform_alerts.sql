CREATE TABLE platform_alerts (
    id BIGINT NOT NULL AUTO_INCREMENT,
    alert_key VARCHAR(20) NOT NULL,
    source_reference VARCHAR(64) NOT NULL,
    title VARCHAR(160) NOT NULL,
    description VARCHAR(2000) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    status VARCHAR(24) NOT NULL,
    capture_mode VARCHAR(16) NOT NULL,
    prediction_recorded_at TIMESTAMP(6) NOT NULL,
    capture_session_id VARCHAR(36) NULL,
    input_source VARCHAR(80) NOT NULL,
    model_version VARCHAR(80) NOT NULL,
    rf_classification VARCHAR(32) NOT NULL,
    rf_probability DOUBLE NOT NULL,
    rf_threshold DOUBLE NOT NULL,
    rf_flagged BOOLEAN NOT NULL,
    if_classification VARCHAR(32) NOT NULL,
    if_score DOUBLE NOT NULL,
    if_threshold DOUBLE NOT NULL,
    if_flagged BOOLEAN NOT NULL,
    created_by VARCHAR(64) NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_platform_alerts_alert_key (alert_key),
    UNIQUE KEY uk_platform_alerts_source_reference (source_reference),
    INDEX ix_platform_alerts_status_created_at (status, created_at),
    INDEX ix_platform_alerts_created_at (created_at)
);

CREATE TABLE platform_alert_activity (
    id BIGINT NOT NULL AUTO_INCREMENT,
    alert_id BIGINT NOT NULL,
    actor VARCHAR(64) NOT NULL,
    action VARCHAR(32) NOT NULL,
    details VARCHAR(2000) NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    PRIMARY KEY (id),
    INDEX ix_platform_alert_activity_alert_created (alert_id, created_at),
    CONSTRAINT fk_platform_alert_activity_alert
        FOREIGN KEY (alert_id) REFERENCES platform_alerts (id) ON DELETE CASCADE
);
