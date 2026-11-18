package com.neurosphere.platform.api;

import com.neurosphere.platform.audit.AuditEventService;
import com.neurosphere.platform.audit.AuditEventSummary;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/platform/admin/audit-events")
public class AuditEventController {
    private final AuditEventService auditEvents;

    public AuditEventController(AuditEventService auditEvents) {
        this.auditEvents = auditEvents;
    }

    @GetMapping
    public List<AuditEventSummary> latest(@RequestParam(defaultValue = "100") int limit) {
        return auditEvents.latest(limit);
    }
}
