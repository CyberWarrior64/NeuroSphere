package com.neurosphere.platform.incidents;

import java.time.Instant;

public record IncidentActivitySummary(Long id, String actor, String action, String details, Instant createdAt) {
    public static IncidentActivitySummary from(IncidentActivity activity) {
        return new IncidentActivitySummary(activity.getId(), activity.getActor(), activity.getAction(),
                activity.getDetails(), activity.getCreatedAt());
    }
}
