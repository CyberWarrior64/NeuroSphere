CREATE TABLE platform_incidents (
    id BIGINT NOT NULL AUTO_INCREMENT,
    incident_key VARCHAR(20) NOT NULL,
    title VARCHAR(160) NOT NULL,
    description VARCHAR(4000) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    status VARCHAR(24) NOT NULL,
    created_by VARCHAR(64) NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    updated_at TIMESTAMP(6) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_platform_incidents_incident_key (incident_key),
    INDEX ix_platform_incidents_status_updated_at (status, updated_at),
    INDEX ix_platform_incidents_updated_at (updated_at)
);

CREATE TABLE platform_incident_activity (
    id BIGINT NOT NULL AUTO_INCREMENT,
    incident_id BIGINT NOT NULL,
    actor VARCHAR(64) NOT NULL,
    action VARCHAR(32) NOT NULL,
    details VARCHAR(2000) NOT NULL,
    created_at TIMESTAMP(6) NOT NULL,
    PRIMARY KEY (id),
    INDEX ix_platform_incident_activity_incident_created (incident_id, created_at),
    CONSTRAINT fk_platform_incident_activity_incident
        FOREIGN KEY (incident_id) REFERENCES platform_incidents (id) ON DELETE CASCADE
);

CREATE TABLE platform_incident_alerts (
    id BIGINT NOT NULL AUTO_INCREMENT,
    incident_id BIGINT NOT NULL,
    alert_id BIGINT NOT NULL,
    linked_by VARCHAR(64) NOT NULL,
    linked_at TIMESTAMP(6) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_platform_incident_alerts_pair (incident_id, alert_id),
    INDEX ix_platform_incident_alerts_alert (alert_id),
    CONSTRAINT fk_platform_incident_alerts_incident
        FOREIGN KEY (incident_id) REFERENCES platform_incidents (id) ON DELETE CASCADE,
    CONSTRAINT fk_platform_incident_alerts_alert
        FOREIGN KEY (alert_id) REFERENCES platform_alerts (id) ON DELETE CASCADE
);
