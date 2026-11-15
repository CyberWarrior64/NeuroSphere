package com.neurosphere.platform.security;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;
import java.time.Instant;
@Entity
@Table(name = "revoked_access_tokens", indexes = {
        @Index(name = "idx_revoked_access_tokens_expires_at", columnList = "expires_at")
})
public class RevokedAccessToken {
    @Id
    @Column(name = "jti", length = 36, nullable = false)
    private String jti;
    @Column(name = "expires_at", nullable = false)
    private Instant expiresAt;
    protected RevokedAccessToken() {}
    public RevokedAccessToken(String jti, Instant expiresAt) { this.jti = jti; this.expiresAt = expiresAt; }
    public String getJti() { return jti; }
    public Instant getExpiresAt() { return expiresAt; }
}
