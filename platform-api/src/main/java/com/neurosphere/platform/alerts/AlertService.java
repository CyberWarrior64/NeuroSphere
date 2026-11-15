package com.neurosphere.platform.alerts;

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
public class AlertService {
    private final AlertRepository alerts;
    private final AlertActivityRepository activities;

    public AlertService(AlertRepository alerts, AlertActivityRepository activities) {
        this.alerts = alerts;
        this.activities = activities;
    }

    @Transactional(readOnly = true)
    public List<AlertSummary> list(int limit, PlatformAlertStatus status) {
        var pageable = PageRequest.of(0, Math.max(1, Math.min(limit, 100)));
        var rows = status == null ? alerts.findAllByOrderByCreatedAtDesc(pageable)
                : alerts.findAllByStatusOrderByCreatedAtDesc(status, pageable);
        return rows.stream().map(AlertSummary::from).toList();
    }

    @Transactional
    public AlertDetail createFromCapture(String sourceReference, String title, String rationale,
            PlatformAlertSeverity severity, String captureMode, String captureSessionId, Instant predictionRecordedAt, String inputSource,
            String modelVersion, String rfClassification, double rfProbability, double rfThreshold,
            boolean rfFlagged, String ifClassification, double ifScore, double ifThreshold,
            boolean ifFlagged, String actor) {
        if (alerts.findBySourceReference(sourceReference).isPresent()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT,
                    "A review alert already exists for this capture prediction.");
        }
        Instant now = Instant.now();
        String key = "NSA-" + UUID.randomUUID().toString().replace("-", "")
                .substring(0, 12).toUpperCase(Locale.ROOT);
        AlertRecord record = alerts.save(new AlertRecord(key, sourceReference, title.trim(), rationale.trim(),
                severity, captureMode, captureSessionId, predictionRecordedAt, inputSource, modelVersion,
                rfClassification, rfProbability, rfThreshold, rfFlagged,
                ifClassification, ifScore, ifThreshold, ifFlagged, actor, now));
        activities.save(new AlertActivity(record, actor, "PROMOTED_TO_REVIEW",
                "Analyst promoted a flagged capture prediction for review.", now));
        return detail(record);
    }

    @Transactional(readOnly = true)
    public AlertDetail get(long id) {
        return detail(find(id));
    }

    @Transactional
    public AlertDetail changeStatus(long id, PlatformAlertStatus status, String actor) {
        AlertRecord record = find(id);
        PlatformAlertStatus previous = record.getStatus();
        if (previous != status) {
            Instant now = Instant.now();
            record.changeStatus(status, now);
            activities.save(new AlertActivity(record, actor, "STATUS_CHANGED",
                    previous.name() + " → " + status.name(), now));
        }
        return detail(record);
    }

    private AlertRecord find(long id) {
        return alerts.findById(id).orElseThrow(() ->
                new ResponseStatusException(HttpStatus.NOT_FOUND, "Alert was not found."));
    }

    private AlertDetail detail(AlertRecord record) {
        return new AlertDetail(AlertSummary.from(record), activities
                .findAllByAlert_IdOrderByCreatedAtAsc(record.getId()).stream()
                .map(AlertActivitySummary::from).toList());
    }
}
