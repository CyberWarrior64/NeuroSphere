package com.neurosphere.platform.alerts;

import jakarta.validation.constraints.NotNull;

public record ChangeAlertStatusRequest(@NotNull PlatformAlertStatus status) {}
