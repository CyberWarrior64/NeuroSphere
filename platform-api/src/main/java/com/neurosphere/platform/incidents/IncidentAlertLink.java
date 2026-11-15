package com.neurosphere.platform.incidents;

import com.neurosphere.platform.alerts.AlertRecord;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.time.Instant;

@Entity
@Table(name = "platform_incident_alerts",
        uniqueConstraints = @UniqueConstraint(name = "uk_platform_incident_alerts_pair", columnNames = {"incident_id", "alert_id"}))
public class IncidentAlertLink {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "incident_id", nullable = false)
    private IncidentRecord incident;
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "alert_id", nullable = false)
    private AlertRecord alert;
    @Column(name = "linked_by", nullable = false, length = 64)
    private String linkedBy;
    @Column(name = "linked_at", nullable = false)
    private Instant linkedAt;

    protected IncidentAlertLink() {}

    public IncidentAlertLink(IncidentRecord incident, AlertRecord alert, String linkedBy, Instant linkedAt) {
        this.incident = incident;
        this.alert = alert;
        this.linkedBy = linkedBy;
        this.linkedAt = linkedAt;
    }

    public AlertRecord getAlert() { return alert; }
    public String getLinkedBy() { return linkedBy; }
    public Instant getLinkedAt() { return linkedAt; }
}
