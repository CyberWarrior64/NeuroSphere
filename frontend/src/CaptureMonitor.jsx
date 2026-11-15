import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, Clock3, Database, FileText, RefreshCw, Search, Wifi } from "lucide-react";
import { loadCaptureRunnerStatus, loadDemoEvents } from "./api.js";
import "./capture-monitor.css";

function formatTime(value) {
  if (!value) return "Time unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function stateLabel(status) {
  if (status === "running") return "Runner active";
  if (status === "stale") return "Heartbeat stale";
  if (status === "stopped") return "Last runner stopped";
  if (status === "idle") return "No runner session";
  return "Status unavailable";
}

export default function CaptureMonitor() {
  const [events, setEvents] = useState([]);
  const [runner, setRunner] = useState(null);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    const results = await Promise.allSettled([loadDemoEvents(100), loadCaptureRunnerStatus()]);
    if (results[0].status === "fulfilled") {
      setEvents(Array.isArray(results[0].value.events)
        ? results[0].value.events.filter((event) => event.simulated === false)
        : []);
      setError("");
    } else {
      setError("Capture history is unavailable. Check the AI engine connection.");
    }
    if (results[1].status === "fulfilled") {
      setRunner(results[1].value);
    } else {
      setRunner({ status: "unavailable" });
    }
    setLastUpdated(new Date().toISOString());
    setRefreshing(false);
  }, []);

  useEffect(() => {
    let active = true;
    const update = async () => {
      if (active) await refresh();
    };
    update();
    const timer = window.setInterval(update, 10000);
    return () => { active = false; window.clearInterval(timer); };
  }, [refresh]);

  const visibleEvents = useMemo(() => {
    const query = search.trim().toLowerCase();
    return events.filter((event) => {
      const modeMatches = filter === "all" || event.capture_mode === filter;
      const text = [event.input_source, event.model_version, event.rf_classification, event.if_classification, event.capture_session_id].join(" ").toLowerCase();
      return modeMatches && (!query || text.includes(query));
    });
  }, [events, filter, search]);

  const liveCount = events.filter((event) => event.capture_mode === "live").length;
  const pcapCount = events.filter((event) => event.capture_mode === "pcap").length;
  const flaggedCount = events.filter((event) => event.rf_flagged || event.if_flagged).length;
  const runnerState = runner?.status || "unavailable";

  return <div className="page capture-monitor">
    <div className="page-head">
      <div><div className="kicker">Network watch · completed flow predictions</div><h1>Real-time Monitor</h1><p>Recent capture-runner output, polled from the local metadata store.</p></div>
      <button className="secondary-btn" onClick={refresh} disabled={refreshing}><RefreshCw size={13}/>{refreshing ? "Refreshing…" : "Refresh"}</button>
    </div>
    <div className="capture-monitor-warning"><Activity size={15}/><span><b>Experimental model signals, not alerts.</b> This view updates every 10 seconds and displays completed flows only. It contains no IP addresses, packet payloads, or raw feature vectors.</span></div>
    <div className="capture-monitor-grid">
      <article className="panel capture-stat"><small>Recent records</small><b>{events.length}</b><span>Bounded local history · latest 100 shown</span></article>
      <article className="panel capture-stat"><small>Live capture</small><b>{liveCount}</b><span>Records in current history window</span></article>
      <article className="panel capture-stat"><small>PCAP replay</small><b>{pcapCount}</b><span>Records in current history window</span></article>
      <article className="panel capture-stat"><small>Detector signals</small><b>{flaggedCount}</b><span>At least one model flagged · not confirmed incidents</span></article>
    </div>
    <section className="panel capture-runner-panel">
      <div className="panel-head"><div><h2>Manual capture runner</h2><p>Client-reported status · no independent sensor attestation</p></div><span className={"record-status " + (runnerState === "running" ? "online" : runnerState === "stale" ? "offline" : "loading")}>{stateLabel(runnerState).toUpperCase()}</span></div>
      <div className="capture-runner-details"><span><Wifi size={13}/>{runner?.capture_mode === "live" ? "Live interface mode" : runner?.capture_mode === "pcap" ? "PCAP replay mode" : "No active capture mode"}</span><span><Clock3 size={13}/>{runner?.last_heartbeat_at ? "Last heartbeat " + formatTime(runner.last_heartbeat_at) : "No heartbeat recorded"}</span><span>{runner?.active_sessions || 0} active runner session{runner?.active_sessions === 1 ? "" : "s"}</span></div>
    </section>
    <section className="panel capture-table-panel">
      <div className="panel-head"><div><h2>Capture prediction history</h2><p>Latest 100 records · refreshes every 10 seconds</p></div><span className="range">{lastUpdated ? "UPDATED " + new Date(lastUpdated).toLocaleTimeString() : "WAITING"}</span></div>
      <div className="capture-table-controls">
        <div className="capture-filters">{[["all","All"],["live","Live"],["pcap","PCAP"]].map(([value,label]) => <button key={value} className={filter === value ? "selected" : ""} onClick={() => setFilter(value)}>{label}</button>)}</div>
        <label className="capture-search"><Search size={13}/><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search source or model"/></label>
      </div>
      {error ? <div className="capture-empty"><Database size={18}/><b>Capture history unavailable</b><span>{error}</span></div> :
      !visibleEvents.length ? <div className="capture-empty"><FileText size={18}/><b>{events.length ? "No matching records" : "No capture predictions yet"}</b><span>{events.length ? "Try another mode or search term." : "Run an authorized live capture or PCAP replay. Results will appear after completed flows are analyzed."}</span></div> :
      <div className="capture-record-list">{visibleEvents.map((event) => <article className="capture-record" key={event.id}>
        <div className="capture-record-origin"><b>{formatTime(event.recorded_at)}</b><span className={"capture-mode-tag " + event.capture_mode}>{event.capture_mode === "live" ? "LIVE CAPTURE" : event.capture_mode === "pcap" ? "PCAP REPLAY" : "MODE UNKNOWN"}</span><small>{event.input_source}</small><small>{event.capture_session_id ? "Session " + event.capture_session_id.slice(0, 8) : "Session not recorded"}</small><small>{event.model_version}</small></div>
        <div className="capture-record-model"><span>Random Forest</span><b className={event.rf_flagged ? "flagged" : ""}>{event.rf_classification}</b><small>{(event.rf_probability * 100).toFixed(1)}% probability · threshold {(event.rf_threshold * 100).toFixed(1)}%</small></div>
        <div className="capture-record-model"><span>Isolation Forest</span><b className={event.if_flagged ? "flagged" : ""}>{event.if_classification}</b><small>{Number(event.if_score).toFixed(4)} anomaly score · threshold {Number(event.if_threshold).toFixed(4)}</small></div>
        <span className="capture-agreement">{(event.detector_agreement || "agreement unknown").replaceAll("_", " ")}</span>
      </article>)}</div>}
    </section>
  </div>;
}