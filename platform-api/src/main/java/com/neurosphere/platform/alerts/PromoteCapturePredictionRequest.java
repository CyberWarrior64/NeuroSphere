package com.neurosphere.platform.alerts;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record PromoteCapturePredictionRequest(
        @NotBlank @Size(max = 160) String title,
        @NotBlank @Size(max = 2000) String analystRationale,
        @NotNull PlatformAlertSeverity severity) {}
