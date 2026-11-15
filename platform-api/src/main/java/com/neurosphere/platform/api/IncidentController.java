package com.neurosphere.platform.api;

import com.neurosphere.platform.incidents.AddIncidentNoteRequest;
import com.neurosphere.platform.incidents.ChangeIncidentStatusRequest;
import com.neurosphere.platform.incidents.CreateIncidentRequest;
import com.neurosphere.platform.incidents.IncidentDetail;
import com.neurosphere.platform.incidents.IncidentService;
import com.neurosphere.platform.incidents.IncidentSummary;
import com.neurosphere.platform.incidents.PlatformIncidentStatus;
import jakarta.validation.Valid;
import java.net.URI;
import java.util.List;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/platform/incidents")
public class IncidentController {
    private final IncidentService incidents;

    public IncidentController(IncidentService incidents) {
        this.incidents = incidents;
    }

    @GetMapping
    public List<IncidentSummary> list(@RequestParam(defaultValue = "50") int limit,
            @RequestParam(required = false) PlatformIncidentStatus status) {
        return incidents.list(limit, status);
    }

    @PostMapping
    public ResponseEntity<IncidentDetail> create(@Valid @RequestBody CreateIncidentRequest request,
            Authentication authentication) {
        IncidentDetail result = incidents.create(request, authentication.getName());
        return ResponseEntity.created(URI.create("/api/v1/platform/incidents/" + result.incident().id()))
                .body(result);
    }

    @GetMapping("/{id}")
    public IncidentDetail get(@PathVariable long id) {
        return incidents.get(id);
    }

    @PatchMapping("/{id}/status")
    public IncidentDetail changeStatus(@PathVariable long id,
            @Valid @RequestBody ChangeIncidentStatusRequest request, Authentication authentication) {
        return incidents.changeStatus(id, request.status(), authentication.getName());
    }

    @PostMapping("/{id}/notes")
    public IncidentDetail addNote(@PathVariable long id, @Valid @RequestBody AddIncidentNoteRequest request,
            Authentication authentication) {
        return incidents.addNote(id, request.note(), authentication.getName());
    }

    @PostMapping("/{id}/alerts/{alertId}")
    public IncidentDetail linkAlert(@PathVariable long id, @PathVariable long alertId,
            Authentication authentication) {
        return incidents.linkAlert(id, alertId, authentication.getName());
    }
}
