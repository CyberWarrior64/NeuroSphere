# NeuroSphere V2 System Architecture

## Purpose

NeuroSphere V2 is intended to be a modular security operations platform for collecting events, analyzing flows, presenting investigations, and supporting analyst-reviewed response. The reference dashboard is a SOC console with navigation, real operational indicators, monitoring, alerts, incidents, cases, sources, and reports.

## Current workspace (verified)

The shared Ubuntu project root contains only ai-engine/. It is a FastAPI service with saved scikit-learn Hybrid V2 models and experimental CICFlowMeter-compatible input. There is no React app, Java/Spring application, authentication, database, message broker, sensor fleet, digital twin, deception service, or response integration. The page shown earlier is a detector console, not the target SOC dashboard.

Existing routes include GET /health, GET /api/v1/models/v2, POST /api/v1/detect/v2, validated-model routes, and experimental CICFlowMeter routes. Hybrid V2 requires the exact 67-feature CIC-IDS2017 schema. Model-parity gaps and weak held-out performance for some attack families are documented in ai-engine/README.md.

## Target architecture

    Analyst browser
       | HTTPS
       v
    React SOC console
       | REST + authenticated WebSocket
       v
    Java 21 Spring Boot platform API
       |-- Spring Security / JWT / RBAC
       |-- dashboard, alerts, incidents, assets, cases, audit
       |-- business rules and analyst-approved response workflow
       |-- MySQL and RabbitMQ
       |-- private HTTP inference call
       v
    Python FastAPI AI engine (existing)
       ^
       |
    Approved network/log collectors, Cowrie, flow/PCAP import
       +---- isolated digital twin and deception event sources (later phases)

Only the Python service currently exists. React, Java, identity, storage, broker, collectors, and lab services are proposals.

## Proposed repository structure

    NeuroSphere/
      frontend/                 React, Tailwind, routes, charts, API client
      platform-api/             Java 21 Spring Boot, auth, platform REST, persistence
      ai-engine/                Existing Python FastAPI service and model assets
      collectors/                Approved flow/log collectors (later phase)
      shared/contracts/          OpenAPI, event schemas, feature schema/version
      infra/                     Compose, proxy, network and environment templates
      docs/architecture/         System, database, contracts, deployment
      docs/development-roadmap.md

This is a proposal, not the current folder tree. Preserve ai-engine/ as the existing service; do not relocate or replace its working model code without a reviewed migration plan.

## Responsibilities and trust boundaries

| Component | Responsibility | Boundary |
|---|---|---|
| React console | Render platform data and analyst workflows; no secrets in browser | Untrusted client |
| Spring Boot API | Authentication, authorization, persistence, audit, AI orchestration, event delivery | Browser-facing application |
| FastAPI AI engine | Validate flow features and return separate model signals | Private network |
| Collectors | Capture/import approved events and preserve provenance | Restricted sensor boundary |
| MySQL | Durable platform state and audit history | Private data network |
| RabbitMQ | Versioned asynchronous event transport | Private network with scoped credentials |
| Digital twin | Isolated simulation of approved assets/scenarios | Lab network; no production route |
| Cowrie/deception | Controlled decoy telemetry | Isolated, monitored lab |

## Dashboard modules from the reference

Overview; Real-time Monitor; SIEM Search; Alerts; Incidents; Endpoint Security; Network Watch; Threat Intelligence; Vulnerability Management; Case Management; Reports; Playbooks; Settings; and Data Sources.

Show only numbers and status backed by connected data. Until collectors and persistence exist, show empty states such as “No source connected” or “No incidents recorded.” Never fabricate alert totals, blocked threats, countries, monitored assets, or live status.

## Security and detection rules

- Keep AI and data services private; expose browser requests through the platform API.
- Separate model output from confirmed incidents. Model scores are investigational signals, not guarantees of safety.
- No automatic blocking or alert escalation. Any future response needs analyst approval, target allow-lists, audit, and rollback.
- Label each record with source, time, model/schema version, and whether it is live, imported, or simulated.
- Isolate the digital twin and honeypot from production systems.

## First proposed vertical slice

After architecture approval: a React SOC-style shell, actual service/model status, flow import/paste into the current model, separate Random Forest and Isolation Forest signals, and research caveats. Auth, alerts, live data, persistence, integrations, and response controls need separate approved scope. A complete seven-phase platform cannot be promised by tomorrow from this starting point.
