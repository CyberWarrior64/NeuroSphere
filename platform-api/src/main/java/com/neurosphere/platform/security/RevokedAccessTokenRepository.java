package com.neurosphere.platform.security;
import java.time.Instant;
import org.springframework.data.jpa.repository.JpaRepository;
public interface RevokedAccessTokenRepository extends JpaRepository<RevokedAccessToken, String> {
    int deleteAllByExpiresAtBefore(Instant instant);
}
