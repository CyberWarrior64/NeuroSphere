package com.neurosphere.platform.api;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/platform")
public class PlatformController {
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
