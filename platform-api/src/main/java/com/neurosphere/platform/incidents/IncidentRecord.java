package com.neurosphere.platform.incidents;

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
@Table(name = "platform_incidents")
public class IncidentRecord {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @Column(name = "incident_key", nullable = false, unique = true, length = 20)
    private String incidentKey;
    @Column(nullable = false, length = 160)
    private String title;
    @Column(nullable = false, length = 4000)
    private String description;
    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 16)
    private PlatformIncidentSeverity severity;
    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 24)
    private PlatformIncidentStatus status;
    @Column(name = "created_by", nullable = false, length = 64)
    private String createdBy;
    @Column(name = "created_at", nullable = false)
    private Instant createdAt;
    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    protected IncidentRecord() {}

    public IncidentRecord(String incidentKey, String title, String description, PlatformIncidentSeverity severity,
            String createdBy, Instant now) {
        this.incidentKey = incidentKey;
        this.title = title;
        this.description = description;
        this.severity = severity;
        this.status = PlatformIncidentStatus.OPEN;
        this.createdBy = createdBy;
        this.createdAt = now;
        this.updatedAt = now;
    }

    public void changeStatus(PlatformIncidentStatus status, Instant now) {
        this.status = status;
        this.updatedAt = now;
    }

    public void touch(Instant now) { this.updatedAt = now; }

    public Long getId() { return id; }
    public String getIncidentKey() { return incidentKey; }
    public String getTitle() { return title; }
    public String getDescription() { return description; }
    public PlatformIncidentSeverity getSeverity() { return severity; }
    public PlatformIncidentStatus getStatus() { return status; }
    public String getCreatedBy() { return createdBy; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
