package com.neurosphere.platform.alerts;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AlertActivityRepository extends JpaRepository<AlertActivity, Long> {
    List<AlertActivity> findAllByAlert_IdOrderByCreatedAtAsc(Long alertId);
}
