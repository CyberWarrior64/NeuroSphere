import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, ClipboardList, Download, LockKeyhole, RefreshCw, ShieldCheck } from "lucide-react";
import { NavLink } from "react-router-dom";
import { loadAuditEvents } from "./api.js";
import { displayUsername } from "./display.js";
import "./audit-log.css";

function displayTime(value) {
  if (!value) return "Time unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function csvValue(value) {
  let text = value == null ? "" : String(value);
  if (/^[\s]*[=+@\-]/.test(text)) text = "'" + text;
  return `"${text.replaceAll('"', '""')}"`;
}

function exportCsv(events) {
  const columns = ["occurredAt", "actor", "action", "targetType", "targetId", "summary"];
  const content = [columns, ...events.map((event) => columns.map((column) => event[column]))]
    .map((row) => row.map(csvValue).join(",")).join("\r\n");
  const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "neurosphere-audit-events.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function AuditLog({ session }) {
  const token = session?.accessToken;
  const isAdmin = session?.roles?.includes("ADMIN");
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [actorFilter, setActorFilter] = useState("");
  const [actionFilter, setActionFilter] = useState("ALL");

  const refresh = useCallback(async () => {
    if (!token || !isAdmin) return;
    setLoading(true);
    try {
      const result = await loadAuditEvents(token, 200);
      setEvents(Array.isArray(result) ? result : []);
      setError("");
    } catch (requestError) {
      const status = requestError.response?.status;
      setError(status === 401 ? "Your platform session expired. Sign in again to view the audit log."
        : status === 403 ? "Your account does not have administrator access to this audit log."
          : "The audit log could not be loaded. Check that the platform API is running.");
    } finally {
      setLoading(false);
    }
  }, [token, isAdmin]);

  useEffect(() => {
    setEvents([]);
    if (!token || !isAdmin) return undefined;
    refresh();
    const timer = window.setInterval(refresh, 30000);
    return () => window.clearInterval(timer);
  }, [token, isAdmin, refresh]);

  const actions = useMemo(() => [...new Set(events.map((event) => event.action))].sort(), [events]);
  const visibleEvents = useMemo(() => events.filter((event) =>
    (actionFilter === "ALL" || event.action === actionFilter)
      && (!actorFilter.trim() || event.actor.toLowerCase().includes(actorFilter.trim().toLowerCase()) || displayUsername(event.actor).toLowerCase().includes(actorFilter.trim().toLowerCase()))),
  [events, actionFilter, actorFilter]);

  if (!token) return <div className="page audit-page"><div className="page-head"><div><div className="kicker">Platform security</div><h1>Audit log</h1><p>Review recent analyst actions across platform workflows.</p></div></div><section className="panel audit-gate"><LockKeyhole size={19}/><b>Sign in to continue</b><p>The audit log is restricted to platform administrators.</p><NavLink to="/login" className="primary-btn">Sign in</NavLink></section></div>;

  if (!isAdmin) return <div className="page audit-page"><div className="page-head"><div><div className="kicker">Platform security</div><h1>Audit log</h1><p>Review recent analyst actions across platform workflows.</p></div></div><section className="panel audit-gate"><LockKeyhole size={19}/><b>Administrator access required</b><p>Your current platform role cannot read this log.</p></section></div>;

  return <div className="page audit-page">
    <div className="page-head"><div><div className="kicker">Platform security · administrator view</div><h1>Audit log</h1><p>Recent actions across case, review alert, and incident workflows.</p></div><div className="audit-actions"><button className="secondary-btn" onClick={refresh} disabled={loading}><RefreshCw size={13}/>{loading ? "Refreshing…" : "Refresh"}</button><button className="primary-btn" onClick={() => exportCsv(visibleEvents)} disabled={!visibleEvents.length}><Download size={13}/>Export CSV</button></div></div>
    <div className="audit-notice"><ShieldCheck size={14}/><span>Entries are written with their workflow changes. Notes, analyst rationales, packet fields, and source addresses are omitted. This view shows up to the latest 200 events; older entries remain in MySQL.</span></div>
    {error && <div className="error audit-error"><AlertTriangle size={13}/>{error}</div>}
    <section className="panel audit-panel">
      <div className="panel-head"><div><h2>Workflow activity</h2><p>{events.length} of the latest 200 entries</p></div><ClipboardList size={15}/></div>
      <div className="audit-filters"><label>Analyst <input type="search" value={actorFilter} onChange={(event) => setActorFilter(event.target.value)} placeholder="Filter by username"/></label><label>Action <select value={actionFilter} onChange={(event) => setActionFilter(event.target.value)}><option value="ALL">All actions</option>{actions.map((action) => <option key={action} value={action}>{action.replaceAll("_", " ")}</option>)}</select></label><span>{visibleEvents.length} shown</span></div>
      {!visibleEvents.length ? <div className="audit-empty"><ClipboardList size={18}/><b>{loading ? "Loading audit events…" : events.length ? "No events match these filters" : "No workflow events recorded yet"}</b><span>Case, alert, and incident actions performed after this feature is deployed will appear here.</span></div> : <div className="audit-table-wrap"><table className="audit-table"><thead><tr><th>Time</th><th>Analyst</th><th>Action</th><th>Record</th><th>Summary</th></tr></thead><tbody>{visibleEvents.map((event) => <tr key={event.id}><td><time>{displayTime(event.occurredAt)}</time></td><td className="audit-actor">{displayUsername(event.actor)}</td><td><span className="audit-action">{event.action.replaceAll("_", " ")}</span></td><td><span className="audit-target">{event.targetType} · {event.targetId}</span></td><td>{event.summary}</td></tr>)}</tbody></table></div>}
    </section>
    <p className="audit-footnote">Audit events are append-only through the application API and share the transaction of the change they describe. Database administrators can still alter database contents; use restricted database credentials and protected backups for stronger tamper resistance.</p>
  </div>;
}
