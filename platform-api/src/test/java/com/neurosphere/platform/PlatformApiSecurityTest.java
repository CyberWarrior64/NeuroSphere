package com.neurosphere.platform;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.neurosphere.platform.flows.FlowAnalysisRecord;
import com.neurosphere.platform.flows.FlowAnalysisRepository;
import com.neurosphere.platform.users.PlatformPasswordResetToken;
import com.neurosphere.platform.users.PlatformPasswordResetTokenRepository;
import com.neurosphere.platform.users.PlatformUser;
import com.neurosphere.platform.users.PlatformUserRepository;
import java.time.Instant;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class PlatformApiSecurityTest {
    @Autowired MockMvc mvc;
    @Autowired PlatformUserRepository users;
    @Autowired PlatformPasswordResetTokenRepository resetTokens;
    @Autowired FlowAnalysisRepository analyses;
    @Autowired PasswordEncoder passwords;
    @Autowired JwtEncoder jwtEncoder;

    @BeforeEach
    void seedUsers() {
        resetTokens.deleteAll();
        users.deleteAll();
        users.save(new PlatformUser("analyst", passwords.encode("correct horse battery"), Set.of("ANALYST")));
        users.save(new PlatformUser("admin", passwords.encode("correct horse battery"), Set.of("ADMIN")));
    }

    @Test
    void protectedRoutesRejectAnonymousCalls() throws Exception {
        mvc.perform(get("/api/v1/platform/me")).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/v1/auth/logout")).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/v1/platform/admin/health")).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/v1/platform/flows/recent")).andExpect(status().isUnauthorized());
    }

    @Test
    void loginIssuesShortLivedBearerTokenAndProfileWorks() throws Exception {
        String token = login("analyst", "correct horse battery");
        mvc.perform(get("/api/v1/platform/me").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.username").value("analyst"))
                .andExpect(jsonPath("$.roles[0]").value("ANALYST"));
        mvc.perform(get("/api/v1/platform/admin/health").header("Authorization", "Bearer " + token))
                .andExpect(status().isForbidden());
    }

    @Test
    void logoutRevokesOnlyThePresentedToken() throws Exception {
        String token = login("analyst", "correct horse battery");
        String otherToken = login("analyst", "correct horse battery");
        mvc.perform(get("/api/v1/platform/me").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk());
        mvc.perform(post("/api/v1/auth/logout").header("Authorization", "Bearer " + token))
                .andExpect(status().isNoContent());
        mvc.perform(get("/api/v1/platform/me").header("Authorization", "Bearer " + token))
                .andExpect(status().isUnauthorized());
        mvc.perform(get("/api/v1/platform/me").header("Authorization", "Bearer " + otherToken))
                .andExpect(status().isOk());
    }

    @Test
    void passwordChangeVerifiesCurrentPasswordAndInvalidatesAllSessionsForThatUser() throws Exception {
        String firstToken = login("analyst", "correct horse battery");
        String secondToken = login("analyst", "correct horse battery");
        String adminToken = login("admin", "correct horse battery");
        mvc.perform(post("/api/v1/auth/change-password")
                        .header("Authorization", "Bearer " + firstToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"currentPassword\":\"wrong password\",\"newPassword\":\"a much longer replacement phrase\"}"))
                .andExpect(status().isBadRequest());
        mvc.perform(post("/api/v1/auth/change-password")
                        .header("Authorization", "Bearer " + firstToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"currentPassword\":\"correct horse battery\",\"newPassword\":\"a much longer replacement phrase\"}"))
                .andExpect(status().isNoContent());
        mvc.perform(get("/api/v1/platform/me").header("Authorization", "Bearer " + firstToken))
                .andExpect(status().isUnauthorized());
        mvc.perform(get("/api/v1/platform/me").header("Authorization", "Bearer " + secondToken))
                .andExpect(status().isUnauthorized());
        mvc.perform(get("/api/v1/platform/me").header("Authorization", "Bearer " + adminToken))
                .andExpect(status().isOk());
        String newToken = login("analyst", "a much longer replacement phrase");
        mvc.perform(get("/api/v1/platform/me").header("Authorization", "Bearer " + newToken))
                .andExpect(status().isOk());
    }

    @Test
    void oneTimeRecoveryCodeResetsPasswordAndCannotBeReused() throws Exception {
        String previousToken = login("analyst", "correct horse battery");
        String recoveryCode = "ab".repeat(32);
        PlatformUser analyst = users.findByUsername("analyst").orElseThrow();
        resetTokens.save(new PlatformPasswordResetToken(sha256(recoveryCode), analyst.getId(), Instant.now().plusSeconds(1800)));

        mvc.perform(post("/api/v1/auth/password-reset")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"recoveryCode\":\"" + recoveryCode + "\",\"newPassword\":\"new recovery password phrase\"}"))
                .andExpect(status().isNoContent());
        mvc.perform(get("/api/v1/platform/me").header("Authorization", "Bearer " + previousToken))
                .andExpect(status().isUnauthorized());
        mvc.perform(post("/api/v1/auth/password-reset")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"recoveryCode\":\"" + recoveryCode + "\",\"newPassword\":\"another replacement password\"}"))
                .andExpect(status().isBadRequest());
        String newToken = login("analyst", "new recovery password phrase");
        mvc.perform(get("/api/v1/platform/me").header("Authorization", "Bearer " + newToken))
                .andExpect(status().isOk());
    }

    @Test
    void adminRoleCanAccessAdminRoute() throws Exception {
        String token = login("admin", "correct horse battery");
        mvc.perform(get("/api/v1/platform/admin/health").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.scope").value("admin"));
    }

    @Test
    void authenticatedAnalystCanReadStoredFlowMetadata() throws Exception {
        FlowAnalysisRecord record = analyses.save(new FlowAnalysisRecord(
                "analyst", Instant.now(), "Hybrid V2", "NORMAL", 0.12, false,
                "ANOMALOUS", 0.62, true, "DETECTORS_DISAGREE"));
        String token = login("analyst", "correct horse battery");
        mvc.perform(get("/api/v1/platform/flows/recent").param("limit", "8")
                        .header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].id").value(record.getId()))
                .andExpect(jsonPath("$[0].submittedBy").value("analyst"))
                .andExpect(jsonPath("$[0].rfAttackProbability").value(0.12))
                .andExpect(jsonPath("$[0].ifFlagged").value(true))
                .andExpect(jsonPath("$[0].features").doesNotExist());
    }

    @Test
    void authenticatedUnsupportedMethodPreservesMethodNotAllowedStatus() throws Exception {
        String token = login("analyst", "correct horse battery");
        mvc.perform(post("/api/v1/platform/me").header("Authorization", "Bearer " + token))
                .andExpect(status().isMethodNotAllowed());
    }

    @Test
    void badCredentialsUseSameUnauthorizedResponse() throws Exception {
        String unknown = mvc.perform(post("/api/v1/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"missing\",\"password\":\"wrong\"}"))
                .andExpect(status().isUnauthorized())
                .andReturn().getResponse().getErrorMessage();
        String wrongPassword = mvc.perform(post("/api/v1/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"analyst\",\"password\":\"wrong\"}"))
                .andExpect(status().isUnauthorized())
                .andReturn().getResponse().getErrorMessage();
        org.junit.jupiter.api.Assertions.assertEquals("Invalid username or password.", unknown);
        org.junit.jupiter.api.Assertions.assertEquals(unknown, wrongPassword);
    }

    @Test
    void decoderRejectsTokenFromAnotherIssuer() throws Exception {
        Instant now = Instant.now();
        JwtClaimsSet claims = JwtClaimsSet.builder()
                .issuer("untrusted-issuer")
                .subject("admin")
                .issuedAt(now)
                .expiresAt(now.plusSeconds(900))
                .claim("roles", java.util.List.of("ADMIN"))
                .build();
        String token = jwtEncoder.encode(JwtEncoderParameters.from(
                JwsHeader.with(MacAlgorithm.HS256).build(), claims)).getTokenValue();
        mvc.perform(get("/api/v1/platform/me").header("Authorization", "Bearer " + token))
                .andExpect(status().isUnauthorized());
    }

    private String login(String username, String password) throws Exception {
        String response = mvc.perform(post("/api/v1/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"" + username + "\",\"password\":\"" + password + "\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.token_type").value("Bearer"))
                .andExpect(jsonPath("$.expires_in").value(900))
                .andExpect(jsonPath("$.roles[0]").exists())
                .andReturn().getResponse().getContentAsString();
        return new com.fasterxml.jackson.databind.ObjectMapper().readTree(response).get("access_token").asText();
    }

    private String sha256(String value) throws NoSuchAlgorithmException {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                .digest(value.getBytes(StandardCharsets.UTF_8)));
    }
}
