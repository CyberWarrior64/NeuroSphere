import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Archive, Clock3, FilePlus2, LockKeyhole, MessageSquareText, RefreshCw, Send, ShieldCheck } from "lucide-react";
import { NavLink } from "react-router-dom";
import { addCaseNote, changeCaseStatus, createCase, loadCase, loadCases } from "./api.js";
import { displayUsername } from "./display.js";
import "./case-management.css";

const statusLabels = { OPEN: "Open", INVESTIGATING: "Investigating", RESOLVED: "Resolved", CLOSED: "Closed" };
const priorities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

function displayTime(value) {
  if (!value) return "Time unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function messageFor(error) {
  const detail = error.response?.data?.detail;
  return typeof detail === "string" ? detail : error.message || "The platform API request failed.";
}

export default function CaseManagement({ session }) {
  const token = session?.accessToken;
  const [cases, setCases] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [filter, setFilter] = useState("ALL");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("MEDIUM");
  const [note, setNote] = useState("");

  const refresh = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const records = await loadCases(token, 100);
      setCases(records);
      setSelectedId((current) => current && records.some((item) => item.id === current) ? current : records[0]?.id ?? null);
      setError("");
    } catch (requestError) {
      setError(messageFor(requestError));
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    setCases([]);
    setSelectedId(null);
    setDetail(null);
    if (token) refresh();
  }, [token, refresh]);

  useEffect(() => {
    if (!token || selectedId == null) {
      setDetail(null);
      return;
    }
    let active = true;
    loadCase(token, selectedId).then((value) => {
      if (active) setDetail(value);
    }).catch((requestError) => {
      if (active) setError(messageFor(requestError));
    });
    return () => { active = false; };
  }, [token, selectedId]);

  async function submitCase(event) {
    event.preventDefault();
    if (!token) return;
    setBusy(true);
    setError("");
    try {
      const created = await createCase(token, { title, description, priority, sourceType: "MANUAL" });
      setTitle("");
      setDescription("");
      setPriority("MEDIUM");
      await refresh();
      setSelectedId(created.caseRecord.id);
      setDetail(created);
    } catch (requestError) {
      setError(messageFor(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function updateStatus(value) {
    if (!token || !detail) return;
    setBusy(true);
    setError("");
    try {
      setDetail(await changeCaseStatus(token, detail.caseRecord.id, value));
      await refresh();
    } catch (requestError) {
      setError(messageFor(requestError));
    } finally {
      setBusy(false);
    }
  }

  async function submitNote(event) {
    event.preventDefault();
    if (!token || !detail || !note.trim()) return;
    setBusy(true);
    setError("");
    try {
      setDetail(await addCaseNote(token, detail.caseRecord.id, note.trim()));
      setNote("");
      await refresh();
    } catch (requestError) {
      setError(messageFor(requestError));
    } finally {
      setBusy(false);
    }
  }

  if (!token) return <div className="page"><div className="page-head"><div><div className="kicker">Case management · authenticated workflow</div><h1>Cases</h1><p>Persistent case records require a platform account.</p></div></div><section className="panel case-login"><LockKeyhole size={19}/><b>Sign in to manage cases</b><p>Cases are stored in MySQL and their status changes and notes are recorded in an activity history.</p><NavLink to="/login" className="primary-btn">Sign in</NavLink></section></div>;

  const current = detail?.caseRecord;
  const visibleCases = filter === "ALL" ? cases : cases.filter((item) => item.status === filter);
  const counts = { open: cases.filter((item) => item.status === "OPEN").length, investigating: cases.filter((item) => item.status === "INVESTIGATING").length, resolved: cases.filter((item) => item.status === "RESOLVED" || item.status === "CLOSED").length };

  return <div className="page case-page">
    <div className="page-head"><div><div className="kicker">Case management · persistent platform workflow</div><h1>Cases</h1><p>Create analyst-reviewed records, track status, and keep an auditable activity history.</p></div><button className="secondary-btn" onClick={refresh} disabled={loading}><RefreshCw size={13}/>{loading ? "Refreshing…" : "Refresh"}</button></div>
    <div className="case-notice"><ShieldCheck size={14}/><span>Cases are separate from model predictions. Create a case only after analyst review; no alerts, IP addresses, or packet data are created automatically.</span></div>
    {error && <div className="error case-error"><AlertTriangle size={13}/>{error}</div>}
    <div className="case-stats"><article className="panel"><small>Open</small><b>{counts.open}</b></article><article className="panel"><small>Investigating</small><b>{counts.investigating}</b></article><article className="panel"><small>Resolved / closed</small><b>{counts.resolved}</b></article><article className="panel"><small>Showing</small><b>{cases.length}</b></article></div>
    <div className="case-layout">
      <section className="panel case-list-panel"><div className="panel-head"><div><h2>Case records</h2><p>Latest 100 · signed in as {displayUsername(session.username)}</p></div><Archive size={15}/></div>
        <div className="case-filter"><label>Status <select value={filter} onChange={(event) => setFilter(event.target.value)}><option value="ALL">All statuses</option>{Object.entries(statusLabels).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label></div>
        {!visibleCases.length ? <div className="case-empty"><Archive size={18}/><b>{loading ? "Loading cases…" : cases.length ? "No cases match this status" : "No case records yet"}</b><span>{cases.length ? "Choose another status filter." : "Create a record after analyst review using the form."}</span></div> :
          <div className="case-list">{visibleCases.map((item) => <button key={item.id} className={"case-list-item" + (selectedId === item.id ? " selected" : "")} onClick={() => setSelectedId(item.id)}><span className={"case-priority " + item.priority.toLowerCase()}>{item.priority}</span><b>{item.title}</b><small>{item.caseKey} · {statusLabels[item.status] || item.status}</small><time>{displayTime(item.updatedAt)}</time></button>)}</div>}
      </section>
      <div className="case-column">
        <section className="panel case-create"><div className="panel-head"><div><h2>Open a reviewed case</h2><p>Manual analyst entry · fields are validated by the API</p></div><FilePlus2 size={15}/></div>
          <form className="case-form" onSubmit={submitCase}><label>Title<input required maxLength={160} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Short case title"/></label><label>Summary<textarea required maxLength={4000} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Record the analyst's reason for opening this case."/></label><label>Priority<select value={priority} onChange={(event) => setPriority(event.target.value)}>{priorities.map((value)=><option key={value} value={value}>{value}</option>)}</select></label><button className="primary-btn" disabled={busy}><FilePlus2 size={13}/>{busy ? "Saving…" : "Create case"}</button></form>
        </section>
        <section className="panel case-detail">
          {!current ? <div className="case-empty"><Archive size={18}/><b>Select a case</b><span>Case details and activity will appear here.</span></div> : <>
            <div className="panel-head"><div><span className="case-key">{current.caseKey}</span><h2>{current.title}</h2><p>Created by {displayUsername(current.createdBy)} · {displayTime(current.createdAt)}</p></div><span className={"case-priority " + current.priority.toLowerCase()}>{current.priority}</span></div>
            <p className="case-description">{current.description}</p>
            <div className="case-meta"><span>Source: {current.sourceType === "CAPTURE_PREDICTION" ? "Analyst-linked prediction" : "Manual"}</span><span>Last updated: {displayTime(current.updatedAt)}</span></div>
            <label className="case-status-control">Status<select disabled={busy} value={current.status} onChange={(event) => updateStatus(event.target.value)}>{Object.entries(statusLabels).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
            <div className="case-activity-head"><h3>Activity history</h3><span><Clock3 size={11}/>{detail.activity.length} entries</span></div>
            <div className="case-activity">{detail.activity.map((item) => <article key={item.id}><i/><div><b>{item.action.replaceAll("_"," ")}</b><p>{item.details}</p><small>{displayUsername(item.actor)} · {displayTime(item.createdAt)}</small></div></article>)}</div>
            <form className="case-note-form" onSubmit={submitNote}><label htmlFor="case-note"><MessageSquareText size={13}/>Add an analyst note</label><textarea id="case-note" maxLength={2000} value={note} onChange={(event) => setNote(event.target.value)} placeholder="Add context or a review note" required/><button className="secondary-btn" disabled={busy}><Send size={12}/>Add note</button></form>
          </>}
        </section>
      </div>
    </div>
  </div>;
}

