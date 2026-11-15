package com.neurosphere.platform.alerts;

import java.util.List;

public record AlertDetail(AlertSummary alert, List<AlertActivitySummary> activity) {}
