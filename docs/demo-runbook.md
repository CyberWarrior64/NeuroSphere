# Hybrid SOC demo runbook

This runbook separates the fictional SOC presentation from actual model analysis and packet capture. Use the simulation to demonstrate layout and analyst workflow concepts; use the live runner to demonstrate experimental analysis of traffic on the Ubuntu machine.

## What is real and what is simulated

| Dashboard or demo item | Source | What it means |
| --- | --- | --- |
| Simulation banner, sample alerts, severity counts, sample cases, demo asset count, and activity paths | Hard-coded UI examples | Fictional values for presentation only. They are not detections and do not describe the monitored network. |
| Engine health and Hybrid V2 model metadata | Running FastAPI service | Live service/model availability and 67-feature schema. |
| Browser flow analysis | Authenticated JSON sent to Spring POST /api/v1/platform/flows/analyze, then forwarded to FastAPI | Real model inference over supplied values. Spring stores result metadata only. Outputs remain experimental research signals. |
| Terminal capture runner | Live interface or offline PCAP, converted into candidate flow features and posted to the CICFlowMeter adapter | Real packets are processed on Ubuntu. Experimental predictions print in the terminal and their metadata, including a generated runner session UUID, is stored in local SQLite and displayed under “Stored detection records.” The UUID links a prediction to its runner session without storing the interface name. This view is prediction history, not the simulated SOC alert table. |
| SIEM Search and Reports | GET /api/v1/demo/events metadata history | Search filters up to 250 saved prediction summaries. Reports summarizes the same window and exports metadata-only CSV. These pages are not connected to a SIEM, alert queue, or incident store. |

Current demo history was seeded from the archived Monday-first-20000.pcap reference capture: 20,000 packets were replayed into the adapter. The bounded SQLite history retains the latest 1,000 prediction summaries. This is historical reference traffic, not a live capture or alert feed. New runner submissions record a client-reported mode (PCAP replay or live capture); the API does not independently attest that mode. The separate authenticated platform history now contains one analysis of a CICIDS2017 DDoS-labeled reference row; its label was not sent to the model. The Random Forest returned ATTACK (0.805 probability) and Isolation Forest returned NORMAL (0.500 anomaly score). This benchmark example is not independent validation and is not an alert.

## Start the dashboard

On Ubuntu, in the project environment:

    cd /mnt/neurosphere/NeuroSphere/ai-engine
    ./run-api.sh

The host binds to loopback. From Windows PowerShell, create an SSH tunnel:

    ssh -N -L 8000:127.0.0.1:8000 -L 8765:127.0.0.1:8000 -L 8081:127.0.0.1:8081 cse-cy-02@100.70.85.104

Keep the SSH terminal open and browse to http://127.0.0.1:8765/. If model status initially says unavailable, refresh after the API has finished loading the saved models. API health and model metadata can be checked on Ubuntu:

    curl -fsS http://127.0.0.1:8000/health
    curl -fsS http://127.0.0.1:8000/api/v1/models/v2

The simulation toggle on the dashboard only shows or hides the fictional SOC examples. It does not start/stop capture or change model inference.

## Run an isolated Digital Twin scenario

Open **Digital Twin** from the sidebar. Select External reconnaissance, Credential spray, or Suspicious data movement, then choose **Run scenario**. The page animates events across four virtual assets and saves up to 10 completed run reports in that browser’s local storage. Use Export JSON to download a report; runs are not shared across devices. All events are fictional. The runner makes no network requests, does not call the AI engine, and does not perform security actions. Use the separate Flow Analysis page for real model inference and the capture runner for authorized packet analysis.

## Analyze one real flow in the browser

Open Flow Analysis and load a JSON record with the model's named 67-feature schema. A template can be loaded from the UI or fetched from:

    curl -fsS http://127.0.0.1:8000/api/v1/models/v2

Template nulls are placeholders, not valid measured features. Supply real numeric measurements. The analysis response includes separate Random Forest and Isolation Forest signals; disagreement is possible. This is not an alert, confirmed incident, or block decision.

## Capture traffic from the Ubuntu interface

Use a separate SSH terminal connected to the Ubuntu host. First identify the live interface:

    ssh cse-cy-02@100.70.85.104
    ip -brief link

The currently observed wired interface is enp0s31f6; verify it is still UP before capture. Run the capture process with the existing virtual environment and packet-capture privileges:

    cd /mnt/neurosphere/NeuroSphere/ai-engine
    sudo .venv/bin/python -m app.feature_extraction.run_reference_capture -i enp0s31f6 -u http://127.0.0.1:8000/api/v1/detect/cicflowmeter-python

The sidebar and System Status panel show the manual runner as Running while its 10-second heartbeat is current, Stopped after normal exit, or Stale after 45 seconds without a heartbeat. These states are runner-reported and do not prove that an independent sensor observed traffic. Interface names and packet data are not stored for status. Each completed flow prints a compact JSON model response. The adapter also saves bounded metadata for the latest 1000 predictions; it stores a runner session UUID when supplied, but no raw features, packet payloads, IP addresses, or interface names. Read the demo history at GET /api/v1/demo/events, the dashboard’s “Stored detection records” panel, or the Real-time Monitor page. Monitor polls every 10 seconds and can filter live capture versus PCAP replay. Network Watch presents the adapter readiness and known parity blockers; it is not a live packet stream. Press Ctrl+C to stop. Do not substitute an interface you are not authorized to monitor. A capture sees traffic available on the selected interface; it may include private network metadata. The runner and readiness API remain research-grade, with unresolved exact-generator parity and detection generalization. Do not use these outputs to automatically block traffic or escalate alerts.

To replay a saved PCAP/PCAPNG instead of sniffing the live interface:

    cd /mnt/neurosphere/NeuroSphere/ai-engine
    .venv/bin/python -m app.feature_extraction.run_reference_capture -f datasets/reference_pcaps/Monday-first-20000.pcap -u http://127.0.0.1:8000/api/v1/detect/cicflowmeter-python

The file path above is an example and must exist on the host. Use the readiness endpoint for the adapter's current parity caveats:

    curl -fsS http://127.0.0.1:8000/api/v1/capture/cicflowmeter-python/readiness


## Spring Boot platform API and MySQL

The Java 21 / Spring Boot 3.5.16 API is running on Ubuntu with MySQL 8.4. Flyway reports schema version 3 up to date; V1 through V3 are successful. One platform user is provisioned. The public platform status route checks MySQL with `SELECT 1` and the dashboard polls it every 30 seconds. Logout revokes the current access token in MySQL; refresh tokens are not implemented. The API binds to loopback on port 8081. The last recorded Maven run passed 12 H2-backed tests; these do not establish full MySQL compatibility.

The FastAPI research engine remains unauthenticated and loopback-bound. The dashboard reads AI health/model metadata from FastAPI; login, flow analysis, and saved history use the authenticated Spring platform API.

Compose uses host networking for platform-api so the Linux container can reach the existing loopback AI service on 127.0.0.1:8000. This is Linux-only; use the Ubuntu host, not Docker Desktop on Windows or macOS. Platform API binds to 127.0.0.1:8081 and MySQL is published at 127.0.0.1:3307.

On Ubuntu, from the repository root, create a private infra/.env from infra/.env.example and set file permissions to owner-only. Generate NS_JWT_SECRET_BASE64 with openssl rand -base64 48. Set unique strong values for MYSQL_PASSWORD and MYSQL_ROOT_PASSWORD. Do not commit or share infra/.env; example values are placeholders. See the root README for exact validation and optional startup commands.

Admin bootstrap is optional and has no default credentials. To create the first admin, set both NS_BOOTSTRAP_USERNAME and NS_BOOTSTRAP_PASSWORD before first startup. Username rules are documented in platform-api/README.md; password length is at least 16 characters. Remove both variables after the first admin is created.

The live MySQL database has applied Flyway V1 through V3 and is at schema version 3. Startup logs advise that this Flyway version has not tested MySQL 8.4 (its documented support range ends at 8.1).

To create a private database backup, run infra/backup-mysql.sh from Ubuntu. It writes a compressed logical dump and SHA-256 sidecar under /mnt/neurosphere/backups/mysql. Restore is destructive: infra/restore-mysql.sh requires the exact typed database confirmation and first creates a backup of the current database. Never test restore against the demo database.

To tunnel both local-only HTTP services from Windows:

    ssh -N -L 8000:127.0.0.1:8000 -L 8765:127.0.0.1:8000 -L 8081:127.0.0.1:8081 cse-cy-02@100.70.85.104

Keep the tunnel open. Dashboard: http://127.0.0.1:8765/. Optional login API: POST http://127.0.0.1:8081/api/v1/auth/login. MySQL is not forwarded. Do not expose these services publicly.

## Known demo boundaries

- Dashboard simulation records are static UI examples; they do not come from the model or capture runner.
- Live capture predictions print to the terminal and appear in “Stored detection records” and the Real-time Monitor page. A local SQLite store retains metadata for up to 1000 adapter predictions; GET /api/v1/demo/events is prediction history, not an alert feed. It stores no raw features, packet payloads, or IP addresses.
- There is no alert, case, or asset workflow connecting capture predictions to the simulated cards.
- Browser-submitted /api/v1/detect/v2 results and their chart remain session-only unless the API integration is changed.
- The production adapter's feature mapping is not certified as exactly equivalent to the CICFlowMeter version used for model training. Evaluation-only candidate mappings must not be presented as production behavior.
- Model performance is limited on some held-out attack families. Use the dashboard only for demonstration and research.
- The deployed Spring API is an early authentication/proxy slice, not a production identity service. There is no production identity lifecycle, connected authentication flow, audit store, broker, authenticated real-time stream, digital twin, Cowrie integration, or response execution flow.
