package com.neurosphere.platform.api;

import com.neurosphere.platform.cases.AddCaseNoteRequest;
import com.neurosphere.platform.cases.CaseDetail;
import com.neurosphere.platform.cases.CaseService;
import com.neurosphere.platform.cases.CaseSummary;
import com.neurosphere.platform.cases.ChangeCaseStatusRequest;
import com.neurosphere.platform.cases.CreateCaseRequest;
import com.neurosphere.platform.cases.PlatformCaseStatus;
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
@RequestMapping("/api/v1/platform/cases")
public class CaseController {
    private final CaseService cases;

    public CaseController(CaseService cases) {
        this.cases = cases;
    }

    @GetMapping
    public List<CaseSummary> list(@RequestParam(defaultValue = "50") int limit,
            @RequestParam(required = false) PlatformCaseStatus status) {
        return cases.list(limit, status);
    }

    @PostMapping
    public ResponseEntity<CaseDetail> create(@Valid @RequestBody CreateCaseRequest request,
            Authentication authentication) {
        CaseDetail created = cases.create(request, authentication.getName());
        return ResponseEntity.created(URI.create("/api/v1/platform/cases/" + created.caseRecord().id()))
                .body(created);
    }

    @GetMapping("/{id}")
    public CaseDetail get(@PathVariable long id) {
        return cases.get(id);
    }

    @PatchMapping("/{id}/status")
    public CaseDetail changeStatus(@PathVariable long id, @Valid @RequestBody ChangeCaseStatusRequest request,
            Authentication authentication) {
        return cases.changeStatus(id, request.status(), authentication.getName());
    }

    @PostMapping("/{id}/notes")
    public CaseDetail addNote(@PathVariable long id, @Valid @RequestBody AddCaseNoteRequest request,
            Authentication authentication) {
        return cases.addNote(id, request.note(), authentication.getName());
    }
}
