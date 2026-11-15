package com.neurosphere.platform.users;

import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class BootstrapAdmin implements ApplicationRunner {
    private static final Pattern USERNAME = Pattern.compile("^[a-z0-9._-]{3,64}$");
    private final PlatformUserRepository users;
    private final PasswordEncoder passwordEncoder;
    private final String username;
    private final String password;

    public BootstrapAdmin(
            PlatformUserRepository users,
            PasswordEncoder passwordEncoder,
            @Value("${NS_BOOTSTRAP_USERNAME:}") String username,
            @Value("${NS_BOOTSTRAP_PASSWORD:}") String password) {
        this.users = users;
        this.passwordEncoder = passwordEncoder;
        this.username = username == null ? "" : username.trim().toLowerCase(Locale.ROOT);
        this.password = password == null ? "" : password;
    }

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        boolean hasUsername = !username.isBlank();
        boolean hasPassword = !password.isBlank();
        if (hasUsername != hasPassword) {
            throw new IllegalStateException(
                    "Set both NS_BOOTSTRAP_USERNAME and NS_BOOTSTRAP_PASSWORD, or leave both unset.");
        }
        if (!hasUsername) return;
        if (!USERNAME.matcher(username).matches()) {
            throw new IllegalStateException("Bootstrap username must be 3-64 lowercase letters, digits, dot, underscore, or hyphen.");
        }
        if (password.length() < 16) {
            throw new IllegalStateException("Bootstrap password must contain at least 16 characters.");
        }
        if (users.count() != 0) return;
        users.saveAndFlush(new PlatformUser(username, passwordEncoder.encode(password), Set.of("ADMIN")));
    }
}
