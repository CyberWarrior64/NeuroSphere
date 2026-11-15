package com.neurosphere.platform.alerts;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "platform_alerts")
public class AlertRecord {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "alert_key", nullable = false, unique = true, length = 20)
    private String alertKey;
    @Column(name = "source_reference", nullable = false, unique = true, length = 64)
    private String sourceReference;
    @Column(nullable = false, length = 160)
    private String title;
    @Column(nullable = false, length = 2000)
    private String description;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 16)
    private PlatformAlertSeverity severity;
    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 24)
    private PlatformAlertStatus status;

    @Column(name = "capture_mode", nullable = false, length = 16)
    private String captureMode;
    @Column(name = "capture_session_id", length = 36)
    private String captureSessionId;
    @Column(name = "prediction_recorded_at", nullable = false)
    private Instant predictionRecordedAt;
    @Column(name = "input_source", nullable = false, length = 80)
    private String inputSource;
    @Column(name = "model_version", nullable = false, length = 80)
    private String modelVersion;
    @Column(name = "rf_classification", nullable = false, length = 32)
    private String rfClassification;
    @Column(name = "rf_probability", nullable = false)
    private double rfProbability;
    @Column(name = "rf_threshold", nullable = false)
    private double rfThreshold;
    @Column(name = "rf_flagged", nullable = false)
    private boolean rfFlagged;
    @Column(name = "if_classification", nullable = false, length = 32)
    private String ifClassification;
    @Column(name = "if_score", nullable = false)
    private double ifScore;
    @Column(name = "if_threshold", nullable = false)
    private double ifThreshold;
    @Column(name = "if_flagged", nullable = false)
    private boolean ifFlagged;
    @Column(name = "created_by", nullable = false, length = 64)
    private String createdBy;
    @Column(name = "created_at", nullable = false)
    private Instant createdAt;
    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    protected AlertRecord() {}

    public AlertRecord(String alertKey, String sourceReference, String title, String description,
            PlatformAlertSeverity severity, String captureMode, String captureSessionId, Instant predictionRecordedAt,
            String inputSource, String modelVersion, String rfClassification, double rfProbability,
            double rfThreshold, boolean rfFlagged, String ifClassification, double ifScore,
            double ifThreshold, boolean ifFlagged, String createdBy, Instant now) {
        this.alertKey = alertKey;
        this.sourceReference = sourceReference;
        this.title = title;
        this.description = description;
        this.severity = severity;
        this.status = PlatformAlertStatus.OPEN;
        this.captureMode = captureMode;
        this.captureSessionId = captureSessionId;
        this.predictionRecordedAt = predictionRecordedAt;
        this.inputSource = inputSource;
        this.modelVersion = modelVersion;
        this.rfClassification = rfClassification;
        this.rfProbability = rfProbability;
        this.rfThreshold = rfThreshold;
        this.rfFlagged = rfFlagged;
        this.ifClassification = ifClassification;
        this.ifScore = ifScore;
        this.ifThreshold = ifThreshold;
        this.ifFlagged = ifFlagged;
        this.createdBy = createdBy;
        this.createdAt = now;
        this.updatedAt = now;
    }

    public void changeStatus(PlatformAlertStatus status, Instant now) {
        this.status = status;
        this.updatedAt = now;
    }

    public Long getId() { return id; }
    public String getAlertKey() { return alertKey; }
    public String getSourceReference() { return sourceReference; }
    public String getTitle() { return title; }
    public String getDescription() { return description; }
    public PlatformAlertSeverity getSeverity() { return severity; }
    public PlatformAlertStatus getStatus() { return status; }
    public String getCaptureMode() { return captureMode; }
    public String getCaptureSessionId() { return captureSessionId; }
    public Instant getPredictionRecordedAt() { return predictionRecordedAt; }
    public String getInputSource() { return inputSource; }
    public String getModelVersion() { return modelVersion; }
    public String getRfClassification() { return rfClassification; }
    public double getRfProbability() { return rfProbability; }
    public double getRfThreshold() { return rfThreshold; }
    public boolean isRfFlagged() { return rfFlagged; }
    public String getIfClassification() { return ifClassification; }
    public double getIfScore() { return ifScore; }
    public double getIfThreshold() { return ifThreshold; }
    public boolean isIfFlagged() { return ifFlagged; }
    public String getCreatedBy() { return createdBy; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
