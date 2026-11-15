package com.neurosphere.platform.security;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.stereotype.Service;

@Service
public class JwtTokenService {
    private final JwtEncoder encoder;
    private final String issuer;
    private final long lifetimeMinutes;

    public JwtTokenService(
            JwtEncoder encoder,
            @Value("${neurosphere.jwt.issuer}") String issuer,
            @Value("${neurosphere.jwt.access-token-minutes}") long lifetimeMinutes) {
        if (lifetimeMinutes < 1 || lifetimeMinutes > 60) {
            throw new IllegalStateException("Access token lifetime must be between 1 and 60 minutes.");
        }
        this.encoder = encoder;
        this.issuer = issuer;
        this.lifetimeMinutes = lifetimeMinutes;
    }

    public String issue(String username, List<String> roles) {
        Instant now = Instant.now();
        JwtClaimsSet claims = JwtClaimsSet.builder()
                .issuer(issuer)
                .subject(username)
                .id(UUID.randomUUID().toString())
                .issuedAt(now)
                .expiresAt(now.plus(lifetimeMinutes, ChronoUnit.MINUTES))
                .claim("roles", roles)
                .build();
        JwsHeader header = JwsHeader.with(MacAlgorithm.HS256).build();
        return encoder.encode(JwtEncoderParameters.from(header, claims)).getTokenValue();
    }

    public long expiresInSeconds() {
        return lifetimeMinutes * 60;
    }
}
