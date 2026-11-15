package com.neurosphere.platform.cases;

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
@Table(name = "platform_cases")
public class CaseRecord {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "case_key", nullable = false, unique = true, length = 20)
    private String caseKey;

    @Column(nullable = false, length = 160)
    private String title;

    @Column(nullable = false, length = 4000)
    private String description;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 24)
    private PlatformCaseStatus status;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 16)
    private PlatformCasePriority priority;

    @Column(name = "source_type", nullable = false, length = 32)
    private String sourceType;

    @Column(name = "source_reference", length = 128)
    private String sourceReference;

    @Column(name = "created_by", nullable = false, length = 64)
    private String createdBy;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    protected CaseRecord() {}

    public CaseRecord(String caseKey, String title, String description, PlatformCasePriority priority,
            String sourceType, String sourceReference, String createdBy, Instant now) {
        this.caseKey = caseKey;
        this.title = title;
        this.description = description;
        this.status = PlatformCaseStatus.OPEN;
        this.priority = priority;
        this.sourceType = sourceType;
        this.sourceReference = sourceReference;
        this.createdBy = createdBy;
        this.createdAt = now;
        this.updatedAt = now;
    }

    public void changeStatus(PlatformCaseStatus status, Instant now) {
        this.status = status;
        this.updatedAt = now;
    }

    public void touch(Instant now) {
        this.updatedAt = now;
    }

    public Long getId() { return id; }
    public String getCaseKey() { return caseKey; }
    public String getTitle() { return title; }
    public String getDescription() { return description; }
    public PlatformCaseStatus getStatus() { return status; }
    public PlatformCasePriority getPriority() { return priority; }
    public String getSourceType() { return sourceType; }
    public String getSourceReference() { return sourceReference; }
    public String getCreatedBy() { return createdBy; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
