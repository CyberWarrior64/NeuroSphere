package com.neurosphere.platform.api;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.springframework.dao.DataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/platform")
public class PlatformController {
    private final JdbcTemplate jdbc;

    public PlatformController(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @GetMapping("/status")
    public ResponseEntity<Map<String, String>> status() {
        try {
            jdbc.queryForObject("SELECT 1", Integer.class);
            return ResponseEntity.ok(Map.of("status", "healthy", "service", "neurosphere-platform-api", "database", "connected"));
        } catch (DataAccessException exception) {
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                    .body(Map.of("status", "unavailable", "service", "neurosphere-platform-api", "database", "unavailable"));
        }
    }

    @GetMapping("/health")
    public Map<String, Object> health() {
        return Map.of("status", "healthy", "service", "neurosphere-platform-api", "time", Instant.now().toString());
    }

    @GetMapping("/me")
    public Map<String, Object> me(Authentication authentication) {
        List<String> roles = authentication.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .map(authority -> authority.replaceFirst("^ROLE_", ""))
                .sorted()
                .toList();
        return Map.of("username", authentication.getName(), "roles", roles);
    }

    @GetMapping("/admin/health")
    public Map<String, Object> adminHealth() {
        return Map.of("status", "healthy", "scope", "admin");
    }
}
