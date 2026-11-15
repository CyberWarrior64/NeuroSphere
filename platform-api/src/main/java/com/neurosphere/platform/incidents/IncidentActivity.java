package com.neurosphere.platform.incidents;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "platform_incident_activity")
public class IncidentActivity {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "incident_id", nullable = false)
    private IncidentRecord incident;
    @Column(nullable = false, length = 64)
    private String actor;
    @Column(nullable = false, length = 32)
    private String action;
    @Column(nullable = false, length = 2000)
    private String details;
    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    protected IncidentActivity() {}

    public IncidentActivity(IncidentRecord incident, String actor, String action, String details, Instant createdAt) {
        this.incident = incident;
        this.actor = actor;
        this.action = action;
        this.details = details;
        this.createdAt = createdAt;
    }

    public Long getId() { return id; }
    public String getActor() { return actor; }
    public String getAction() { return action; }
    public String getDetails() { return details; }
    public Instant getCreatedAt() { return createdAt; }
}
