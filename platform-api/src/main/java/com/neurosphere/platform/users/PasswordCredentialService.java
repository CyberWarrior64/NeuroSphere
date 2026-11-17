package com.neurosphere.platform.users;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.HexFormat;
import java.util.Locale;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class PasswordCredentialService {
    private static final String INVALID_RECOVERY_CODE = "Recovery code is invalid or expired.";
    private final PlatformUserRepository users;
    private final PlatformPasswordResetTokenRepository resetTokens;
    private final PasswordEncoder passwords;

    public PasswordCredentialService(PlatformUserRepository users,
                                     PlatformPasswordResetTokenRepository resetTokens,
                                     PasswordEncoder passwords) {
        this.users = users;
        this.resetTokens = resetTokens;
        this.passwords = passwords;
    }

    @Transactional
    public void changePassword(String username, String currentPassword, String newPassword) {
        PlatformUser user = users.findByUsername(username.trim().toLowerCase(Locale.ROOT))
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED));
        if (!passwords.matches(currentPassword, user.getPasswordHash())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Current password is incorrect.");
        }
        if (passwords.matches(newPassword, user.getPasswordHash())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Choose a different new password.");
        }
        user.setPasswordHash(passwords.encode(newPassword));
        user.incrementCredentialVersion();
    }

    @Transactional
    public void resetPassword(String recoveryCode, String newPassword) {
        String tokenHash = sha256(recoveryCode.toLowerCase(Locale.ROOT));
        PlatformPasswordResetToken token = resetTokens.findByTokenHashForUpdate(tokenHash)
                .orElseThrow(this::invalidRecoveryCode);
        if (!token.getExpiresAt().isAfter(Instant.now())) {
            throw invalidRecoveryCode();
        }
        PlatformUser user = users.findById(token.getUserId())
                .filter(PlatformUser::isEnabled)
                .orElseThrow(this::invalidRecoveryCode);
        user.setPasswordHash(passwords.encode(newPassword));
        user.incrementCredentialVersion();
        resetTokens.delete(token);
    }

    private ResponseStatusException invalidRecoveryCode() {
        return new ResponseStatusException(HttpStatus.BAD_REQUEST, INVALID_RECOVERY_CODE);
    }

    private String sha256(String value) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 is unavailable.", exception);
        }
    }
}
