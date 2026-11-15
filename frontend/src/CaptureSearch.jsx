import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Clock3, Database, Filter, RefreshCw, Search, X } from "lucide-react";
import { loadDemoEvents } from "./api.js";
import "./capture-monitor.css";
import "./history-pages.css";

function time(value) {
  if (!value) return "Time unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function CaptureSearch() {
  const [events, setEvents] = useState([]);
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("all");
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [limit, setLimit] = useState(50);
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
      setError("Local capture history is unavailable. Check the AI engine connection.");
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 10000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const matches = useMemo(() => {
    const term = query.trim().toLowerCase();
    return events.filter((event) => {
      const modeMatch = mode === "all" || event.capture_mode === mode;
      const flaggedMatch = !flaggedOnly || event.rf_flagged || event.if_flagged;
      const searchable = [event.recorded_at, event.input_source, event.model_version, event.capture_mode, event.rf_classification, event.if_classification, event.capture_session_id].join(" ").toLowerCase();
      return modeMatch && flaggedMatch && (!term || searchable.includes(term));
    });
  }, [events, flaggedOnly, mode, query]);

  return <div className="page capture-monitor history-page">
    <div className="page-head"><div><div className="kicker">SIEM Search · local research data</div><h1>Capture Prediction Search</h1><p>Search metadata for the latest 250 completed capture predictions.</p></div><button className="secondary-btn" onClick={refresh} disabled={refreshing}><RefreshCw size={13}/>{refreshing ? "Refreshing…" : "Refresh"}</button></div>
    <div className="history-warning"><AlertTriangle size={14}/><span><b>No SIEM is connected.</b> Results are model prediction history only, not security events or confirmed alerts. This search contains no raw features, IP addresses, or packet payloads.</span></div>
    <section className="panel capture-table-panel">
      <div className="panel-head"><div><h2>Search controls</h2><p>Polling every 10 seconds · {updated ? "Updated " + new Date(updated).toLocaleTimeString() : "Loading"}</p></div><span className="range"><Clock3 size={12}/>{events.length} RECORDS</span></div>
      <div className="history-controls">
        <label className="capture-search"><Search size={13}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search source, model, result, or session"/></label>
        <label className="history-mode"><Filter size={12}/><select value={mode} onChange={(event) => setMode(event.target.value)}><option value="all">All modes</option><option value="live">Live capture</option><option value="pcap">PCAP replay</option></select></label>
        <button className={"history-flag-toggle" + (flaggedOnly ? " selected" : "")} onClick={() => setFlaggedOnly((value) => !value)}>{flaggedOnly ? <X size={12}/> : <AlertTriangle size={12}/>}Model flagged</button>
      </div>
      {error ? <div className="capture-empty"><Database size={18}/><b>Search unavailable</b><span>{error}</span></div> :
      !matches.length ? <div className="capture-empty"><Database size={18}/><b>{events.length ? "No matching predictions" : "No capture predictions saved"}</b><span>{events.length ? "Change the filters or search term." : "Run the authorized capture CLI to add completed flow predictions."}</span></div> :
      <><div className="history-results-count">Showing {Math.min(limit, matches.length)} of {matches.length} matches in the latest {events.length} stored records.</div>
        <div className="capture-record-list">{matches.slice(0, limit).map((event) => <article className="capture-record" key={event.id}>
          <div className="capture-record-origin"><b>{time(event.recorded_at)}</b><span className={"capture-mode-tag " + event.capture_mode}>{event.capture_mode === "live" ? "LIVE CAPTURE" : event.capture_mode === "pcap" ? "PCAP REPLAY" : "MODE UNKNOWN"}</span><small>{event.input_source}</small><small>{event.capture_session_id ? "Session " + event.capture_session_id.slice(0, 8) : "Session not recorded"}</small></div>
          <div className="capture-record-model"><span>Random Forest</span><b className={event.rf_flagged ? "flagged" : ""}>{event.rf_classification}</b><small>{(event.rf_probability * 100).toFixed(1)}% probability · threshold {(event.rf_threshold * 100).toFixed(1)}%</small></div>
          <div className="capture-record-model"><span>Isolation Forest</span><b className={event.if_flagged ? "flagged" : ""}>{event.if_classification}</b><small>{Number(event.if_score).toFixed(4)} anomaly score · threshold {Number(event.if_threshold).toFixed(4)}</small></div>
          <span className="capture-agreement">{(event.detector_agreement || "agreement unknown").replaceAll("_", " ")}</span>
        </article>)}</div>
        {matches.length > limit && <button className="secondary-btn history-more" onClick={() => setLimit((value) => Math.min(value + 50, 250))}>Show 50 more</button>}
      </>}
    </section>
  </div>;
}