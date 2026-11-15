import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Clock3, Database, RefreshCw, ShieldAlert, UserCheck } from "lucide-react";
import { loadDemoEvents, loadAlerts, createAlertFromCapture, changeAlertStatus } from "./api.js";
import "./capture-monitor.css";
import "./history-pages.css";
import "./alert-workflow.css";

const alertStatuses = ["OPEN", "ACKNOWLEDGED", "INVESTIGATING", "RESOLVED", "FALSE_POSITIVE"];
const severityOptions = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

function formatTime(value) {
  if (!value) return "Time unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}
function friendly(error) {
  const detail = error.response?.data?.detail;
  return typeof detail === "string" ? detail : error.message || "Request failed.";
}

export default function AlertSignals({ session }) {
  const token = session?.accessToken;
  const [events, setEvents] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [model, setModel] = useState("any");
  const [mode, setMode] = useState("all");
  const [alertFilter, setAlertFilter] = useState("ALL");
  const [error, setError] = useState("");
  const [alertError, setAlertError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [updated, setUpdated] = useState(null);
  const [promoting, setPromoting] = useState("");
  const [title, setTitle] = useState("Model-flagged capture prediction");
  const [rationale, setRationale] = useState("");
  const [severity, setSeverity] = useState("MEDIUM");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    const eventRequest = loadDemoEvents(250);
    const alertRequest = token ? loadAlerts(token, 100) : Promise.resolve([]);
    const [eventResult, alertResult] = await Promise.allSettled([eventRequest, alertRequest]);
    if (eventResult.status === "fulfilled") {
      const response = eventResult.value;
      setEvents(Array.isArray(response.events) ? response.events.filter((event) => event.simulated === false) : []);
      setError("");
      setUpdated(new Date().toISOString());
    } else {
      setError("Capture prediction history is unavailable. Check the AI engine connection.");
    }
    if (alertResult.status === "fulfilled") {
      setAlerts(Array.isArray(alertResult.value) ? alertResult.value : []);
      setAlertError("");
    } else {
      setAlertError(friendly(alertResult.reason));
    }
    setRefreshing(false);
  }, [token]);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 10000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const signals = useMemo(() => events.filter((event) => {
    const rf = Boolean(event.rf_flagged);
    const iso = Boolean(event.if_flagged);
    const modelMatch = model === "any" || (model === "both" ? rf && iso : model === "rf" ? rf && !iso : iso && !rf);
    return modelMatch && (mode === "all" || event.capture_mode === mode) && (rf || iso);
  }), [events, model, mode]);

  const filteredAlerts = useMemo(() => alerts.filter((alert) => alertFilter === "ALL" || alert.status === alertFilter), [alerts, alertFilter]);
  const knownReferences = useMemo(() => new Set(alerts.map((alert) => alert.sourceReference)), [alerts]);
  const counts = useMemo(() => ({
    total: events.filter((event) => event.rf_flagged || event.if_flagged).length,
    rf: events.filter((event) => event.rf_flagged).length,
    iso: events.filter((event) => event.if_flagged).length,
    both: events.filter((event) => event.rf_flagged && event.if_flagged).length,
  }), [events]);

  async function submitPromotion(event, prediction) {
    event.preventDefault();
    if (!token) return;
    setBusy(true);
    setAlertError("");
    try {
      await createAlertFromCapture(token, prediction.id, { title: title.trim(), analystRationale: rationale.trim(), severity });
      setPromoting("");
      setTitle("Model-flagged capture prediction");
      setRationale("");
      await refresh();
    } catch (requestError) {
      setAlertError(friendly(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function updateStatus(alertId, nextStatus) {
    if (!token) return;
    setBusy(true);
    setAlertError("");
    try {
      const updatedDetail = await changeAlertStatus(token, alertId, nextStatus);
      setAlerts((current) => current.map((item) => item.id === alertId ? updatedDetail.alert : item));
    } catch (requestError) {
      setAlertError(friendly(requestError));
    } finally {
      setBusy(false);
    }
  }

  return <div className="page capture-monitor history-page alert-page">
    <div className="page-head"><div><div className="kicker">Alerts · analyst-reviewed model signals</div><h1>Alert Review</h1><p>Review capture predictions and promote selected signals into the persistent analyst queue.</p></div><button className="secondary-btn" onClick={refresh} disabled={refreshing}><RefreshCw size={13}/>{refreshing ? "Refreshing…" : "Refresh"}</button></div>
    <div className="history-warning"><AlertTriangle size={14}/><span><b>Model flags are not confirmed attacks.</b> Promotion requires an authenticated analyst, a reason, and a manually selected severity. The platform verifies the prediction against recent AI-engine history; no blocking or response action is performed.</span></div>
    <div className="capture-monitor-grid">
      <article className="panel capture-stat"><small>Flagged predictions</small><b>{counts.total}</b><span>Latest 250 capture records</span></article>
      <article className="panel capture-stat"><small>Random Forest</small><b>{counts.rf}</b><span>Experimental classifier flags</span></article>
      <article className="panel capture-stat"><small>Isolation Forest</small><b>{counts.iso}</b><span>Experimental anomaly flags</span></article>
      <article className="panel capture-stat"><small>Saved review alerts</small><b>{alerts.length}</b><span>Analyst-promoted · MySQL</span></article>
    </div>
    <section className="panel capture-table-panel alert-queue">
      <div className="panel-head"><div><h2>Persistent review queue</h2><p>Authenticated platform records · status changes are recorded in the activity log</p></div><span className="range"><UserCheck size={12}/>{alerts.length} SAVED</span></div>
      {!token && <div className="alert-login-note">Sign in to create and review persistent alerts. Model-flagged candidates remain visible below.</div>}
      {alertError && <div className="error alert-inline-error"><AlertTriangle size={13}/>{alertError}</div>}
      <div className="alert-filter"><label>Status<select value={alertFilter} onChange={(event) => setAlertFilter(event.target.value)}><option value="ALL">All statuses</option>{alertStatuses.map((value)=><option key={value} value={value}>{value.replaceAll("_"," ")}</option>)}</select></label></div>
      {!filteredAlerts.length ? <div className="capture-empty"><Database size={18}/><b>{alerts.length ? "No alerts match this status" : "No analyst review alerts saved"}</b><span>{alerts.length ? "Choose a different status filter." : "Choose a flagged prediction below and submit an analyst rationale to create a review alert."}</span></div> :
        <div className="alert-persisted-list">{filteredAlerts.map((alert) => <article className="alert-persisted" key={alert.id}>
          <div className="alert-persisted-main"><span className={"case-priority " + alert.severity.toLowerCase()}>{alert.severity}</span><b>{alert.title}</b><small>{alert.alertKey} · source prediction {alert.sourceReference.slice(0,8)} · by {alert.createdBy}</small><small>{alert.rfFlagged ? "RF flagged" : "RF clear"} · {alert.ifFlagged ? "IF flagged" : "IF clear"} · capture {formatTime(alert.predictionRecordedAt)} · saved {formatTime(alert.createdAt)}</small><p>{alert.description}</p></div>
          <label className="alert-status-select">Status<select disabled={busy} value={alert.status} onChange={(event) => updateStatus(alert.id,event.target.value)}>{alertStatuses.map((value)=><option key={value} value={value}>{value.replaceAll("_"," ")}</option>)}</select></label>
        </article>)}</div>}
    </section>
    <section className="panel capture-table-panel">
      <div className="panel-head"><div><h2>Flagged capture predictions</h2><p>{updated ? "Updated " + new Date(updated).toLocaleTimeString() : "Loading history"} · latest 250 records · refreshes every 10 seconds</p></div><span className="range"><Clock3 size={12}/>{signals.length} CANDIDATES</span></div>
      <div className="history-controls">
        <label className="history-mode"><ShieldAlert size={12}/><select value={model} onChange={(event) => setModel(event.target.value)}><option value="any">Either model</option><option value="both">Both models</option><option value="rf">Random Forest only</option><option value="iso">Isolation Forest only</option></select></label>
        <label className="history-mode"><select value={mode} onChange={(event) => setMode(event.target.value)}><option value="all">All capture modes</option><option value="live">Live capture</option><option value="pcap">PCAP replay</option></select></label>
      </div>
      {error ? <div className="capture-empty"><Database size={18}/><b>Signals unavailable</b><span>{error}</span></div> :
      !signals.length ? <div className="capture-empty"><Database size={18}/><b>{events.length ? "No flagged predictions in this view" : "No capture history available"}</b><span>{events.length ? "Try a different model or capture mode filter." : "Run the authorized capture CLI to save model predictions."}</span></div> :
      <div className="capture-record-list">{signals.map((event) => {
        const both = event.rf_flagged && event.if_flagged;
        const label = both ? "Both flagged" : event.rf_flagged ? "RF flagged" : "IF flagged";
        const alreadySaved = knownReferences.has(event.id);
        return <div className="alert-signal-wrap" key={event.id}><article className="capture-record">
          <div className="capture-record-origin"><b>{formatTime(event.recorded_at)}</b><span className={"capture-mode-tag " + event.capture_mode}>{event.capture_mode === "live" ? "LIVE CAPTURE" : event.capture_mode === "pcap" ? "PCAP REPLAY" : "MODE UNKNOWN"}</span><small>{event.input_source}</small><small>{event.capture_session_id ? "Session " + event.capture_session_id.slice(0,8) : "Session not recorded"}</small></div>
          <div className="capture-record-model"><span>Random Forest</span><b className={event.rf_flagged ? "flagged" : ""}>{event.rf_classification}</b><small>{(event.rf_probability * 100).toFixed(1)}% probability · threshold {(event.rf_threshold * 100).toFixed(1)}%</small></div>
          <div className="capture-record-model"><span>Isolation Forest</span><b className={event.if_flagged ? "flagged" : ""}>{event.if_classification}</b><small>{Number(event.if_score).toFixed(4)} anomaly score · threshold {Number(event.if_threshold).toFixed(4)}</small></div>
          <span className="capture-agreement">{label}</span>
        </article>
        {alreadySaved ? <span className="alert-promoted-label">Saved for review</span> :
        promoting === event.id ? <form className="alert-promote-form" onSubmit={(submitEvent) => submitPromotion(submitEvent,event)}><label>Alert title<input required maxLength={160} value={title} onChange={(e)=>setTitle(e.target.value)}/></label><label>Severity<select value={severity} onChange={(e)=>setSeverity(e.target.value)}>{severityOptions.map((value)=><option key={value} value={value}>{value}</option>)}</select></label><label>Analyst rationale<textarea required maxLength={2000} value={rationale} onChange={(e)=>setRationale(e.target.value)} placeholder="Explain why this signal needs review."/></label><button className="primary-btn small" disabled={busy}>{busy?"Saving…":"Create review alert"}</button><button type="button" className="secondary-btn small" onClick={()=>setPromoting("")}>Cancel</button></form> :
        token && <button className="secondary-btn small alert-promote-open" onClick={()=>{setPromoting(event.id);setRationale("");}}>Promote for review</button>}
        </div>;
      })}</div>}
    </section>
  </div>;
}

