# NeuroSphere V2 roadmap

## Current baseline

The shared project is a working research demo composed of a React SOC-style dashboard and a Python/FastAPI model service. The frontend is served by FastAPI on loopback. It is not yet the full target platform in the architecture documents.

Verified demo components:

- Dashboard built with React, Tailwind, React Router, Axios, Recharts, and Lucide.
- FastAPI health, GPU, model metadata, and flow detection routes.
- Hybrid V2 serves Random Forest and Isolation Forest outputs over the named 67-feature CIC-IDS2017 schema.
- Dashboard simulation mode displays fictional sample alerts, cases, inventory, severity counts, and illustrative paths. These remain explicitly labeled as simulated.
- Digital Twin Lab preview runs three deterministic scenarios over four virtual assets in-browser; it creates no live traffic, AI predictions, or response actions.
- Browser-submitted flow records reach the real model endpoint; outputs and short browser trend are session-only.
- Experimental Python packet capture / PCAP replay runner posts completed records to the CICFlowMeter adapter and prints output to the terminal.
- Capture-adapter predictions are recorded in bounded metadata-only local SQLite history (maximum 1000), exposed by GET /api/v1/demo/events. Raw feature vectors, IP addresses, and packet payloads are not stored.
- Alerts separates experimental predictions from analyst-reviewed alerts. An authenticated analyst can promote a recent flagged capture prediction after server-side lookup, selecting severity and rationale; status changes are stored with activity history. It is not automated incident confirmation.
- Incidents supports authenticated MySQL-backed manual incident records, links only to analyst-promoted review alerts, and stores status/note/link activity. The three fictional scenarios remain available in a separate demo tab; no automated response runs.
- Case Management uses authenticated Spring endpoints and MySQL migrations for manual case creation, status changes, and an append-only activity history. Model predictions are not automatically promoted to cases.
- SIEM Search and Reports pages read that existing history: Search filters up to 250 prediction summaries; Reports aggregates the same bounded window and exports CSV metadata. They do not represent a connected SIEM or alert/incident pipeline.
- Threat Intelligence reads the public Emerging Threats compromised-host IPv4 feed through FastAPI. It uses a bounded in-memory cache and shows source timestamps; this is analyst context only, not traffic correlation or blocking.
- The frontend production build completed successfully for the current FastAPI host.
- Java 21 / Spring Boot 3.5.16 provides login, JWT-protected routes, Flyway V1–V6, database-backed JWT logout revocation, a public database-readiness probe, an authenticated AI proxy, protected analysis history, authenticated case management, analyst-promoted review alerts, and manually correlated incidents linked to review alerts with MySQL activity history. MySQL 8.4 and platform-api are running on Ubuntu; Flyway schema version 6 is up to date. The earlier 12 H2-backed tests predate case, alert, and incident workflows; the current package build skipped tests. Alert/case/incident endpoints remain without dedicated automated coverage.
- A source-only Git checkpoint exists on the Ubuntu host on branch main (initial commit c5fa200). No remote is configured, so the checkpoint is not an off-machine backup.

The dashboard uses Spring for authenticated flow analysis, saved history, and manually created cases; engine status/model metadata come from FastAPI. Both services bind to loopback and are reached through SSH tunneling. The case feature is a basic shared analyst workflow, not a multi-tenant incident-management system. No production deployment, broad external alert/source integrations, managed collector, persistent server-side digital twin, network-facing deception deployment, RabbitMQ, WebSocket, or approved response system is implemented. The live runner is a separate CLI workflow; its metadata prediction results appear in the dashboard section named “Stored detection records,” separate from the simulated alert, case, and asset examples. Refer to docs/demo-runbook.md.

## Phases and current status

### Phase 1 — Core platform and authentication — Partial

Implemented: SOC dashboard shell and local FastAPI connection; separate Spring Boot login, JWT/RBAC-protected routes, database-backed access-token logout revocation, a public MySQL readiness probe, user model/repository, Flyway migrations, and authenticated AI proxy. Maven build and 12 H2-backed tests passed in the last recorded run.

Outstanding: account recovery, refresh tokens, audit event storage, and production secret/deployment operations. The current FastAPI demo remains unauthenticated; keep it bound to loopback and use SSH tunneling.

Exit criteria: clean setup; authenticated access; role enforcement; secrets externalized; migration-backed storage; access/audit behavior tested.

### Phase 2 — Network and system data collection — Partial

Implemented: experimental CLI for live interface capture and offline PCAP/PCAPNG replay. It emits candidate flow records for analysis and records runner-reported mode (live or PCAP) and a session UUID in metadata-only history, linking predictions to a lifecycle record. A bounded local session registry reports manual runner start, heartbeat, stop, and 45-second stale state to the dashboard without retaining interface names. Legacy sample records were backfilled as PCAP after confirming they came from the archived reference replay.

Outstanding: multi-source registry and ownership, independently attested collector health, complete event provenance, managed capture lifecycle, and a production retention/migration policy. The dashboard displays bounded SQLite prediction history under “Stored detection records” and the Real-time Monitor view. Both show completed model predictions, not an alert feed; Monitor polls every 10 seconds and supports live/PCAP filtering. Network Watch displays the adapter readiness response, runner heartbeat, empirical reference comparison, and open parity blockers. Do not describe the fictional map or alert cards as network telemetry.

Exit criteria: approved source is identified; capture records carry time/source provenance; replay is idempotent; dashboard reflects actual source status.

### Phase 3 — AI threat detection — Partial

Implemented: saved Hybrid V2 models, FastAPI inference, 67-feature schema metadata, separate detector outputs, readiness/parity reporting, experimental packet adapter, and metadata-only history for capture-adapter predictions.

Outstanding: exact parity with the training generator release, evaluation on independent captures, representative attack-family performance, model version governance, and robust failure/calibration handling. Existing benchmark results do not establish generalization to arbitrary networks.

Exit criteria: versioned input contract; independent holdout evidence; repeatable prediction record; failures and uncertainty visible; no prediction is treated as a confirmed incident by default.

### Phase 4 — Digital Twin — Partial

Implemented: an isolated in-browser preview with four virtual assets and three deterministic scenarios. Runs create visibly simulated timeline events; the latest 10 reports persist in browser storage and can be exported as JSON. They cannot access live telemetry, invoke model inference, or trigger production actions.

Outstanding: versioned topology and scenario contracts, shared server-side run persistence, importable state snapshots, and validation of isolation boundaries.

Exit criteria: reproducible isolated scenarios, provenance labels, and enforced separation from production endpoints.

### Phase 5 — Deception Analytics — Local lab slice

Cowrie 3.1.1 runs as a loopback-only SSH honeypot on 127.0.0.1:2222. The AI Engine reports service status and aggregate event counts from the local JSON audit log; raw credentials, addresses, and command text are not returned to the dashboard. Telnet is disabled. There is no external network exposure, long-term retention policy, or production sensor management.

Exit criteria: approved and isolated decoy deployment, parsed and sourced events, retention, containment, and operational ownership documented.

### Phase 6 — Orchestration and real-time monitoring — Partial

The dashboard's simulated incidents are illustrative only. Analyst-promoted alert records, manual cases, and incidents persist in MySQL with activity history; analysts can link stored alerts to incidents manually. Automated correlation, a playbook engine, RabbitMQ, authenticated WebSocket streaming, and response execution are not implemented.

Exit criteria: durable/idempotent event handling, bounded retry/dead-letter behavior, authenticated stream, review/approval workflow, audit history, and rollback. Begin with review-only actions; do not automate containment without separate validation and approval.

### Phase 7 — Integration, testing, deployment — Partial

Implemented: current host-run FastAPI and built frontend; optional platform API Dockerfile and Compose configuration; Compose config validation; loopback SSH-tunnel workflow.

Completed on the demo host: Java/MySQL containers are running; Flyway V1–V6 succeeded and the schema is at version 6. A private logical MySQL backup was created with a SHA-256 sidecar. Backup and guarded restore scripts are implemented; restore/rollback rehearsal remains outstanding. Outstanding: configure an approved remote backup/hosting destination, CI, broader integration/security tests, monitoring, and clean-machine setup. A local Git checkpoint exists, but it does not protect against loss of the Ubuntu host. Spring H2 tests do not cover full MySQL behavior.

Exit criteria: reproducible install and deployment; integration/security checks pass; data restore and rollback demonstrated; demo and production configuration separated; limitations documented.

## Near-term demo completion order

1. Keep simulation labels visible and make turning simulation off easy.
2. Demonstrate the real model through browser flow submission or the Ubuntu capture runner. Keep experimental results separate from fictional SOC events.
3. Use the bounded metadata history from capture-adapter predictions (GET /api/v1/demo/events). Store no raw feature vectors, packet payloads, or IP addresses; do not treat a model signal as an alert unless an authenticated analyst deliberately promotes it for review.
4. Rehearse the “Stored detection records” view with actual adapter predictions and verify timestamps/source labels. Keep capture explicit and local; do not grant the web app raw-packet privileges.
5. The Ubuntu demo host now runs MySQL and the Spring API with Flyway schema version 6, logout revocation, case management, analyst-reviewed alerts, and manual incident correlation enabled. Use the existing account for authenticated flow analysis and saved history; keep the FastAPI engine loopback-bound and the research limitations visible.
6. Run a clean demo rehearsal using docs/demo-runbook.md and record what remains unconnected.

The demo can be completed far sooner than the production system. Production completion requires implementing and validating each phase, not simply polishing the dashboard. Do not claim all seven phases are complete because the demo runs.

## Definition of done

For each phase: agreed scope and threat boundary, reviewed contracts, implementation/configuration, automated test and recorded result, limitations, runbook, and Git checkpoint. Keep simulated and observed data distinguishable in the UI and stored records.
