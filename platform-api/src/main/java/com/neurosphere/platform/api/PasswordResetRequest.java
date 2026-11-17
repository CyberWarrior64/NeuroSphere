package com.neurosphere.platform.api;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record PasswordResetRequest(
        @NotBlank @Pattern(regexp = "(?i)^[a-f0-9]{64}$") String recoveryCode,
        @NotBlank @Size(min = 16, max = 128) String newPassword) {}
