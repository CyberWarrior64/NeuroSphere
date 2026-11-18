package com.neurosphere.platform.audit;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "platform_audit_events")
public class PlatformAuditEvent {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "occurred_at", nullable = false, updatable = false)
    private Instant occurredAt;

    @Column(nullable = false, length = 64, updatable = false)
    private String actor;

    @Column(nullable = false, length = 48, updatable = false)
    private String action;

    @Column(name = "target_type", nullable = false, length = 32, updatable = false)
    private String targetType;

    @Column(name = "target_id", nullable = false, length = 80, updatable = false)
    private String targetId;

    @Column(nullable = false, length = 240, updatable = false)
    private String summary;

    protected PlatformAuditEvent() {}

    public PlatformAuditEvent(String actor, String action, String targetType, String targetId,
            String summary, Instant occurredAt) {
        this.actor = actor;
        this.action = action;
        this.targetType = targetType;
        this.targetId = targetId;
        this.summary = summary;
        this.occurredAt = occurredAt;
    }

    public Long getId() { return id; }
    public Instant getOccurredAt() { return occurredAt; }
    public String getActor() { return actor; }
    public String getAction() { return action; }
    public String getTargetType() { return targetType; }
    public String getTargetId() { return targetId; }
    public String getSummary() { return summary; }
}
