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

The capture runner may add _capture_mode with pcap or live; the API stores it as non-feature metadata and returns it in stored history. Missing or invalid values become unspecified. This mode is client-reported and not independently attested. The API stores prediction summaries only; it does not retain raw feature vectors, packet payloads, IP addresses, or interface names.

Detection returns separate RF class/probability/threshold/flag and IF class/anomaly-score/threshold/flag, agreement/category, automatic_blocking=false, and a caution. Missing/extra fields are rejected with 422; unloaded models return 503. Scores are not guarantees of safety. Raw-packet parity and external generalization remain unresolved.

The feature body is strict. Example shape only (not a valid full request):

    {"Destination Port": 443, "Flow Duration": 125000, "Total Fwd Packets": 3}

## Current browser-to-platform contract

- POST /api/v1/platform/flows/analyze requires a bearer session and exactly 67 feature keys. Spring calls the loopback AI service, persists only score/result metadata, and returns the AI result with an analysis ID and timestamp.
- GET /api/v1/platform/flows/recent?limit=10 requires a bearer session and returns at most 50 stored summaries. It never returns raw input features.
- GET /api/v1/platform/status is public and checks database readiness with a lightweight SELECT 1; it reports no user or configuration details.
- The React flow screen keeps the short-lived access token in memory and clears it on refresh or expiry. Explicit logout calls POST /api/v1/auth/logout; Spring stores the token ID until expiration and rejects further use. If logout cannot reach the API, the UI still clears local state and warns that the token may remain valid until expiry. The demo dashboard remains available without login.

## Target browser-to-platform contract

Use HTTPS JSON under /api/v1/platform. JWT access tokens and Spring Security roles protect routes. Suggested endpoints: GET /dashboard/summary, GET /dashboard/sources, GET /alerts, GET /incidents, GET /assets, GET /events/search, POST /flows/analyze.

Java validates session, schema version, and request size, then calls private AI. It attaches a request ID and wraps the result with provenance/model metadata. Do not expose AI ports or credentials to the browser.

## Target Java-to-AI contract

Use private HTTP with bounded payloads/timeouts, service identity, network isolation, and X-Request-ID. Validate all 67 names against model metadata. Translate FastAPI errors into safe platform errors; do not leak traces. The current proxy stores model version and the RF/IF scores, classifications, flags, and agreement. Thresholds and raw features are not stored. The private AI endpoint itself still has no service-auth token or request envelope.

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
