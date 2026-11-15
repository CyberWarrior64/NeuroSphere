# NeuroSphere Platform API (Phase 1 slice)

This is a separate Java 21 / Spring Boot 3.5.16 service. It adds an authenticated platform boundary and proxies flow analysis to the existing Python AI engine. It does not replace ai-engine. It persists successful flow-analysis result metadata and authenticated analyst case records; raw flow features are not stored.

## API

- `POST /api/v1/auth/login` — public username/password login. Returns `access_token`, `token_type`, `expires_in` (900 seconds), and `roles`.
- `POST /api/v1/auth/logout` — authenticated; revokes the presented access token immediately. Returns 204.
- `GET /api/v1/platform/status` — public readiness probe; checks MySQL with `SELECT 1` and returns 503 if the database is unavailable.
- `GET /api/v1/platform/health` — bearer token required.
- `GET /api/v1/platform/me` — bearer token required; returns the authenticated username and roles.
- `GET /api/v1/platform/admin/health` — requires `ADMIN`.
- POST /api/v1/platform/flows/analyze — bearer token required; requires exactly 67 feature keys, forwards the record to the configured AI engine, and stores model result metadata. Do not send personal or production-sensitive records to the research model.
- GET /api/v1/platform/flows/recent?limit=10 — bearer token required; returns up to 50 recent result summaries without raw feature values.
- GET /api/v1/platform/cases?limit=50&status=OPEN — bearer token required; returns up to 100 recent case summaries.
- POST /api/v1/platform/cases — bearer token required; opens a manually reviewed case and writes its initial activity event.
- GET /api/v1/platform/cases/{id} — bearer token required; returns the case and its activity history.
- PATCH /api/v1/platform/cases/{id}/status — bearer token required; changes lifecycle status and records the transition.
- POST /api/v1/platform/cases/{id}/notes — bearer token required; appends an analyst note to the activity history.

Invalid credentials return the same 401 message. Access tokens use HS256, include issuer, expiry, and unique token ID claims, and last 15 minutes. Logout records the token ID until expiry; subsequent requests with that token return 401. There are no refresh tokens.

## Configuration

The service requires a MySQL URL, username, password, and a base64 JWT signing key decoding to at least 32 random bytes. No application credentials or signing key are shipped.

Required environment:

- `NS_DB_URL` — e.g. `jdbc:mysql://127.0.0.1:3306/neurosphere_platform?serverTimezone=UTC`
- `NS_DB_USERNAME`
- `NS_DB_PASSWORD`
- `NS_JWT_SECRET_BASE64`
- Optional: `NS_PLATFORM_PORT` (8081), `NS_BIND_ADDRESS` (127.0.0.1), `NS_AI_ENGINE_URL` (127.0.0.1:8000), `NS_CORS_ALLOWED_ORIGINS` (127.0.0.1:8765 and localhost:5173)

Generate a signing secret outside source control, for example with `openssl rand -base64 48`, then inject it via the environment or a secrets manager. Do not commit the value.

An initial admin account is created only if both `NS_BOOTSTRAP_USERNAME` and `NS_BOOTSTRAP_PASSWORD` are supplied and the user table is empty. The username must be 3–64 lowercase letters, digits, dot, underscore, or hyphen; the password must be at least 16 characters. The password is stored as BCrypt. Remove the bootstrap variables after the first start.

Flyway owns schema changes; Hibernate validates the MySQL schema. The service listens on loopback by default. Keep it behind the existing SSH tunnel; do not publish it to a public interface.

## Build and test

On a machine with Docker, run tests from the platform-api directory:

    docker run --rm -v "$PWD":/workspace -w /workspace maven:3.9.9-eclipse-temurin-21 mvn -B test

Before starting the local Ubuntu Compose stack, package the JAR from the project root:

    docker run --rm -v "$PWD/platform-api:/workspace" -w /workspace maven:3.9.9-eclipse-temurin-21 mvn -B -DskipTests package

Compose mounts platform-api/target/platform-api-0.1.0.jar read-only and runs it from the Maven/Temurin image, avoiding a separate API image build. The Compose service uses Linux host networking, keeps the app bound to 127.0.0.1, and reaches the existing AI engine and loopback-published MySQL port. Do not run the service with missing DB/JWT configuration. This host-network setup is specific to Linux, not Docker Desktop on Windows/macOS.

The existing integration tests use H2 and a test-only signing secret. The 12 tests cover login/security behavior, token revocation, protected history reads, and score-only analysis metadata against a mocked AI response; they predate the case-management feature and do not cover its endpoints or connect to production MySQL/AI. The current case-management package was compiled with tests skipped.

## Current boundary

This slice provides authentication, migration-backed users and flow-result history, an authenticated AI proxy, and shared MySQL-backed cases with activity history. The React dashboard uses the platform session for flow submissions and case management. It does not include user registration, password reset, account recovery, refresh tokens, formal retention, a general authentication audit log, tenant isolation, incident/alert workflows, or production deployment.
