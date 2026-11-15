package com.neurosphere.platform.incidents;

import jakarta.validation.constraints.NotNull;

public record ChangeIncidentStatusRequest(@NotNull PlatformIncidentStatus status) {}
