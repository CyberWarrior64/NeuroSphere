# NeuroSphere V2 Database Design

## Status and rules

Current platform persistence: MySQL 8.4 with Flyway V1–V6 backs platform users/roles, flow-analysis result summaries, revoked JWT access-token IDs, authenticated case records/activity, analyst-promoted alert snapshots/activity, and incidents with linked alerts. The AI engine still loads model artifacts locally and does not use MySQL.

Use UTC timestamps, stable generated IDs, foreign keys, migrations, least-privilege DB accounts, and documented retention. Preserve provenance and model/schema versions. Store detector signals separately from analyst-confirmed incidents. Do not persist full flow vectors or raw PCAP by default; first agree on purpose, privacy, access, and retention. Keep credentials out of ordinary tables.

## Implemented tables

- platform_users and platform_user_roles (Flyway V1): BCrypt account records and role assignments.
- platform_flow_analyses (Flyway V2): submitter, model version, timestamp, RF/IF classifications, scores, flags, and detector agreement. Raw feature vectors, packet data, and IP addresses are excluded.
- revoked_access_tokens (Flyway V3): JWT ID (jti), expiration timestamp, and revocation timestamp. Revoked IDs are retained only until their tokens expire; bearer tokens are never stored.
- platform_cases and platform_case_activity (Flyway V4): manually reviewed case records and append-only status/note activity, tied to authenticated usernames. No packet features or network addresses are stored in these tables.
- platform_alerts and platform_alert_activity (Flyway V5): authenticated analyst-promoted snapshots of verified recent flagged capture predictions, with analyst-selected severity, rationale, model fields, lifecycle status, and status activity. The API checks the prediction against AI-engine history before storing it; raw features, IP addresses, and packet payloads are excluded.
- platform_incidents, platform_incident_activity, and platform_incident_alerts (Flyway V6): manually opened incident records, status/note history, and deduplicated links to persisted review alerts. Incident creation and alert linking are analyst actions; there is no automatic correlation or response execution.

The flow-analysis table currently has no automated retention policy. Define and implement retention before treating this as a production store.

## Proposed future tables

### Identity and authorization
- users: id, username/email (unique), password_hash, display_name, enabled, created_at, updated_at.
- roles: id, name (unique), description.
- user_roles: user_id, role_id, assigned_at, assigned_by.
- refresh_sessions if needed: user_id, token_hash, expires_at, revoked_at, created_at. Never store bearer tokens in clear text.

Initial roles: ADMIN, ANALYST, RESPONDER, VIEWER. Enforce roles in Spring Security and WebSocket subscriptions.

### Inventory and sources
- assets: id, external_key, hostname, primary_ip, asset_type, criticality, environment, first_seen_at, last_seen_at, status, source_id.
- data_sources: id, name, source_type, status, last_event_at, health_detail, secret_reference, timestamps. Store only a secret-manager reference.
- sensor_heartbeats: id, source_id, observed_at, version, status, bounded metrics_json.

### Events and inference
- network_flows: id, source_id, observed_start_at, observed_end_at, source/destination fields, protocol, feature_schema_version, optional features_json, ingest_status, created_at.
- detections: id, flow_id, source_id, detected_at, engine_name, model_version, input_schema_version, RF classification/score/threshold/flag, IF classification/score/threshold/flag, review_status, limitations_json.
- alerts: id, detection_id (nullable), source_id, title, category, severity, status, first_seen_at, last_seen_at, assigned_to, timestamps.
- alert_events: id, alert_id, actor_id, event_type, old/new state, occurred_at. Append-only.

The current 67-value CIC-IDS2017 payload is an inference input, not evidence of a validated production feed. Retain it only after policy review.

### Investigation workflow
- incidents: id, title, description, severity, status, opened_at, closed_at, owner_id, created_by, updated_at.
- incident_alerts: incident_id, alert_id, linked_at, linked_by.
- cases: id, case_number (unique), title, status, priority, owner_id, timestamps.
- case_activity: id, case_id, actor_id, activity_type, body, occurred_at.
- evidence_items: id, case_id, source_type, source_id, protected storage reference, sha256, collected_at/by, metadata_json.

### Later phases
- deception_events: id, source_id, observed_at, event_type, source_address, target_decoy, severity, evidence_reference, metadata_json.
- twin_scenarios and twin_runs: versioned scenario definitions and isolated simulation results.
- response_actions: id, alert_id, action_type, status, requested_by, approved_by, requested/approved/executed timestamps, result_json, idempotency_key. Keep execution unavailable until a separately approved response design.
- audit_events: id, occurred_at, actor_id, action, target_type/id, request_id, source_ip, result, details_json. Append-only and restricted.

## Relationships and open decisions

Users and roles are many-to-many. Sources have many events. Flows can have multiple detections; detections can be associated with alerts. Alerts link to incidents. Cases contain evidence and activity.

Index timestamps with source, severity, and status. Use unique constraints for usernames, source keys, case numbers, and idempotency keys. Keep commonly filtered values typed; use JSON only for versioned variable evidence. Define retention before partitioning high-volume tables.

Owner review remains needed for tenant isolation, IP handling, raw capture retention, user provisioning, password policy, data residency, backup retention, and the flow-history retention period before production use.
