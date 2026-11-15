# NeuroSphere V2 roadmap

## Current baseline

The shared project is a working research demo composed of a React SOC-style dashboard and a Python/FastAPI model service. The frontend is served by FastAPI on loopback. It is not yet the full target platform in the architecture documents.

Verified demo components:

- Dashboard built with React, Tailwind, React Router, Axios, Recharts, and Lucide.
- FastAPI health, GPU, model metadata, and flow detection routes.
- Hybrid V2 serves Random Forest and Isolation Forest outputs over the named 67-feature CIC-IDS2017 schema.
- Dashboard simulation mode displays fictional sample alerts, cases, inventory, severity counts, and illustrative paths. These remain explicitly labeled as simulated.
- Browser-submitted flow records reach the real model endpoint; outputs and short browser trend are session-only.
- Experimental Python packet capture / PCAP replay runner posts completed records to the CICFlowMeter adapter and prints output to the terminal.
- Capture-adapter predictions are recorded in bounded metadata-only local SQLite history (maximum 1000), exposed by GET /api/v1/demo/events. Raw feature vectors, IP addresses, and packet payloads are not stored.
- The frontend production build completed successfully for the current FastAPI host.
- Java 21 / Spring Boot 3.5.16 provides login, JWT/RBAC-protected routes, Flyway V1–V3 migrations, database-backed JWT logout revocation, an authenticated AI proxy, and protected analysis history. MySQL 8.4 and platform-api are running on Ubuntu; Flyway schema version 3 is up to date and one platform user exists. The last recorded Maven run passed 12 H2-backed tests.
- The project has no Git metadata, so versioned Git checkpoints are not currently available.

The dashboard uses Spring for authenticated flow analysis and saved history; engine status and model metadata come from FastAPI. Both services bind to loopback and are reached through SSH tunneling. No production deployment, durable alert/case workflow, managed collector service, digital twin, Cowrie analytics, RabbitMQ, WebSocket, or automated response system is implemented. The live runner is a separate CLI workflow; its metadata prediction results appear in the dashboard section named “Stored detection records,” separate from the simulated alert, case, and asset examples. Refer to docs/demo-runbook.md.

## Phases and current status

### Phase 1 — Core platform and authentication — Partial

Implemented: SOC dashboard shell and local FastAPI connection; separate Spring Boot login, JWT/RBAC-protected routes, database-backed access-token logout revocation, user model/repository, Flyway migrations, and authenticated AI proxy. Maven build and 12 H2-backed tests passed in the last recorded run.

Outstanding: account recovery, refresh tokens, audit event storage, and production secret/deployment operations. The current FastAPI demo remains unauthenticated; keep it bound to loopback and use SSH tunneling.

Exit criteria: clean setup; authenticated access; role enforcement; secrets externalized; migration-backed storage; access/audit behavior tested.

### Phase 2 — Network and system data collection — Partial

Implemented: experimental CLI for live interface capture and offline PCAP/PCAPNG replay. It emits candidate flow records for analysis and records the runner-reported mode (live or PCAP) in metadata-only history. Legacy sample records were backfilled as PCAP after confirming they came from the archived reference replay.

Outstanding: source registry, managed collector health/staleness, complete event provenance, managed capture lifecycle, and a production retention/migration policy. The dashboard now displays the current bounded SQLite prediction history under “Stored detection records.” These are demo-only model results, not an alert feed. Do not describe the fictional map or alert cards as network telemetry.

Exit criteria: approved source is identified; capture records carry time/source provenance; replay is idempotent; dashboard reflects actual source status.

### Phase 3 — AI threat detection — Partial

Implemented: saved Hybrid V2 models, FastAPI inference, 67-feature schema metadata, separate detector outputs, readiness/parity reporting, experimental packet adapter, and metadata-only history for capture-adapter predictions.

Outstanding: exact parity with the training generator release, evaluation on independent captures, representative attack-family performance, model version governance, and robust failure/calibration handling. Existing benchmark results do not establish generalization to arbitrary networks.

Exit criteria: versioned input contract; independent holdout evidence; repeatable prediction record; failures and uncertainty visible; no prediction is treated as a confirmed incident by default.

### Phase 4 — Digital Twin — Not started

Build only after an isolated asset/scenario contract exists. Simulated data must be visibly marked and prevented from invoking production actions.

Exit criteria: reproducible isolated scenarios, provenance labels, and enforced separation from production endpoints.

### Phase 5 — Deception Analytics — Not started

No Cowrie deployment or honeypot event ingestion currently exists.

Exit criteria: approved and isolated decoy deployment, parsed and sourced events, retention, containment, and operational ownership documented.

### Phase 6 — Orchestration and real-time monitoring — Not started

The dashboard's simulated cases are illustrative only. There is no durable incident or playbook service, RabbitMQ, authenticated WebSocket stream, or response execution.

Exit criteria: durable/idempotent event handling, bounded retry/dead-letter behavior, authenticated stream, review/approval workflow, audit history, and rollback. Begin with review-only actions; do not automate containment without separate validation and approval.

### Phase 7 — Integration, testing, deployment — Partial

Implemented: current host-run FastAPI and built frontend; optional platform API Dockerfile and Compose configuration; Compose config validation; loopback SSH-tunnel workflow.

Completed on the demo host: Java/MySQL containers are running; Flyway V1–V3 succeeded and the schema is at version 3. A private logical MySQL backup was created with a SHA-256 sidecar. Backup and guarded restore scripts are implemented; restore/rollback rehearsal remains outstanding. Outstanding: Git checkpoints (the project directory has no Git metadata), CI, broader integration/security tests, monitoring, and clean-machine setup. Spring H2 tests do not cover full MySQL behavior.

Exit criteria: reproducible install and deployment; integration/security checks pass; data restore and rollback demonstrated; demo and production configuration separated; limitations documented.

## Near-term demo completion order

1. Keep simulation labels visible and make turning simulation off easy.
2. Demonstrate the real model through browser flow submission or the Ubuntu capture runner. Keep experimental results separate from fictional SOC events.
3. Use the bounded metadata history from capture-adapter predictions (GET /api/v1/demo/events). Store no raw feature vectors, packet payloads, or IP addresses; do not treat a model signal as a persisted alert.
4. Rehearse the “Stored detection records” view with actual adapter predictions and verify timestamps/source labels. Keep capture explicit and local; do not grant the web app raw-packet privileges.
5. The Ubuntu demo host now runs MySQL and the Spring API with Flyway schema version 3 and logout revocation enabled. Use the existing account for authenticated flow analysis and saved history; keep the FastAPI engine loopback-bound and the research limitations visible.
6. Run a clean demo rehearsal using docs/demo-runbook.md and record what remains unconnected.

The demo can be completed far sooner than the production system. Production completion requires implementing and validating each phase, not simply polishing the dashboard. Do not claim all seven phases are complete because the demo runs.

## Definition of done

For each phase: agreed scope and threat boundary, reviewed contracts, implementation/configuration, automated test and recorded result, limitations, runbook, and Git checkpoint. Keep simulated and observed data distinguishable in the UI and stored records.
