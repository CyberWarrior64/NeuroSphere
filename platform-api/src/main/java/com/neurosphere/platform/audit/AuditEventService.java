package com.neurosphere.platform.audit;

import java.time.Instant;
import java.util.List;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuditEventService {
    private final PlatformAuditEventRepository events;

    public AuditEventService(PlatformAuditEventRepository events) {
        this.events = events;
    }

    public void record(String actor, String action, String targetType, String targetId,
            String summary, Instant occurredAt) {
        events.save(new PlatformAuditEvent(actor, action, targetType, targetId, summary, occurredAt));
    }

    @Transactional(readOnly = true)
    public List<AuditEventSummary> latest(int limit) {
        int boundedLimit = Math.max(1, Math.min(limit, 200));
        return events.findAllByOrderByOccurredAtDescIdDesc(PageRequest.of(0, boundedLimit)).stream()
                .map(AuditEventSummary::from).toList();
    }
}
