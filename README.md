# NeuroSphere V2

NeuroSphere currently has a research demo plus an early, optional Java platform API slice. It is not yet the complete seven-phase platform described in the target architecture.

## Current capabilities

- React SOC dashboard serves clearly labeled fictional simulation data alongside real AI and platform/database readiness status and model outputs. The browser preview is available at 127.0.0.1:8765 through the SSH tunnel.
- Authenticated flow analysis sends the 67-feature request through Spring Boot; the API calls the private FastAPI service and stores only model scores, classifications, flags, model version, timestamp, and submitting username in MySQL. Raw feature vectors are not retained.
- The live/PCAP capture runner processes traffic on Ubuntu and prints experimental model results. The separate metadata store keeps up to 1000 prediction records and displays the runner-reported capture mode without raw features, packet payloads, IP addresses, or interface names. The mode is client-reported, not independently attested; predictions are not alerts.
- The Spring Boot 3.5 / Java 21 platform API has JWT/RBAC login, Flyway migrations V1–V3, database-backed JWT logout revocation, an authenticated AI proxy, and protected recent-analysis history. Maven build and tests pass (12/12).
- MySQL and the platform API are running on the Ubuntu host. The AI launcher redirects temporary files to /mnt/neurosphere; the 16 GB root filesystem remains full, which can still block unrelated system builds or updates.
- A source-only Git checkpoint exists on the Ubuntu host on branch `main` (commit `c5fa200`). No remote is configured, so it is not an off-machine backup.

The existing FastAPI research demo remains unauthenticated and does not require the optional platform API. It is bound to loopback; do not expose it publicly.

## Run the dashboard demo

On the Ubuntu host:

    cd /mnt/neurosphere/NeuroSphere/ai-engine
    ./run-api.sh

From Windows PowerShell:

    ssh -N -L 8000:127.0.0.1:8000 -L 8765:127.0.0.1:8000 -L 8081:127.0.0.1:8081 cse-cy-02@100.70.85.104

Keep the tunnel open and browse to http://127.0.0.1:8765/.

To rebuild the React dashboard on the Ubuntu host, keep npm temporary files and its cache on the mounted data drive because the root filesystem is full:

    mkdir -p /mnt/neurosphere/tmp /mnt/neurosphere/npm-cache
    cd /mnt/neurosphere/NeuroSphere/frontend
    TMPDIR=/mnt/neurosphere/tmp npm_config_cache=/mnt/neurosphere/npm-cache npm run build

FastAPI serves the generated frontend/dist assets directly; no API restart is needed after a successful build.

## Platform API and MySQL on Ubuntu Linux

Host networking in Compose is Linux-specific. Run these commands on the Ubuntu machine, not Docker Desktop on Windows or macOS.

From the repository root, prepare a private environment file:

    cp infra/.env.example infra/.env
    chmod 600 infra/.env
    openssl rand -base64 48

Edit infra/.env. Set unique strong MYSQL_PASSWORD and MYSQL_ROOT_PASSWORD values, and set NS_JWT_SECRET_BASE64 to the generated random base64 value. Never commit or share infra/.env. The example values are placeholders, not usable credentials. The docker compose config command expands environment variables, so do not paste its rendered output into public logs or chats.

Optional first-start admin bootstrap requires setting both NS_BOOTSTRAP_USERNAME and NS_BOOTSTRAP_PASSWORD in infra/.env. The username must match the documented lowercase format and the password must be at least 16 characters. There are no default credentials. After the first admin is created, remove both variables and restart the service.

Package the platform API JAR from the project root before starting Compose:

    docker run --rm -v "$PWD/platform-api:/workspace" -w /workspace maven:3.9.9-eclipse-temurin-21 mvn -B -DskipTests package

The API container mounts this JAR read-only and runs it from the Maven/Temurin image; Compose does not build a separate API image. Validate and start the optional services:

    docker compose --env-file infra/.env -f infra/docker-compose.yml config -q
    docker compose --env-file infra/.env -f infra/docker-compose.yml up -d

The optional Java API listens on host loopback port 8081; MySQL listens on 127.0.0.1:3307. The API connects to the existing loopback FastAPI service. Flyway runs the user-table migration when the API starts with valid database and JWT configuration. Verify current service state with docker compose ps and docker compose logs; configuration validation alone does not prove the database migration or API startup.

Use infra/backup-mysql.sh to create a private compressed SQL backup under /mnt/neurosphere/backups/mysql. Restore with infra/restore-mysql.sh <backup.sql.gz>; it requires typing the exact RESTORE <database> confirmation and creates a fresh pre-restore backup first. Do not run restore unless intentionally replacing the database contents.

To reach both local-only HTTP services from Windows, use a dual-port SSH tunnel:

    ssh -N -L 8000:127.0.0.1:8000 -L 8765:127.0.0.1:8000 -L 8081:127.0.0.1:8081 cse-cy-02@100.70.85.104

The dashboard uses FastAPI for health and model metadata. Login, flow analysis, and saved analysis history use the authenticated platform API.

## Important limits

Simulation values are fictional and are not observed network events. Detection outputs are experimental research signals; exact feature parity with the training generator and generalization to independent traffic are unproven. Do not automate blocking or alert escalation.

The Java API is an early authentication/proxy slice. Production gaps include account recovery and refresh tokens, audit storage, durable alert/case workflows, managed collectors, digital twin, Cowrie deception analytics, RabbitMQ/WebSocket orchestration, response approvals, security review, restore/rollback rehearsal, and repeatable production deployment.

See [the demo runbook](docs/demo-runbook.md), [the phased roadmap](docs/development-roadmap.md), [the platform API notes](platform-api/README.md), and [architecture documents](docs/architecture/).
