package com.neurosphere.platform.incidents;

import java.time.Instant;

public record IncidentSummary(Long id, String incidentKey, String title, String description,
        PlatformIncidentSeverity severity, PlatformIncidentStatus status, String createdBy,
        Instant createdAt, Instant updatedAt) {
    public static IncidentSummary from(IncidentRecord incident) {
        return new IncidentSummary(incident.getId(), incident.getIncidentKey(), incident.getTitle(),
                incident.getDescription(), incident.getSeverity(), incident.getStatus(), incident.getCreatedBy(),
                incident.getCreatedAt(), incident.getUpdatedAt());
    }
}
