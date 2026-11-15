import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Archive, Clock3, FilePlus2, Link2, MessageSquareText, RefreshCw, Send, ShieldAlert } from "lucide-react";
import { NavLink } from "react-router-dom";
import { addIncidentNote, changeIncidentStatus, createIncident, linkAlertToIncident, loadAlerts, loadIncident, loadIncidents } from "./api.js";
import IncidentSimulation from "./IncidentSimulation.jsx";
import "./incident-management.css";

const labels = { OPEN: "Open", INVESTIGATING: "Investigating", RESOLVED: "Resolved", CLOSED: "Closed" };
const severities = ["LOW","MEDIUM","HIGH","CRITICAL"];
function time(value) { if (!value) return "Time unavailable"; const date=new Date(value); return Number.isNaN(date.getTime())?value:date.toLocaleString(); }
function errorText(error) { const d=error.response?.data?.detail; return typeof d==="string"?d:error.message||"Request failed."; }

function ManagedIncidents({ session }) {
  const token=session?.accessToken;
  const [incidents,setIncidents]=useState([]),[alerts,setAlerts]=useState([]),[detail,setDetail]=useState(null);
  const [selectedId,setSelectedId]=useState(null),[filter,setFilter]=useState("ALL"),[loading,setLoading]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState("");
  const [title,setTitle]=useState(""),[description,setDescription]=useState(""),[severity,setSeverity]=useState("MEDIUM"),[note,setNote]=useState(""),[alertToLink,setAlertToLink]=useState("");

  const refresh=useCallback(async()=>{
    if(!token)return;setLoading(true);
    const [incidentResult,alertResult]=await Promise.allSettled([loadIncidents(token,100),loadAlerts(token,100)]);
    if(incidentResult.status==="fulfilled"){
      const rows=incidentResult.value;setIncidents(rows);setSelectedId(current=>current&&rows.some(x=>x.id===current)?current:rows[0]?.id??null);
    }else setError(errorText(incidentResult.reason));
    if(alertResult.status==="fulfilled")setAlerts(alertResult.value);
    setLoading(false);
  },[token]);

  useEffect(()=>{setIncidents([]);setAlerts([]);setSelectedId(null);setDetail(null);if(token)refresh();},[token,refresh]);
  useEffect(()=>{
    if(!token||selectedId==null){setDetail(null);return;}
    let active=true;loadIncident(token,selectedId).then(x=>{if(active)setDetail(x)}).catch(e=>{if(active)setError(errorText(e))});
    return()=>{active=false};
  },[token,selectedId]);

  async function openIncident(event){
    event.preventDefault();setBusy(true);setError("");
    try{const result=await createIncident(token,{title,description,severity});setTitle("");setDescription("");setSeverity("MEDIUM");await refresh();setSelectedId(result.incident.id);setDetail(result)}
    catch(e){setError(errorText(e))}finally{setBusy(false)}
  }
  async function changeStatus(status){
    setBusy(true);setError("");try{setDetail(await changeIncidentStatus(token,detail.incident.id,status));await refresh()}catch(e){setError(errorText(e))}finally{setBusy(false)}
  }
  async function addNote(event){
    event.preventDefault();if(!note.trim())return;setBusy(true);setError("");
    try{setDetail(await addIncidentNote(token,detail.incident.id,note.trim()));setNote("");await refresh()}catch(e){setError(errorText(e))}finally{setBusy(false)}
  }
  async function addAlertLink(event){
    event.preventDefault();if(!alertToLink)return;setBusy(true);setError("");
    try{setDetail(await linkAlertToIncident(token,detail.incident.id,alertToLink));setAlertToLink("");await refresh()}catch(e){setError(errorText(e))}finally{setBusy(false)}
  }

  if(!token)return <div className="panel incident-login"><ShieldAlert size={18}/><b>Sign in to manage persistent incidents</b><p>Authenticated incidents can link reviewed alerts and retain status changes and notes in MySQL.</p><NavLink to="/login" className="primary-btn">Sign in</NavLink></div>;
  const visible=filter==="ALL"?incidents:incidents.filter(x=>x.status===filter);
  const current=detail?.incident;
  const linkedIds=new Set((detail?.alerts||[]).map(x=>x.id));
  const linkable=alerts.filter(x=>!linkedIds.has(x.id)&&!["RESOLVED","FALSE_POSITIVE"].includes(x.status));
  const counts={open:incidents.filter(x=>x.status==="OPEN").length,investigating:incidents.filter(x=>x.status==="INVESTIGATING").length,resolved:incidents.filter(x=>["RESOLVED","CLOSED"].includes(x.status)).length};

  return <div className="incident-managed">
    <div className="incident-managed-head"><div><div className="kicker">Persisted incidents · analyst workflow</div><h2>Incident records</h2><p>Manually create incidents and link reviewed alert records. No response action is executed.</p></div><button className="secondary-btn" onClick={refresh} disabled={loading}><RefreshCw size={13}/>{loading?"Refreshing…":"Refresh"}</button></div>
    {error&&<div className="error case-error"><AlertTriangle size={13}/>{error}</div>}
    <div className="case-stats"><article className="panel"><small>Open</small><b>{counts.open}</b></article><article className="panel"><small>Investigating</small><b>{counts.investigating}</b></article><article className="panel"><small>Resolved / closed</small><b>{counts.resolved}</b></article><article className="panel"><small>Linked alerts</small><b>{detail?.alerts?.length||0}</b></article></div>
    <div className="case-layout">
      <section className="panel case-list-panel"><div className="panel-head"><div><h3>Incident records</h3><p>Latest 100 · {session.username}</p></div><Archive size={14}/></div>
        <div className="case-filter"><label>Status <select value={filter} onChange={e=>setFilter(e.target.value)}><option value="ALL">All statuses</option>{Object.entries(labels).map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label></div>
        {!visible.length?<div className="case-empty"><Archive size={17}/><b>{incidents.length?"No incidents match this filter":loading?"Loading incidents…":"No incident records yet"}</b><span>{incidents.length?"Choose a different status filter.":"Create an incident after analyst review."}</span></div>:<div className="case-list">{visible.map(item=><button key={item.id} className={"case-list-item"+(selectedId===item.id?" selected":"")} onClick={()=>setSelectedId(item.id)}><span className={"case-priority "+item.severity.toLowerCase()}>{item.severity}</span><b>{item.title}</b><small>{item.incidentKey} · {labels[item.status]}</small><time>{time(item.updatedAt)}</time></button>)}</div>}
      </section>
      <div className="case-column">
        <section className="panel case-create"><div className="panel-head"><div><h3>Create an incident</h3><p>Manual analyst decision · not created automatically by model flags</p></div><FilePlus2 size={14}/></div>
          <form className="case-form" onSubmit={openIncident}><label>Title<input required maxLength={160} value={title} onChange={e=>setTitle(e.target.value)} placeholder="Incident title"/></label><label>Summary<textarea required maxLength={4000} value={description} onChange={e=>setDescription(e.target.value)} placeholder="Describe why this incident was opened."/></label><label>Severity<select value={severity} onChange={e=>setSeverity(e.target.value)}>{severities.map(v=><option key={v}>{v}</option>)}</select></label><button className="primary-btn" disabled={busy}><FilePlus2 size={13}/>{busy?"Saving…":"Create incident"}</button></form>
        </section>
        <section className="panel case-detail">
          {!current?<div className="case-empty"><Archive size={17}/><b>Select an incident</b><span>Details and activity history appear here.</span></div>:<>
            <div className="panel-head"><div><span className="case-key">{current.incidentKey}</span><h3>{current.title}</h3><p>Opened by {current.createdBy} · {time(current.createdAt)}</p></div><span className={"case-priority "+current.severity.toLowerCase()}>{current.severity}</span></div>
            <p className="case-description">{current.description}</p>
            <label className="case-status-control">Status<select disabled={busy} value={current.status} onChange={e=>changeStatus(e.target.value)}>{Object.entries(labels).map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label>
            <div className="incident-linked-alerts"><div className="incident-subhead"><h4>Linked review alerts</h4><span><Link2 size={11}/>{detail.alerts.length}</span></div>
              {detail.alerts.map(alert=><div className="incident-alert-item" key={alert.id}><b>{alert.alertKey} · {alert.title}</b><small>{alert.severity} · {alert.status.replaceAll("_"," ")} · source {alert.sourceReference.slice(0,8)}</small></div>)}
              <form className="incident-link-form" onSubmit={addAlertLink}><select value={alertToLink} onChange={e=>setAlertToLink(e.target.value)}><option value="">Select an open review alert</option>{linkable.map(alert=><option key={alert.id} value={alert.id}>{alert.alertKey} · {alert.title}</option>)}</select><button className="secondary-btn small" disabled={busy||!alertToLink}><Link2 size={11}/>Link alert</button></form>
            </div>
            <div className="case-activity-head"><h4>Activity history</h4><span><Clock3 size={11}/>{detail.activity.length} entries</span></div>
            <div className="case-activity">{detail.activity.map(item=><article key={item.id}><i/><div><b>{item.action.replaceAll("_"," ")}</b><p>{item.details}</p><small>{item.actor} · {time(item.createdAt)}</small></div></article>)}</div>
            <form className="case-note-form" onSubmit={addNote}><label><MessageSquareText size={13}/>Add analyst note</label><textarea maxLength={2000} value={note} onChange={e=>setNote(e.target.value)} placeholder="Add investigation context" required/><button className="secondary-btn" disabled={busy}><Send size={12}/>Add note</button></form>
          </>}
        </section>
      </div>
    </div>
  </div>;
}

export default function IncidentManagement({session}) {
  const [view,setView]=useState(session?.accessToken?"managed":"demo");
  useEffect(()=>{if(session?.accessToken)setView("managed")},[session?.accessToken]);
  return <div className="incident-views"><div className="incident-view-switch"><button className={view==="managed"?"selected":""} onClick={()=>setView("managed")}>Persistent incidents</button><button className={view==="demo"?"selected":""} onClick={()=>setView("demo")}>Demo scenarios</button></div>{view==="demo"?<IncidentSimulation/>:<ManagedIncidents session={session}/>}</div>;
}

