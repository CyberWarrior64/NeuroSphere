package com.neurosphere.platform.incidents;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IncidentAlertLinkRepository extends JpaRepository<IncidentAlertLink, Long> {
    List<IncidentAlertLink> findAllByIncident_IdOrderByLinkedAtAsc(Long incidentId);
    boolean existsByIncident_IdAndAlert_Id(Long incidentId, Long alertId);
}
