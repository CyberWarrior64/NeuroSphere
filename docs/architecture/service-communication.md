# NeuroSphere V2 Service Communication

## Existing FastAPI contracts

The current service lives in ai-engine/ and normally binds to 127.0.0.1:8000.

| Route | Contract |
|---|---|
| GET /health | Service health and name |
| GET /api/v1/models/v2 | Hybrid V2 version, feature count/names, frozen RF/IF thresholds |
| POST /api/v1/detect/v2 | One JSON object with exactly the named 67 CIC-IDS2017 features; finite numeric or null values |
| GET /api/v1/capture/cicflowmeter-python/readiness | Experimental adapter readiness and known parity blockers |
| POST /api/v1/detect/cicflowmeter-python | Experimental CICFlowMeter record input |

The capture runner may add _capture_mode with pcap or live and a generated _capture_session_id UUID; the API stores both as non-feature metadata and returns them in stored history. Missing or invalid values become unspecified or null. Both are client-reported and not independently attested. The session UUID links a prediction to a runner lifecycle record. The API stores prediction summaries only; it does not retain raw feature vectors, packet payloads, IP addresses, or interface names.

Detection returns separate RF class/probability/threshold/flag and IF class/anomaly-score/threshold/flag, agreement/category, automatic_blocking=false, and a caution. Missing/extra fields are rejected with 422; unloaded models return 503. Scores are not guarantees of safety. Raw-packet parity and external generalization remain unresolved.

The feature body is strict. Example shape only (not a valid full request):

    {"Destination Port": 443, "Flow Duration": 125000, "Total Fwd Packets": 3}

## Current browser-to-platform contract

- POST /api/v1/platform/flows/analyze requires a bearer session and exactly 67 feature keys. Spring calls the loopback AI service, persists only score/result metadata, and returns the AI result with an analysis ID and timestamp.
- GET /api/v1/platform/flows/recent?limit=10 requires a bearer session and returns at most 50 stored summaries. It never returns raw input features.
- GET /api/v1/platform/status is public and checks database readiness with a lightweight SELECT 1; it reports no user or configuration details.
- GET/POST /api/v1/platform/cases, GET /api/v1/platform/cases/{id}, PATCH /api/v1/platform/cases/{id}/status, and POST /api/v1/platform/cases/{id}/notes require a bearer token. Case writes include the authenticated actor and append activity entries. List results are bounded to 100; notes are bounded to 2,000 characters.
- GET /api/v1/platform/alerts and GET /api/v1/platform/alerts/{id}, POST /api/v1/platform/alerts/from-capture/{predictionId}, and PATCH /api/v1/platform/alerts/{id}/status require a bearer token. Spring fetches the candidate from loopback FastAPI history and verifies that a non-simulated model flag exists before creating an alert snapshot. Severity and rationale are analyst-selected; alert activity is stored in MySQL.
- GET/POST /api/v1/platform/incidents, GET /api/v1/platform/incidents/{id}, PATCH /api/v1/platform/incidents/{id}/status, POST /api/v1/platform/incidents/{id}/notes, and POST /api/v1/platform/incidents/{id}/alerts/{alertId} require a bearer token. Incidents are manually created; only stored review alerts can be linked. Status, note, and link actions are recorded in MySQL activity history.
- The React flow screen keeps the short-lived access token in memory and clears it on refresh or expiry. Explicit logout calls POST /api/v1/auth/logout; Spring stores the token ID until expiration and rejects further use. If logout cannot reach the API, the UI still clears local state and warns that the token may remain valid until expiry. The demo dashboard remains available without login.

## Target browser-to-platform contract

Use HTTPS JSON under /api/v1/platform. JWT access tokens and Spring Security roles protect routes. Suggested endpoints: GET /dashboard/summary, GET /dashboard/sources, GET /alerts, GET /incidents, GET /assets, GET /events/search, POST /flows/analyze.

Java validates session, schema version, and request size, then calls private AI. It attaches a request ID and wraps the result with provenance/model metadata. Do not expose AI ports or credentials to the browser.

## Target Java-to-AI contract

Use private HTTP with bounded payloads/timeouts, service identity, network isolation, and X-Request-ID. Validate all 67 names against model metadata. Translate FastAPI errors into safe platform errors; do not leak traces. The current proxy stores model version and the RF/IF scores, classifications, flags, and agreement. Thresholds and raw features are not stored. The private AI endpoint itself still has no service-auth token or request envelope. The manual capture runner reports lifecycle to GET /api/v1/capture/runner/status and POST /api/v1/capture/runner/session; it sends only a generated session ID, live/PCAP mode, and lifecycle action. The runner controls these client-reported values, and stale status means no heartbeat for 45 seconds.

The AI Engine exposes GET /api/v1/endpoint/telemetry for the Linux host on which it runs. The route reads local CPU/load, memory, root filesystem free space, uptime, and at most 500 SSH service journal records from the prior 24 hours. It returns aggregate failed/successful SSH login counts only; raw journal messages, usernames, and addresses are neither returned nor stored. The dashboard polls this endpoint every 30 seconds. This is read-only host telemetry, not an endpoint detection/response agent.

The AI Engine exposes GET /api/v1/deception/cowrie/status for the local Cowrie sensor. It verifies the Cowrie PID and loopback-only SSH configuration, then reads a bounded tail of the Cowrie JSON audit log and returns 24-hour aggregate counts and event-type totals. It never returns raw Cowrie records, credential fields, client addresses, or command text. Cowrie is bound to 127.0.0.1:2222; Telnet is disabled. Raw audit logs remain on the Ubuntu data volume and have no configured retention schedule yet.

The AI Engine exposes GET /api/v1/threat-intel/status and GET /api/v1/threat-intel/indicators?limit=200 for the public Emerging Threats compromised-host IPv4 list. It fetches the fixed HTTPS source on demand, caches successful results in process memory for 15 minutes, retries failed fetches no more than once every five minutes, caps response size at 1 MB, filters to globally routable IPv4 addresses, and returns at most 500 indicators. A failed refresh preserves the last successful in-memory result and marks it stale. The outbound request sends no analyst, host, or traffic data. This feed is contextual intelligence only: the engine does not correlate it with observed traffic or make blocking/response decisions.

## Target asynchronous events

RabbitMQ is not configured today. Define durable exchanges/queues, routing keys, retries, dead-letter policy, ownership, and retention before use. Proposed versioned envelope:

    {
      "event_id": "uuid",
      "event_type": "network.flow.observed",
      "schema_version": "1.0",
      "occurred_at": "RFC3339 UTC",
      "source": {"id": "source-id", "kind": "sensor"},
      "correlation_id": "uuid",
      "payload": {}
    }

Validate schema, cap message size, make consumers idempotent by event_id, and dead-letter poison messages. Do not put secrets or raw packet payloads in routine events.

## Target WebSocket and errors

Use authenticated WSS through Spring Boot. Authorize subscriptions per role; apply size/rate limits and reconnect backoff. Frames carry event ID, type, schema version, timestamp, correlation ID, and minimized payload. Persist authoritative state in MySQL; WebSocket frames are notifications.

Platform errors have code, safe message, request_id, and optional field errors. Log IDs, not secrets or complete sensitive payloads. Source health distinguishes unavailable, degraded, stale, and healthy with last observation time.

## Collection and response

Collectors normalize source data while retaining source IDs and original times. Do not claim coverage until a real source is configured and heartbeats arrive. Cowrie and twin events are labeled as decoy/simulation. Response actions remain a separate audited analyst-approval workflow, outside the first delivery.
