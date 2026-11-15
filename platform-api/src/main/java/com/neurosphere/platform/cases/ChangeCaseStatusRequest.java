package com.neurosphere.platform.cases;

import jakarta.validation.constraints.NotNull;

public record ChangeCaseStatusRequest(@NotNull PlatformCaseStatus status) {}
