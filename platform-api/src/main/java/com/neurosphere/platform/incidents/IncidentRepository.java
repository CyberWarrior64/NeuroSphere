package com.neurosphere.platform.incidents;

import java.util.List;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IncidentRepository extends JpaRepository<IncidentRecord, Long> {
    List<IncidentRecord> findAllByOrderByUpdatedAtDesc(Pageable pageable);
    List<IncidentRecord> findAllByStatusOrderByUpdatedAtDesc(PlatformIncidentStatus status, Pageable pageable);
}
