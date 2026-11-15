import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, BarChart3, Download, RefreshCw } from "lucide-react";
import { loadDemoEvents } from "./api.js";
import "./history-pages.css";

function csvCell(value) {
  const text = value == null ? "" : String(value);
  return "\"" + text.replaceAll("\"", "\"\"") + "\"";
}

function exportCsv(events) {
  const columns = ["recorded_at","capture_mode","input_source","capture_session_id","model_version","rf_classification","rf_probability","rf_flagged","if_classification","if_score","if_flagged","detector_agreement"];
  const rows = [columns, ...events.map((event) => columns.map((key) => event[key]))];
  const blob = new Blob([rows.map((row) => row.map(csvCell).join(",")).join("\r\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "neurosphere-capture-summary.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function Reports() {
  const [events, setEvents] = useState([]);
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
    const timer = window.setInterval(refresh, 30000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const summary = useMemo(() => ({
    total: events.length,
    live: events.filter((event) => event.capture_mode === "live").length,
    pcap: events.filter((event) => event.capture_mode === "pcap").length,
    rfFlagged: events.filter((event) => event.rf_flagged).length,
    ifFlagged: events.filter((event) => event.if_flagged).length,
    bothFlagged: events.filter((event) => event.rf_flagged && event.if_flagged).length,
    disagreement: events.filter((event) => String(event.detector_agreement || "").toLowerCase().includes("disagree")).length,
  }), [events]);

  const modes = useMemo(() => [
    { name: "Live capture", value: summary.live },
    { name: "PCAP replay", value: summary.pcap },
    { name: "Mode unspecified", value: Math.max(0, summary.total - summary.live - summary.pcap) },
  ], [summary]);

  return <div className="page history-page reports-page">
    <div className="page-head"><div><div className="kicker">Reports · local prediction history</div><h1>Capture Summary</h1><p>Aggregate view of the latest 250 stored capture prediction records.</p></div><div className="report-actions"><button className="secondary-btn" onClick={refresh} disabled={refreshing}><RefreshCw size={13}/>{refreshing ? "Refreshing…" : "Refresh"}</button><button className="primary-btn" onClick={() => exportCsv(events)} disabled={!events.length}><Download size={13}/>Export CSV</button></div></div>
    <div className="history-warning"><AlertTriangle size={14}/><span><b>Research summary, not an incident report.</b> Counts describe model flags in bounded prediction history. They are not confirmed attacks, alerts, or blocking actions.</span></div>
    {error && <div className="error history-error">{error}</div>}
    <div className="report-stats">
      <article className="panel report-stat"><small>Records in report window</small><b>{summary.total}</b><span>Latest 250 available</span></article>
      <article className="panel report-stat"><small>Random Forest flagged</small><b>{summary.rfFlagged}</b><span>Experimental model signals</span></article>
      <article className="panel report-stat"><small>Isolation Forest flagged</small><b>{summary.ifFlagged}</b><span>Experimental anomaly signals</span></article>
      <article className="panel report-stat"><small>Both flagged</small><b>{summary.bothFlagged}</b><span>Not analyst-confirmed</span></article>
    </div>
    <div className="reports-grid">
      <section className="panel report-panel"><div className="panel-head"><div><h2>Capture modes</h2><p>Mode is reported by the runner.</p></div><BarChart3 size={15}/></div>
        <div className="report-bars">{modes.map((item) => <div className="report-bar-row" key={item.name}><span>{item.name}</span><div><i style={{width: summary.total ? (item.value / summary.total * 100) + "%" : "0%"}}/></div><b>{item.value}</b></div>)}</div>
      </section>
      <section className="panel report-panel"><div className="panel-head"><div><h2>Detector alignment</h2><p>Based on saved prediction metadata.</p></div></div>
        <div className="report-alignment"><div><span>Both detectors flagged</span><b>{summary.bothFlagged}</b></div><div><span>Recorded disagreement labels</span><b>{summary.disagreement}</b></div><small>Model disagreement is expected; neither output alone confirms an incident.</small></div>
      </section>
    </div>
    <div className="report-footnote">{updated ? "Updated " + new Date(updated).toLocaleString() + " · " : ""}Report includes saved metadata only. It contains no IP addresses, packet payloads, or raw feature vectors.</div>
  </div>;
}