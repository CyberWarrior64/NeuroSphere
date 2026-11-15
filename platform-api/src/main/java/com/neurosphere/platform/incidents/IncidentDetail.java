package com.neurosphere.platform.incidents;

import com.neurosphere.platform.alerts.AlertSummary;
import java.util.List;

public record IncidentDetail(IncidentSummary incident, List<IncidentActivitySummary> activity,
        List<AlertSummary> alerts) {}
