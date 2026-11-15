package com.neurosphere.platform.flows;

import java.time.Instant;

public record FlowAnalysisSummary(
        Long id,
        Instant analyzedAt,
        String submittedBy,
        String modelVersion,
        String rfClassification,
        double rfAttackProbability,
        boolean rfFlagged,
        String ifClassification,
        double ifAnomalyScore,
        boolean ifFlagged,
        String detectorAgreement) {
    public static FlowAnalysisSummary from(FlowAnalysisRecord record) {
        return new FlowAnalysisSummary(record.getId(), record.getAnalyzedAt(), record.getSubmittedBy(),
                record.getModelVersion(), record.getRfClassification(), record.getRfAttackProbability(),
                record.isRfFlagged(), record.getIfClassification(), record.getIfAnomalyScore(),
                record.isIfFlagged(), record.getDetectorAgreement());
    }
}
