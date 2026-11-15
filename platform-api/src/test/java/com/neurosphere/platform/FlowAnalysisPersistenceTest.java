package com.neurosphere.platform;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.neurosphere.platform.api.AiDetectionController;
import com.neurosphere.platform.flows.FlowAnalysisRecord;
import com.neurosphere.platform.flows.FlowAnalysisRepository;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.TestingAuthenticationToken;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

@SpringBootTest
@ActiveProfiles("test")
class FlowAnalysisPersistenceTest {
    @Autowired FlowAnalysisRepository analyses;

    @Test
    void successfulAnalysisPersistsOnlyScoresAndReturnsRecordId() {
        String responseJson = """
                {"model_version":"Hybrid V2","detection":{
                  "random_forest":{"classification":"NORMAL","attack_probability":0.12,"flagged":false},
                  "isolation_forest":{"classification":"ANOMALOUS","anomaly_score":0.62,"flagged":true}},
                 "risk_assessment":{"detector_agreement":"DETECTORS_DISAGREE"}}
                """;
        RestClient.Builder builder = RestClient.builder().baseUrl("http://ai-engine.test");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("http://ai-engine.test/api/v1/detect/v2"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
                .andRespond(withSuccess(responseJson, MediaType.APPLICATION_JSON));

        Map<String, Object> features = new LinkedHashMap<>();
        for (int index = 0; index < 67; index++) features.put("feature-" + index, 0.0);
        Map<String, Object> response = new AiDetectionController(builder.build(), analyses)
                .analyze(features, new TestingAuthenticationToken("persistence-test-analyst", "unused", "ROLE_ANALYST"));

        assertNotNull(response.get("analysis_id"));
        assertNotNull(response.get("analyzed_at"));
        List<FlowAnalysisRecord> saved = analyses.findAll().stream()
                .filter(record -> record.getSubmittedBy().equals("persistence-test-analyst"))
                .toList();
        assertEquals(1, saved.size());
        assertEquals(0.12, saved.get(0).getRfAttackProbability());
        assertEquals(0.62, saved.get(0).getIfAnomalyScore());
        assertEquals("DETECTORS_DISAGREE", saved.get(0).getDetectorAgreement());
        server.verify();
    }
}
