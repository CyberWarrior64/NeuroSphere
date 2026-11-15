package com.neurosphere.platform.cases;

import java.time.Instant;

public record CaseSummary(
        Long id,
        String caseKey,
        String title,
        String description,
        PlatformCaseStatus status,
        PlatformCasePriority priority,
        String sourceType,
        String sourceReference,
        String createdBy,
        Instant createdAt,
        Instant updatedAt) {
    public static CaseSummary from(CaseRecord record) {
        return new CaseSummary(record.getId(), record.getCaseKey(), record.getTitle(), record.getDescription(),
                record.getStatus(), record.getPriority(), record.getSourceType(), record.getSourceReference(),
                record.getCreatedBy(), record.getCreatedAt(), record.getUpdatedAt());
    }
}
