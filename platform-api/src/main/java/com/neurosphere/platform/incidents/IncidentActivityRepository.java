package com.neurosphere.platform.incidents;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IncidentActivityRepository extends JpaRepository<IncidentActivity, Long> {
    List<IncidentActivity> findAllByIncident_IdOrderByCreatedAtAsc(Long incidentId);
}
