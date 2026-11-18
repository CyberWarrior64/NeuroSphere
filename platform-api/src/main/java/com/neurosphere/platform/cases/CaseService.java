package com.neurosphere.platform.cases;

import com.neurosphere.platform.audit.AuditEventService;
import java.time.Instant;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class CaseService {
    private final CaseRepository cases;
    private final CaseActivityRepository activities;
    private final AuditEventService auditEvents;

    public CaseService(CaseRepository cases, CaseActivityRepository activities, AuditEventService auditEvents) {
        this.cases = cases;
        this.activities = activities;
        this.auditEvents = auditEvents;
    }

    @Transactional(readOnly = true)
    public List<CaseSummary> list(int limit, PlatformCaseStatus status) {
        int boundedLimit = Math.max(1, Math.min(limit, 100));
        var pageable = PageRequest.of(0, boundedLimit);
        var records = status == null
                ? cases.findAllByOrderByUpdatedAtDesc(pageable)
                : cases.findAllByStatusOrderByUpdatedAtDesc(status, pageable);
        return records.stream().map(CaseSummary::from).toList();
    }

    @Transactional
    public CaseDetail create(CreateCaseRequest request, String actor) {
        Instant now = Instant.now();
        String key = "NSC-" + UUID.randomUUID().toString().replace("-", "")
                .substring(0, 12).toUpperCase(Locale.ROOT);
        String sourceType = request.sourceType() == null ? "MANUAL" : request.sourceType();
        CaseRecord record = cases.save(new CaseRecord(key, request.title().trim(), request.description().trim(),
                request.priority(), sourceType, request.sourceReference(), actor, now));
        activities.save(new CaseActivity(record, actor, "CREATED",
                "Case opened with " + request.priority().name().toLowerCase(Locale.ROOT) + " priority.", now));
        auditEvents.record(actor, "CASE_CREATED", "CASE", key, "Opened a case record.", now);
        return detail(record);
    }

    @Transactional(readOnly = true)
    public CaseDetail get(long id) {
        return detail(find(id));
    }

    @Transactional
    public CaseDetail changeStatus(long id, PlatformCaseStatus newStatus, String actor) {
        CaseRecord record = find(id);
        PlatformCaseStatus previous = record.getStatus();
        if (previous != newStatus) {
            Instant now = Instant.now();
            record.changeStatus(newStatus, now);
            activities.save(new CaseActivity(record, actor, "STATUS_CHANGED",
                    previous.name() + " → " + newStatus.name(), now));
            auditEvents.record(actor, "CASE_STATUS_CHANGED", "CASE", record.getCaseKey(),
                    "Changed case status from " + previous.name() + " to " + newStatus.name() + ".", now);
        }
        return detail(record);
    }

    @Transactional
    public CaseDetail addNote(long id, String note, String actor) {
        CaseRecord record = find(id);
        Instant now = Instant.now();
        record.touch(now);
        activities.save(new CaseActivity(record, actor, "NOTE_ADDED", note.trim(), now));
        auditEvents.record(actor, "CASE_NOTE_ADDED", "CASE", record.getCaseKey(),
                "Added a case note. Note text is kept out of the audit log.", now);
        return detail(record);
    }

    private CaseRecord find(long id) {
        return cases.findById(id).orElseThrow(() ->
                new ResponseStatusException(HttpStatus.NOT_FOUND, "Case was not found."));
    }

    private CaseDetail detail(CaseRecord record) {
        return new CaseDetail(CaseSummary.from(record), activities
                .findAllByCaseRecord_IdOrderByCreatedAtAsc(record.getId()).stream()
                .map(CaseActivitySummary::from).toList());
    }
}
