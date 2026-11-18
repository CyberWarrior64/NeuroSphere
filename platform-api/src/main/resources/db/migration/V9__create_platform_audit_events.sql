CREATE TABLE platform_audit_events (
    id BIGINT NOT NULL AUTO_INCREMENT,
    occurred_at TIMESTAMP NOT NULL,
    actor VARCHAR(64) NOT NULL,
    action VARCHAR(48) NOT NULL,
    target_type VARCHAR(32) NOT NULL,
    target_id VARCHAR(80) NOT NULL,
    summary VARCHAR(240) NOT NULL,
    PRIMARY KEY (id),
    INDEX idx_platform_audit_events_occurred_at (occurred_at, id),
    INDEX idx_platform_audit_events_actor_time (actor, occurred_at)
);
