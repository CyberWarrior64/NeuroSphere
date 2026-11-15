package com.neurosphere.platform.cases;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CaseActivityRepository extends JpaRepository<CaseActivity, Long> {
    List<CaseActivity> findAllByCaseRecord_IdOrderByCreatedAtAsc(Long caseId);
}
