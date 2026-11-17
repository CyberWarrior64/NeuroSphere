# NeuroSphere smoke-test files

These fixtures contain synthetic examples for checking the current demo. They are not evidence of an attack or a normal network session.

## Flow Analysis

- `flow-smoke-test.json` has all 67 current Hybrid V2 feature names and numeric placeholder measurements. It passed a direct request to the current AI detection endpoint when created. Its RF/Isolation Forest output is only a wiring/schema check; do not interpret its classification.
- `flow-template-67.json` mirrors the model schema with `null` placeholders. Use it to compare the field names or load it into the Flow Analysis page, but do not submit the null template as a measured flow.

In the dashboard, sign in, open **Flow Analysis**, choose `flow-smoke-test.json`, and run detection. The platform API stores a result summary. The raw feature vector is not retained.

## Offline packet capture

`capture-smoke-test.pcap` is a tiny synthetic TCP exchange between RFC 5737 documentation addresses. The packets are fictitious and do not target real hosts. The generator is `make_capture_smoke_test.py` and uses only Python’s standard library.

The fixture is also copied into the Ubuntu project checkout at `/mnt/neurosphere/NeuroSphere/docs/test-fixtures/capture-smoke-test.pcap`. Replay it offline on Ubuntu:

```bash
cd /mnt/neurosphere/NeuroSphere/ai-engine
.venv/bin/python -m app.feature_extraction.run_reference_capture \
  -f /mnt/neurosphere/NeuroSphere/docs/test-fixtures/capture-smoke-test.pcap \
  -u http://127.0.0.1:8000/api/v1/detect/cicflowmeter-python
```

This sends the synthetic completed flow to the AI engine and adds a prediction summary to the local capture history. It does not start live packet capture. The adapter remains experimental, and a model result is not an alert or a verdict about the capture.

## Case and incident workflows

`case-entry-smoke-test.json` and `incident-entry-smoke-test.json` are copy/paste examples for their respective signed-in forms; those pages do not accept file uploads. Creating them writes QA records to MySQL. You can change their status and add notes, then verify the dashboard’s **Recent Cases** panel.

## Check the remaining dashboard sections

1. Use **Show demo data** on the dashboard to exercise simulated alerts, severity counts, map animation, and demo cases. The banner labels all of these as fictional.
2. Open **Digital Twin** and run one built-in scenario; its events are simulated and stay local to the browser.
3. Open **Playbooks** and check/uncheck steps; progress is local to that page session.
4. Sign in and open **Cases**, **Incidents**, and **Alerts** to check the persistent workflows.
5. Open **Settings** and verify AI, platform/MySQL, endpoint telemetry, Cowrie, and threat-feed service states. Endpoint, Cowrie, and threat-feed panels read connected services; no fixture file can honestly make those integrations live.
6. **Real-time Monitor** and **SIEM Search** display capture prediction history, not a SIEM or confirmed alert feed. The PCAP replay above creates one clearly marked test prediction there.

All model output is research-only. Do not use these fixtures to test blocking, alert escalation, or response automation.
