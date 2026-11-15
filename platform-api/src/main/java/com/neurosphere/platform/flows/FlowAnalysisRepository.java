package com.neurosphere.platform.flows;

import java.util.List;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface FlowAnalysisRepository extends JpaRepository<FlowAnalysisRecord, Long> {
    List<FlowAnalysisRecord> findAllByOrderByAnalyzedAtDesc(Pageable pageable);
}
