package com.neurosphere.platform.alerts;

import java.time.Instant;

public record AlertActivitySummary(Long id, String actor, String action, String details, Instant createdAt) {
    public static AlertActivitySummary from(AlertActivity activity) {
        return new AlertActivitySummary(activity.getId(), activity.getActor(), activity.getAction(),
                activity.getDetails(), activity.getCreatedAt());
    }
}
