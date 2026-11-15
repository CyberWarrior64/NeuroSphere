package com.neurosphere.platform.incidents;

import com.neurosphere.platform.alerts.AlertActivity;
import com.neurosphere.platform.alerts.AlertRecord;
import com.neurosphere.platform.alerts.AlertRepository;
import com.neurosphere.platform.alerts.AlertSummary;
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
public class IncidentService {
    private final IncidentRepository incidents;
    private final IncidentActivityRepository activities;
    private final IncidentAlertLinkRepository links;
    private final AlertRepository alerts;

    public IncidentService(IncidentRepository incidents, IncidentActivityRepository activities,
            IncidentAlertLinkRepository links, AlertRepository alerts) {
        this.incidents = incidents;
        this.activities = activities;
        this.links = links;
        this.alerts = alerts;
    }

    @Transactional(readOnly = true)
    public List<IncidentSummary> list(int limit, PlatformIncidentStatus status) {
        var pageable = PageRequest.of(0, Math.max(1, Math.min(limit, 100)));
        var rows = status == null ? incidents.findAllByOrderByUpdatedAtDesc(pageable)
                : incidents.findAllByStatusOrderByUpdatedAtDesc(status, pageable);
        return rows.stream().map(IncidentSummary::from).toList();
    }

    @Transactional
    public IncidentDetail create(CreateIncidentRequest request, String actor) {
        Instant now = Instant.now();
        String key = "NSI-" + UUID.randomUUID().toString().replace("-", "")
                .substring(0, 12).toUpperCase(Locale.ROOT);
        IncidentRecord incident = incidents.save(new IncidentRecord(key, request.title().trim(),
                request.description().trim(), request.severity(), actor, now));
        activities.save(new IncidentActivity(incident, actor, "CREATED",
                "Incident opened for analyst investigation.", now));
        return detail(incident);
    }

    @Transactional(readOnly = true)
    public IncidentDetail get(long id) {
        return detail(find(id));
    }

    @Transactional
    public IncidentDetail changeStatus(long id, PlatformIncidentStatus status, String actor) {
        IncidentRecord incident = find(id);
        PlatformIncidentStatus previous = incident.getStatus();
        if (previous != status) {
            Instant now = Instant.now();
            incident.changeStatus(status, now);
            activities.save(new IncidentActivity(incident, actor, "STATUS_CHANGED",
                    previous.name() + " → " + status.name(), now));
        }
        return detail(incident);
    }

    @Transactional
    public IncidentDetail addNote(long id, String note, String actor) {
        IncidentRecord incident = find(id);
        Instant now = Instant.now();
        incident.touch(now);
        activities.save(new IncidentActivity(incident, actor, "NOTE_ADDED", note.trim(), now));
        return detail(incident);
    }

    @Transactional
    public IncidentDetail linkAlert(long incidentId, long alertId, String actor) {
        IncidentRecord incident = find(incidentId);
        AlertRecord alert = alerts.findById(alertId).orElseThrow(() ->
                new ResponseStatusException(HttpStatus.NOT_FOUND, "Review alert was not found."));
        if (links.existsByIncident_IdAndAlert_Id(incidentId, alertId)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "This review alert is already linked.");
        }
        Instant now = Instant.now();
        links.save(new IncidentAlertLink(incident, alert, actor, now));
        activities.save(new IncidentActivity(incident, actor, "ALERT_LINKED",
                "Linked review alert " + alert.getAlertKey() + " (" + alert.getSeverity().name() + ").", now));
        incident.touch(now);
        return detail(incident);
    }

    private IncidentRecord find(long id) {
        return incidents.findById(id).orElseThrow(() ->
                new ResponseStatusException(HttpStatus.NOT_FOUND, "Incident was not found."));
    }

    private IncidentDetail detail(IncidentRecord incident) {
        List<IncidentActivitySummary> activity = activities
                .findAllByIncident_IdOrderByCreatedAtAsc(incident.getId()).stream()
                .map(IncidentActivitySummary::from).toList();
        List<AlertSummary> linkedAlerts = links
                .findAllByIncident_IdOrderByLinkedAtAsc(incident.getId()).stream()
                .map(IncidentAlertLink::getAlert).map(AlertSummary::from).toList();
        return new IncidentDetail(IncidentSummary.from(incident), activity, linkedAlerts);
    }
}
