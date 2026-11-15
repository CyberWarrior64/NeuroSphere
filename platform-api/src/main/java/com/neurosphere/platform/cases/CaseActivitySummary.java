package com.neurosphere.platform.cases;

import java.time.Instant;

public record CaseActivitySummary(Long id, String actor, String action, String details, Instant createdAt) {
    public static CaseActivitySummary from(CaseActivity activity) {
        return new CaseActivitySummary(activity.getId(), activity.getActor(), activity.getAction(),
                activity.getDetails(), activity.getCreatedAt());
    }
}
