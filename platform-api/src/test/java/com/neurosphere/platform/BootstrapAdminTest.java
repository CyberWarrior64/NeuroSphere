package com.neurosphere.platform;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.neurosphere.platform.users.BootstrapAdmin;
import com.neurosphere.platform.users.PlatformUser;
import com.neurosphere.platform.users.PlatformUserRepository;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.boot.DefaultApplicationArguments;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

class BootstrapAdminTest {
    private final PlatformUserRepository users = org.mockito.Mockito.mock(PlatformUserRepository.class);
    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder(4);

    @Test
    void bootstrapDoesNothingWithoutExplicitEnvironmentCredentials() throws Exception {
        new BootstrapAdmin(users, encoder, "", "").run(new DefaultApplicationArguments(new String[0]));
        verify(users, never()).count();
        verify(users, never()).saveAndFlush(any());
    }

    @Test
    void partialBootstrapConfigurationFailsClosed() {
        BootstrapAdmin bootstrap = new BootstrapAdmin(users, encoder, "admin", "");
        assertThrows(IllegalStateException.class,
                () -> bootstrap.run(new DefaultApplicationArguments(new String[0])));
        verify(users, never()).saveAndFlush(any());
    }

    @Test
    void createsOnlyHashedAdminWhenTableIsEmpty() throws Exception {
        when(users.count()).thenReturn(0L);
        String password = "very-long-test-password";
        BootstrapAdmin bootstrap = new BootstrapAdmin(users, encoder, "Admin.User", password);
        bootstrap.run(new DefaultApplicationArguments(new String[0]));

        ArgumentCaptor<PlatformUser> captor = ArgumentCaptor.forClass(PlatformUser.class);
        verify(users).saveAndFlush(captor.capture());
        PlatformUser created = captor.getValue();
        assertEquals("admin.user", created.getUsername());
        assertEquals(Set.of("ADMIN"), created.getRoles());
        org.junit.jupiter.api.Assertions.assertNotEquals(password, created.getPasswordHash());
        org.junit.jupiter.api.Assertions.assertTrue(encoder.matches(password, created.getPasswordHash()));
    }
}
