# NeuroSphere SOC Dashboard

React SOC-style dashboard for the existing AI engine. It uses React Router, Tailwind CSS, Axios, Recharts, and Lucide icons.

## Run in development

Keep FastAPI running on 127.0.0.1:8000, then from frontend:

    npm install
    npm run dev

Vite serves on 127.0.0.1:5173 and proxies /health, /gpu, and /api requests to FastAPI.

## Build for the FastAPI host

From frontend:

    npm run build

FastAPI serves frontend/dist at / and its assets at /assets. Restart FastAPI after building when needed.

From Windows PowerShell, tunnel to the loopback-only Ubuntu service:

    ssh -N -L 8765:127.0.0.1:8000 cse-cy-02@100.70.85.104

Keep the tunnel open and browse to http://127.0.0.1:8765/.

## Data status

Simulation mode starts enabled for the dashboard example alerts, cases, inventory counts, and illustrative network paths. These values are fictional, not observed traffic, and do not come from model results.

Engine status and model schema are fetched from FastAPI. Browser-submitted flow analysis uses POST /api/v1/detect/v2; its chart is temporary browser-session state. The live/PCAP capture runner uses POST /api/v1/detect/cicflowmeter-python. That adapter stores bounded metadata-only prediction history in local SQLite, exposed by GET /api/v1/demo/events and displayed under “Stored detection records.” The store excludes raw feature vectors, packet payloads, and IP addresses. These prediction records do not create dashboard alert, incident, or case records.

See ../docs/demo-runbook.md for the separated simulation, browser analysis, and Ubuntu capture workflows. See ../docs/development-roadmap.md for remaining platform work.
