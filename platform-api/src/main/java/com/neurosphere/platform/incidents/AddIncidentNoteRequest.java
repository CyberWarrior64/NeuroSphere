package com.neurosphere.platform.incidents;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record AddIncidentNoteRequest(@NotBlank @Size(max = 2000) String note) {}
