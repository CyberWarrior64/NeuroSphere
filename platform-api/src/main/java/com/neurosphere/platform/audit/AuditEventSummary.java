package com.neurosphere.platform.audit;

import java.time.Instant;

public record AuditEventSummary(long id, Instant occurredAt, String actor, String action,
        String targetType, String targetId, String summary) {
    public static AuditEventSummary from(PlatformAuditEvent event) {
        return new AuditEventSummary(event.getId(), event.getOccurredAt(), event.getActor(),
                event.getAction(), event.getTargetType(), event.getTargetId(), event.getSummary());
    }
}
