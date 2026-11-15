package com.neurosphere.platform.security;
import java.time.Instant;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
@Service
public class TokenRevocationService {
    private final RevokedAccessTokenRepository tokens;
    public TokenRevocationService(RevokedAccessTokenRepository tokens) { this.tokens = tokens; }
    @Transactional(readOnly = true)
    public boolean isRevoked(String tokenId) { return tokens.existsById(tokenId); }
    @Transactional
    public void revoke(String tokenId, Instant expiresAt) {
        if (tokenId == null || tokenId.isBlank() || expiresAt == null) {
            throw new IllegalArgumentException("Cannot revoke a token without an identifier and expiry.");
        }
        Instant now = Instant.now();
        tokens.deleteAllByExpiresAtBefore(now);
        if (expiresAt.isAfter(now)) tokens.save(new RevokedAccessToken(tokenId, expiresAt));
    }
}
