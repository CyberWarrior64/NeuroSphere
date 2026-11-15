package com.neurosphere.platform.api;

import com.neurosphere.platform.flows.FlowAnalysisRecord;
import com.neurosphere.platform.flows.FlowAnalysisRepository;
import com.neurosphere.platform.flows.FlowAnalysisSummary;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/v1/platform/flows")
public class AiDetectionController {
    private static final Logger log = LoggerFactory.getLogger(AiDetectionController.class);
    private final RestClient aiEngine;
    private final FlowAnalysisRepository analyses;

    public AiDetectionController(RestClient aiEngine, FlowAnalysisRepository analyses) {
        this.aiEngine = aiEngine;
        this.analyses = analyses;
    }

    @PostMapping("/analyze")
    public Map<String, Object> analyze(@RequestBody Map<String, Object> features, Authentication authentication) {
        if (features.size() != 67 || features.keySet().stream().anyMatch(String::isBlank)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
                    "Expected exactly 67 named CIC-IDS2017 features.");
        }
        try {
            Map<String, Object> result = aiEngine.post()
                    .uri("/api/v1/detect/v2")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(features)
                    .retrieve()
                    .body(new ParameterizedTypeReference<>() {});
            if (result == null) {
                throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "AI engine returned an empty response.");
            }
            Map<String, Object> detection = map(result, "detection");
            Map<String, Object> rf = map(detection, "random_forest");
            Map<String, Object> isolation = map(detection, "isolation_forest");
            Map<String, Object> risk = map(result, "risk_assessment");
            Instant analyzedAt = Instant.now();
            String modelVersion = text(result, "model_version");
            FlowAnalysisRecord saved = analyses.save(new FlowAnalysisRecord(
                    authentication.getName(), analyzedAt, modelVersion,
                    text(rf, "classification"), number(rf, "attack_probability"), bool(rf, "flagged"),
                    text(isolation, "classification"), number(isolation, "anomaly_score"), bool(isolation, "flagged"),
                    text(risk, "detector_agreement")));
            Map<String, Object> response = new LinkedHashMap<>(result);
            response.put("analysis_id", saved.getId());
            response.put("analyzed_at", analyzedAt.toString());
            return response;
        } catch (ResponseStatusException exception) {
            throw exception;
        } catch (RestClientResponseException exception) {
            String responseBody = exception.getResponseBodyAsString();
            log.warn("AI engine returned HTTP {}: {}", exception.getStatusCode().value(),
                    responseBody.substring(0, Math.min(responseBody.length(), 500)));
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY,
                    "AI engine rejected the flow request; check the feature schema and service logs.");
        } catch (RestClientException exception) {
            log.warn("AI engine request failed: {}", exception.getClass().getSimpleName());
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY,
                    "AI engine is unavailable; retry after checking service health.");
        }
    }

    @GetMapping("/recent")
    public List<FlowAnalysisSummary> recent(@RequestParam(defaultValue = "10") int limit) {
        int boundedLimit = Math.max(1, Math.min(limit, 50));
        return analyses.findAllByOrderByAnalyzedAtDesc(PageRequest.of(0, boundedLimit)).stream()
                .map(FlowAnalysisSummary::from)
                .toList();
    }

    private static Map<String, Object> map(Map<String, Object> source, String key) {
        Object value = source.get(key);
        if (!(value instanceof Map<?, ?> values)) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "AI engine response was missing detection data.");
        }
        Map<String, Object> converted = new LinkedHashMap<>();
        values.forEach((field, fieldValue) -> {
            if (field instanceof String name) converted.put(name, fieldValue);
        });
        return converted;
    }

    private static String text(Map<String, Object> source, String key) {
        Object value = source.get(key);
        if (value instanceof String text && !text.isBlank()) return text;
        throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "AI engine response was missing a text field.");
    }

    private static double number(Map<String, Object> source, String key) {
        Object value = source.get(key);
        if (value instanceof Number number && Double.isFinite(number.doubleValue())) return number.doubleValue();
        throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "AI engine response was missing a numeric field.");
    }

    private static boolean bool(Map<String, Object> source, String key) {
        Object value = source.get(key);
        if (value instanceof Boolean result) return result;
        throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "AI engine response was missing a boolean field.");
    }
}
