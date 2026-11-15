package com.neurosphere.platform.cases;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record CreateCaseRequest(
        @NotBlank @Size(max = 160) String title,
        @NotBlank @Size(max = 4000) String description,
        @NotNull PlatformCasePriority priority,
        @Pattern(regexp = "MANUAL|CAPTURE_PREDICTION") String sourceType,
        @Size(max = 128) String sourceReference) {}
