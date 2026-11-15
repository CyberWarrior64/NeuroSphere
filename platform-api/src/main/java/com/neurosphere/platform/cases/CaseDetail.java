package com.neurosphere.platform.cases;

import java.util.List;

public record CaseDetail(CaseSummary caseRecord, List<CaseActivitySummary> activity) {}
