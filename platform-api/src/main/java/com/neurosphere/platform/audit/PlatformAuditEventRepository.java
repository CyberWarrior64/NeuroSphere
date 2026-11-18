package com.neurosphere.platform.audit;

import java.util.List;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PlatformAuditEventRepository extends JpaRepository<PlatformAuditEvent, Long> {
    List<PlatformAuditEvent> findAllByOrderByOccurredAtDescIdDesc(Pageable pageable);
}
