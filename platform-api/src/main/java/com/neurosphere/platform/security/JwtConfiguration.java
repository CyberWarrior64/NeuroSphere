package com.neurosphere.platform.security;

import com.neurosphere.platform.users.PlatformUser;
import com.neurosphere.platform.users.PlatformUserRepository;
import com.nimbusds.jose.jwk.source.ImmutableSecret;
import org.springframework.security.oauth2.core.OAuth2Error;
import org.springframework.security.oauth2.core.OAuth2TokenValidator;
import org.springframework.security.oauth2.core.DelegatingOAuth2TokenValidator;
import org.springframework.security.oauth2.jwt.Jwt;
import java.util.Base64;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtValidators;
import org.springframework.security.oauth2.jwt.NimbusJwtEncoder;

@Configuration
public class JwtConfiguration {
    @Bean
    SecretKey jwtSecretKey(@Value("${neurosphere.jwt.secret-base64}") String secretBase64) {
        if (secretBase64 == null || secretBase64.isBlank()) {
            throw new IllegalStateException("NS_JWT_SECRET_BASE64 is required.");
        }
        final byte[] secret;
        try {
            secret = Base64.getDecoder().decode(secretBase64);
        } catch (IllegalArgumentException ex) {
            throw new IllegalStateException("NS_JWT_SECRET_BASE64 must be valid Base64.", ex);
        }
        if (secret.length < 32) {
            throw new IllegalStateException("NS_JWT_SECRET_BASE64 must decode to at least 32 bytes.");
        }
        return new SecretKeySpec(secret, "HmacSHA256");
    }

    @Bean
    JwtEncoder jwtEncoder(SecretKey jwtSecretKey) {
        return new NimbusJwtEncoder(new ImmutableSecret<>(jwtSecretKey));
    }

    @Bean
    JwtDecoder jwtDecoder(
            SecretKey jwtSecretKey,
            @Value("${neurosphere.jwt.issuer}") String issuer,
            TokenRevocationService revocations,
            PlatformUserRepository users) {
        var decoder = org.springframework.security.oauth2.jwt.NimbusJwtDecoder
                .withSecretKey(jwtSecretKey)
                .macAlgorithm(MacAlgorithm.HS256)
                .build();
        OAuth2TokenValidator<Jwt> issuerAndTime = JwtValidators.createDefaultWithIssuer(issuer);
        OAuth2TokenValidator<Jwt> revocation = jwt -> {
            if (jwt.getId() == null || jwt.getId().isBlank()) {
                return org.springframework.security.oauth2.core.OAuth2TokenValidatorResult.failure(
                        new OAuth2Error("invalid_token", "Token identifier is missing.", null));
            }
            if (revocations.isRevoked(jwt.getId())) {
                return org.springframework.security.oauth2.core.OAuth2TokenValidatorResult.failure(
                        new OAuth2Error("invalid_token", "Token has been revoked.", null));
            }
            return org.springframework.security.oauth2.core.OAuth2TokenValidatorResult.success();
        };
        OAuth2TokenValidator<Jwt> credentialVersion = jwt -> {
            Object tokenVersionClaim = jwt.getClaims().get("credential_version");
            PlatformUser user = jwt.getSubject() == null ? null
                    : users.findByUsername(jwt.getSubject()).orElse(null);
            boolean versionMatches = user != null && tokenVersionClaim instanceof Number tokenVersion
                    && tokenVersion.intValue() == user.getCredentialVersion();
            if (user == null || !user.isEnabled() || !versionMatches) {
                return org.springframework.security.oauth2.core.OAuth2TokenValidatorResult.failure(
                        new OAuth2Error("invalid_token", "Credentials have changed.", null));
            }
            return org.springframework.security.oauth2.core.OAuth2TokenValidatorResult.success();
        };
        decoder.setJwtValidator(new DelegatingOAuth2TokenValidator<>(issuerAndTime, revocation, credentialVersion));
        return decoder;
    }
}
