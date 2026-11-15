import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Clock3, Database, RefreshCw, ShieldAlert } from "lucide-react";
import { loadDemoEvents } from "./api.js";
import "./capture-monitor.css";
import "./history-pages.css";

function formatTime(value) {
  if (!value) return "Time unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function AlertSignals() {
  const [events, setEvents] = useState([]);
  const [model, setModel] = useState("any");
  const [mode, setMode] = useState("all");
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [updated, setUpdated] = useState(null);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const response = await loadDemoEvents(250);
      setEvents(Array.isArray(response.events) ? response.events.filter((event) => event.simulated === false) : []);
      setError("");
      setUpdated(new Date().toISOString());
    } catch {
      setError("Capture prediction history is unavailable. Check the AI engine connection.");
    } finally {
      setRefreshing(false);
    }
  }, []);

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

  const counts = useMemo(() => ({
    total: events.filter((event) => event.rf_flagged || event.if_flagged).length,
    rf: events.filter((event) => event.rf_flagged).length,
    iso: events.filter((event) => event.if_flagged).length,
    both: events.filter((event) => event.rf_flagged && event.if_flagged).length,
  }), [events]);

  return <div className="page capture-monitor history-page">
    <div className="page-head"><div><div className="kicker">Alerts · experimental model signals</div><h1>Flagged Predictions</h1><p>Review model-flagged results from the latest 250 stored capture predictions.</p></div><button className="secondary-btn" onClick={refresh} disabled={refreshing}><RefreshCw size={13}/>{refreshing ? "Refreshing…" : "Refresh"}</button></div>
    <div className="history-warning"><AlertTriangle size={14}/><span><b>This is not an alert queue.</b> These are experimental Random Forest and Isolation Forest flags. They are not confirmed attacks, persisted alerts, or instructions to block traffic.</span></div>
    <div className="capture-monitor-grid">
      <article className="panel capture-stat"><small>Flagged predictions</small><b>{counts.total}</b><span>Either model flagged</span></article>
      <article className="panel capture-stat"><small>Random Forest</small><b>{counts.rf}</b><span>Classifier threshold exceeded</span></article>
      <article className="panel capture-stat"><small>Isolation Forest</small><b>{counts.iso}</b><span>Anomaly threshold exceeded</span></article>
      <article className="panel capture-stat"><small>Both models flagged</small><b>{counts.both}</b><span>Not analyst-confirmed</span></article>
    </div>
    <section className="panel capture-table-panel">
      <div className="panel-head"><div><h2>Prediction signals</h2><p>{updated ? "Updated " + new Date(updated).toLocaleTimeString() : "Loading history"} · refreshes every 10 seconds</p></div><span className="range"><Clock3 size={12}/>{signals.length} SIGNALS</span></div>
      <div className="history-controls">
        <label className="history-mode"><ShieldAlert size={12}/><select value={model} onChange={(event) => setModel(event.target.value)}><option value="any">Either model</option><option value="both">Both models</option><option value="rf">Random Forest only</option><option value="iso">Isolation Forest only</option></select></label>
        <label className="history-mode"><select value={mode} onChange={(event) => setMode(event.target.value)}><option value="all">All capture modes</option><option value="live">Live capture</option><option value="pcap">PCAP replay</option></select></label>
      </div>
      {error ? <div className="capture-empty"><Database size={18}/><b>Signals unavailable</b><span>{error}</span></div> :
      !signals.length ? <div className="capture-empty"><Database size={18}/><b>{events.length ? "No flagged predictions in this view" : "No capture history available"}</b><span>{events.length ? "Try a different model or capture mode filter." : "Run the authorized capture CLI to save model predictions."}</span></div> :
      <div className="capture-record-list">{signals.map((event) => {
        const both = event.rf_flagged && event.if_flagged;
        const label = both ? "Both flagged" : event.rf_flagged ? "RF flagged" : "IF flagged";
        return <article className="capture-record" key={event.id}>
          <div className="capture-record-origin"><b>{formatTime(event.recorded_at)}</b><span className={"capture-mode-tag " + event.capture_mode}>{event.capture_mode === "live" ? "LIVE CAPTURE" : event.capture_mode === "pcap" ? "PCAP REPLAY" : "MODE UNKNOWN"}</span><small>{event.input_source}</small><small>{event.capture_session_id ? "Session " + event.capture_session_id.slice(0, 8) : "Session not recorded"}</small></div>
          <div className="capture-record-model"><span>Random Forest</span><b className={event.rf_flagged ? "flagged" : ""}>{event.rf_classification}</b><small>{(event.rf_probability * 100).toFixed(1)}% probability · threshold {(event.rf_threshold * 100).toFixed(1)}%</small></div>
          <div className="capture-record-model"><span>Isolation Forest</span><b className={event.if_flagged ? "flagged" : ""}>{event.if_classification}</b><small>{Number(event.if_score).toFixed(4)} anomaly score · threshold {Number(event.if_threshold).toFixed(4)}</small></div>
          <span className="capture-agreement">{label}</span>
        </article>;
      })}</div>}
    </section>
  </div>;
}

