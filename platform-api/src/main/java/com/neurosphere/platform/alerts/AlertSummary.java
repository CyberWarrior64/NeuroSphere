package com.neurosphere.platform.alerts;

import java.time.Instant;

public record AlertSummary(
        Long id,
        String alertKey,
        String sourceReference,
        String title,
        String description,
        PlatformAlertSeverity severity,
        PlatformAlertStatus status,
        String captureMode,
        String captureSessionId,
        Instant predictionRecordedAt,
        String inputSource,
        String modelVersion,
        String rfClassification,
        double rfProbability,
        double rfThreshold,
        boolean rfFlagged,
        String ifClassification,
        double ifScore,
        double ifThreshold,
        boolean ifFlagged,
        String createdBy,
        Instant createdAt,
        Instant updatedAt) {
    public static AlertSummary from(AlertRecord r) {
        return new AlertSummary(r.getId(), r.getAlertKey(), r.getSourceReference(), r.getTitle(),
                r.getDescription(), r.getSeverity(), r.getStatus(), r.getCaptureMode(),
                r.getCaptureSessionId(), r.getPredictionRecordedAt(), r.getInputSource(), r.getModelVersion(),
                r.getRfClassification(), r.getRfProbability(), r.getRfThreshold(), r.isRfFlagged(),
                r.getIfClassification(), r.getIfScore(), r.getIfThreshold(), r.isIfFlagged(),
                r.getCreatedBy(), r.getCreatedAt(), r.getUpdatedAt());
    }
}
