package com.neurosphere.platform.cases;

import java.util.List;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CaseRepository extends JpaRepository<CaseRecord, Long> {
    List<CaseRecord> findAllByOrderByUpdatedAtDesc(Pageable pageable);
    List<CaseRecord> findAllByStatusOrderByUpdatedAtDesc(PlatformCaseStatus status, Pageable pageable);
}
