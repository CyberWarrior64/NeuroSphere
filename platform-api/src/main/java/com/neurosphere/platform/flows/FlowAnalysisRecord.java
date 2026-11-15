package com.neurosphere.platform.flows;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "platform_flow_analyses")
public class FlowAnalysisRecord {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "submitted_by", nullable = false, length = 64)
    private String submittedBy;

    @Column(name = "analyzed_at", nullable = false)
    private Instant analyzedAt;

    @Column(name = "model_version", nullable = false, length = 80)
    private String modelVersion;

    @Column(name = "rf_classification", nullable = false, length = 32)
    private String rfClassification;

    @Column(name = "rf_attack_probability", nullable = false)
    private double rfAttackProbability;

    @Column(name = "rf_flagged", nullable = false)
    private boolean rfFlagged;

    @Column(name = "if_classification", nullable = false, length = 32)
    private String ifClassification;

    @Column(name = "if_anomaly_score", nullable = false)
    private double ifAnomalyScore;

    @Column(name = "if_flagged", nullable = false)
    private boolean ifFlagged;

    @Column(name = "detector_agreement", nullable = false, length = 64)
    private String detectorAgreement;

    protected FlowAnalysisRecord() {}

    public FlowAnalysisRecord(String submittedBy, Instant analyzedAt, String modelVersion,
            String rfClassification, double rfAttackProbability, boolean rfFlagged,
            String ifClassification, double ifAnomalyScore, boolean ifFlagged,
            String detectorAgreement) {
        this.submittedBy = submittedBy;
        this.analyzedAt = analyzedAt;
        this.modelVersion = modelVersion;
        this.rfClassification = rfClassification;
        this.rfAttackProbability = rfAttackProbability;
        this.rfFlagged = rfFlagged;
        this.ifClassification = ifClassification;
        this.ifAnomalyScore = ifAnomalyScore;
        this.ifFlagged = ifFlagged;
        this.detectorAgreement = detectorAgreement;
    }

    public Long getId() { return id; }
    public String getSubmittedBy() { return submittedBy; }
    public Instant getAnalyzedAt() { return analyzedAt; }
    public String getModelVersion() { return modelVersion; }
    public String getRfClassification() { return rfClassification; }
    public double getRfAttackProbability() { return rfAttackProbability; }
    public boolean isRfFlagged() { return rfFlagged; }
    public String getIfClassification() { return ifClassification; }
    public double getIfAnomalyScore() { return ifAnomalyScore; }
    public boolean isIfFlagged() { return ifFlagged; }
    public String getDetectorAgreement() { return detectorAgreement; }
}
