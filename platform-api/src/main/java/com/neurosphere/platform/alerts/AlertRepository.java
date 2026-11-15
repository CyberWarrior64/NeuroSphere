package com.neurosphere.platform.alerts;

import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AlertRepository extends JpaRepository<AlertRecord, Long> {
    List<AlertRecord> findAllByOrderByCreatedAtDesc(Pageable pageable);
    List<AlertRecord> findAllByStatusOrderByCreatedAtDesc(PlatformAlertStatus status, Pageable pageable);
    Optional<AlertRecord> findBySourceReference(String sourceReference);
}
