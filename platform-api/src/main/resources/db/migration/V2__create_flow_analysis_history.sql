CREATE TABLE platform_flow_analyses (
    id BIGINT NOT NULL AUTO_INCREMENT,
    submitted_by VARCHAR(64) NOT NULL,
    analyzed_at TIMESTAMP(6) NOT NULL,
    model_version VARCHAR(80) NOT NULL,
    rf_classification VARCHAR(32) NOT NULL,
    rf_attack_probability DOUBLE NOT NULL,
    rf_flagged BOOLEAN NOT NULL,
    if_classification VARCHAR(32) NOT NULL,
    if_anomaly_score DOUBLE NOT NULL,
    if_flagged BOOLEAN NOT NULL,
    detector_agreement VARCHAR(64) NOT NULL,
    PRIMARY KEY (id),
    INDEX ix_platform_flow_analyses_analyzed_at (analyzed_at),
    INDEX ix_platform_flow_analyses_submitted_by_analyzed_at (submitted_by, analyzed_at)
);
