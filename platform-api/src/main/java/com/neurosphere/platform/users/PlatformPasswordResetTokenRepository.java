package com.neurosphere.platform.users;

import jakarta.persistence.LockModeType;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface PlatformPasswordResetTokenRepository
        extends JpaRepository<PlatformPasswordResetToken, String> {
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select token from PlatformPasswordResetToken token where token.tokenHash = :tokenHash")
    Optional<PlatformPasswordResetToken> findByTokenHashForUpdate(@Param("tokenHash") String tokenHash);

    void deleteAllByUserId(Long userId);
}
