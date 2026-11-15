package com.neurosphere.platform.api;

import com.neurosphere.platform.alerts.AlertDetail;
import com.neurosphere.platform.alerts.AlertService;
import com.neurosphere.platform.alerts.AlertSummary;
import com.neurosphere.platform.alerts.ChangeAlertStatusRequest;
import com.neurosphere.platform.alerts.PlatformAlertSeverity;
import com.neurosphere.platform.alerts.PlatformAlertStatus;
import com.neurosphere.platform.alerts.PromoteCapturePredictionRequest;
import jakarta.validation.Valid;
import java.net.URI;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.Map;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpStatus;
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
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/v1/platform/alerts")
public class AlertController {
    private final AlertService alerts;
    private final RestClient aiEngine;

    public AlertController(AlertService alerts, RestClient aiEngine) {
        this.alerts = alerts;
        this.aiEngine = aiEngine;
    }

    @GetMapping
    public List<AlertSummary> list(@RequestParam(defaultValue = "50") int limit,
            @RequestParam(required = false) PlatformAlertStatus status) {
        return alerts.list(limit, status);
    }

    @PostMapping("/from-capture/{predictionId}")
    public ResponseEntity<AlertDetail> promote(@PathVariable String predictionId,
            @Valid @RequestBody PromoteCapturePredictionRequest request, Authentication authentication) {
        Map<String, Object> event = findCapturePrediction(predictionId);
        boolean rfFlagged = bool(event, "rf_flagged");
        boolean ifFlagged = bool(event, "if_flagged");
        if (!rfFlagged && !ifFlagged) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY,
                    "Only a model-flagged capture prediction can be promoted for review.");
        }
        AlertDetail created = alerts.createFromCapture(
                predictionId, request.title(), request.analystRationale(), request.severity(),
                text(event, "capture_mode", "unspecified", 16), optionalText(event, "capture_session_id", 36),
                instant(event, "recorded_at"), text(event, "input_source", "capture runner", 80),
                text(event, "model_version", "unknown", 80),
                text(event, "rf_classification", "UNKNOWN", 32), number(event, "rf_probability"),
                number(event, "rf_threshold"), rfFlagged, text(event, "if_classification", "UNKNOWN", 32),
                number(event, "if_score"), number(event, "if_threshold"), ifFlagged,
                authentication.getName());
        return ResponseEntity.created(URI.create("/api/v1/platform/alerts/" + created.alert().id()))
                .body(created);
    }

    @GetMapping("/{id}")
    public AlertDetail get(@PathVariable long id) {
        return alerts.get(id);
    }

    @PatchMapping("/{id}/status")
    public AlertDetail changeStatus(@PathVariable long id, @Valid @RequestBody ChangeAlertStatusRequest request,
            Authentication authentication) {
        return alerts.changeStatus(id, request.status(), authentication.getName());
    }

    private Map<String, Object> findCapturePrediction(String id) {
        try {
            Map<String, Object> response = aiEngine.get().uri("/api/v1/demo/events?limit=250")
                    .retrieve().body(new ParameterizedTypeReference<>() {});
            if (response == null || !(response.get("events") instanceof List<?> events)) {
                throw new ResponseStatusException(HttpStatus.BAD_GATEWAY,
                        "Capture history returned an unexpected response.");
            }
            for (Object value : events) {
                if (value instanceof Map<?, ?> event && id.equals(event.get("id"))
                        && Boolean.FALSE.equals(event.get("simulated"))) {
                    Map<String, Object> result = new java.util.LinkedHashMap<>();
                    event.forEach((key, field) -> {
                        if (key instanceof String name) result.put(name, field);
                    });
                    return result;
                }
            }
            throw new ResponseStatusException(HttpStatus.NOT_FOUND,
                    "Capture prediction was not found in recent history.");
        } catch (ResponseStatusException exception) {
            throw exception;
        } catch (RestClientException exception) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY,
                    "Capture history is unavailable; retry after checking the AI engine.");
        }
    }

    private static String text(Map<String, Object> event, String key, String fallback, int maxLength) {
        Object value = event.get(key);
        if (!(value instanceof String text) || text.isBlank()) return fallback;
        if (text.length() > maxLength) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Capture history returned an oversized field.");
        }
        return text;
    }

    private static String optionalText(Map<String, Object> event, String key, int maxLength) {
        Object value = event.get(key);
        if (!(value instanceof String text) || text.isBlank()) return null;
        if (text.length() > maxLength) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Capture history returned an oversized field.");
        }
        return text;
    }

    private static Instant instant(Map<String, Object> event, String key) {
        Object value = event.get(key);
        if (value instanceof String text) {
            try {
                return Instant.parse(text);
            } catch (DateTimeParseException ignored) {
                // Report a safe upstream error instead of accepting a malformed timestamp.
            }
        }
        throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Capture history returned an invalid timestamp.");
    }

    private static double number(Map<String, Object> event, String key) {
        Object value = event.get(key);
        if (value instanceof Number number && Double.isFinite(number.doubleValue())) return number.doubleValue();
        throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Capture history omitted a numeric model field.");
    }

    private static boolean bool(Map<String, Object> event, String key) {
        Object value = event.get(key);
        if (value instanceof Boolean result) return result;
        throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Capture history omitted a model flag.");
    }
}
