import { useEffect, useMemo, useState } from "react";
import { NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { Activity, AlertTriangle, Archive, Bell, Blocks, BookOpenCheck, Bot, Bug, ChevronDown, ChevronRight, ClipboardList, Clock3, Cpu, Database, FileBarChart2, FileSearch, Globe2, LayoutDashboard, ListFilter, LockKeyhole, Network, Plus, Radar, Server, Settings, Shield, ShieldAlert, ShieldCheck, Siren, Upload, Wifi, LogIn, LogOut } from "lucide-react";
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import TwinLab from "./TwinLab.jsx";
import CaptureMonitor from "./CaptureMonitor.jsx";
import NetworkWatch from "./NetworkWatch.jsx";
import CaptureSearch from "./CaptureSearch.jsx";
import Reports from "./Reports.jsx";
import AlertSignals from "./AlertSignals.jsx";
import IncidentManagement from "./IncidentManagement.jsx";
import CaseManagement from "./CaseManagement.jsx";
import AuditLog from "./AuditLog.jsx";
import { EndpointSecurity, ThreatIntelligence, VulnerabilityManagement, Playbooks } from "./DemoModules.jsx";
import { analyzeFlow, changePlatformPassword, loadAlerts, loadCaptureRunnerStatus, loadCases, loadCowrieStatus, loadDemoEvents, loadEndpointTelemetry, loadEngineStatus, loadIncidents, loadPlatformStatus, loadRecentAnalyses, loadThreatFeedStatus, loginToPlatform, logoutFromPlatform, resetPlatformPassword, PLATFORM_API_URL } from "./api.js";
import "./settings.css";
import "./dashboard-live.css";

const nav = [["Overview","/",LayoutDashboard],["Real-time Monitor","/monitor",Activity],["SIEM Search","/search",FileSearch],["Alerts","/alerts",Bell],["Incidents","/incidents",ShieldAlert],["Endpoint Security","/endpoints",Cpu],["Network Watch","/network",Network],["Digital Twin","/twin",Blocks],["Threat Intelligence","/threat-intel",Globe2],["Vulnerability Mgmt","/vulnerabilities",Bug],["Case Management","/cases",Archive],["Reports","/reports",FileBarChart2],["Playbooks","/playbooks",BookOpenCheck],["Settings","/settings",Settings]];
const topNav = [["Dashboard","/",LayoutDashboard],["Alerts","/alerts",Bell],["Incidents","/incidents",Shield],["Threat Intel","/threat-intel",Radar],["Reports","/reports",FileBarChart2],["Cases","/cases",Archive],["Playbooks","/playbooks",Blocks],["Sign in","/login",LogIn]];
function Dot({state="muted"}){return <i className={"dot "+state}/>;}

function Header({online,session,onSignOut}){
  return <header className="topbar">
    <NavLink to="/" className="brand"><span className="brand-mark"><ShieldCheck size={21}/></span><span><b>NEUROSPHERE</b><small>SECURITY OPERATIONS</small></span></NavLink>
    <nav className="topnav">{topNav.map(([label,path,Icon])=><NavLink key={path+label} to={path} end={path==="/"} className={({isActive})=>"toplink"+(isActive?" selected":"")}><Icon size={15}/>{label}</NavLink>)}</nav>
    <div className="head-actions"><span className="mode"><Dot state="online"/>RESEARCH</span><button className="iconbtn" aria-label="Notifications"><Bell size={17}/></button><NavLink to="/settings" className="iconbtn" aria-label="Open settings"><Settings size={17}/></NavLink><NavLink to={session?"/settings":"/login"} className="analyst" title={session?"Open analyst settings":"Sign in to configure analyst access"} aria-label={session?"Open analyst settings":"Sign in as analyst"}><span>{session?"AU":"NS"}</span><div><b>{session?session.username:"Local analyst"}</b><small>{session?session.roles.join(", ")||"Platform user":"Research mode"}</small></div><ChevronDown size={13}/></NavLink>{session&&<button className="logout-btn" onClick={onSignOut}><LogOut size={13}/>Sign out</button>}<NavLink to="/login" className="login-head-link">{session?"Session":"Sign in"}</NavLink><span className="online-label"><Dot state={online?"online":"offline"}/>{online?"Engine online":"Engine offline"}</span></div>
  </header>;
}

function Sidebar({online,captureStatus,endpointTelemetry,cowrieStatus,threatFeedStatus,session}){
  const captureMode=captureStatus?.capture_mode==="live"?"Live capture":captureStatus?.capture_mode==="pcap"?"PCAP replay":"Live / PCAP · manual CLI";
  const captureLabel=captureStatus?.status==="running"?"Running":captureStatus?.status==="stale"?"Stale":captureStatus?.status==="stopped"?"Stopped":captureStatus?.status==="idle"?"Not run":"Checking";
  const endpointOnline=endpointTelemetry?.status==="connected";
  const cowrieOnline=cowrieStatus?.status==="connected";
  const cowrieLabel=cowrieOnline?"Connected":cowrieStatus?.status==="unsafe_bind"?"Unsafe bind":cowrieStatus?.status==="stopped"?"Stopped":"Not linked";
  const feedOnline=threatFeedStatus?.status==="connected";
  const feedLabel=feedOnline?"Connected":threatFeedStatus?.status==="stale"?"Stale":threatFeedStatus?.status==="unavailable"?"Unavailable":"Checking";
  const feedNote=threatFeedStatus?.indicator_count!=null?`${threatFeedStatus.indicator_count} public IP indicators`:"Emerging Threats · public feed";
  const sources=[["AI Detection Engine","Hybrid V2 · 67 features",Bot,online,online?"Online":"Offline"],["Network Capture",captureMode,Wifi,captureStatus?.status==="running",captureLabel],["Endpoint Logs",endpointOnline?endpointTelemetry.hostname:"Linux host telemetry",Server,endpointOnline,endpointOnline?"Connected":"Not linked"],["Deception Sensor",cowrieOnline?"Cowrie · loopback lab":"Cowrie honeypot",Bug,cowrieOnline,cowrieLabel],["Threat Feeds",feedNote,Globe2,feedOnline,feedLabel]];
  const visibleNav=session?.roles?.includes("ADMIN")?[...nav.slice(0,-1),["Audit log","/audit",ClipboardList],nav[nav.length-1]]:nav;
  return <aside className="sidebar"><div className="side-scroll"><div className="nav-caption">OPERATIONS</div><nav className="sidenav">{visibleNav.map(([label,path,Icon])=><NavLink key={path} to={path} end={path==="/"} className={({isActive})=>"sidelink"+(isActive?" selected":"")}><Icon size={15}/><span>{label}</span>{label==="Alerts"&&<small>—</small>}</NavLink>)}</nav>
    <section className="sources"><div className="sources-head">DATA SOURCES<button aria-label="Add source"><Plus size={13}/></button></div>{sources.map(([name,note,Icon,ok,state])=><div className="source" key={name}><Icon size={13}/><div><b>{name}</b><small>{note}</small></div><Dot state={ok?"online":"muted"}/><span>{state}</span></div>)}<div className="sources-foot">{[online,captureStatus?.status==="running",endpointOnline,cowrieOnline,feedOnline].filter(Boolean).length} of 5 sources reporting<ChevronRight size={12}/></div></section>
    <div className="secure-note"><LockKeyhole size={13}/>Loopback service · no public exposure</div></div><div className="side-foot">NEUROSPHERE V2 <span>0.1 · Research build</span></div></aside>;
}

function PageHead({kicker,title,subtitle,children}){return <div className="page-head"><div><div className="kicker">{kicker}</div><h1>{title}</h1><p>{subtitle}</p></div>{children&&<div>{children}</div>}</div>;}
function Metric({icon:Icon,label,value,detail,color,state}){return <article className={"metric "+color}><div className="metric-row"><span><Icon size={17}/></span>{state&&<small className={"metric-state "+state}>{state==="online"?"Operational":state==="offline"?"Unavailable":"No feed"}</small>}</div><div className="metric-label">{label}</div><b>{value}</b><small>{detail}</small></article>;}
function Empty({icon:Icon=Database,title,text,children}){return <div className="empty"><span><Icon size={19}/></span><b>{title}</b><p>{text}</p>{children}</div>;}

function SessionTrend({detections}){
  const data=useMemo(()=>detections.slice(0,12).reverse().map((entry,i)=>({time:new Date(entry.time).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit",second:"2-digit"}),probability:Math.round(entry.probability*1000)/10,idx:i+1})),[detections]);
  if(!data.length)return <Empty icon={Activity} title="No session analyses yet" text="Analyze an imported flow to build a session-only trend."/>;
  return <div className="trend-chart"><ResponsiveContainer width="100%" height={180}><AreaChart data={data} margin={{top:8,right:8,left:-22,bottom:0}}><defs><linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#45c9ba" stopOpacity={.28}/><stop offset="95%" stopColor="#45c9ba" stopOpacity={.01}/></linearGradient></defs><CartesianGrid stroke="#e3e9f1" strokeDasharray="3 5" vertical={false}/><XAxis dataKey="time" tick={{fill:"#60728a",fontSize:9}} axisLine={false} tickLine={false}/><YAxis domain={[0,100]} unit="%" tick={{fill:"#60728a",fontSize:9}} axisLine={false} tickLine={false}/><Tooltip contentStyle={{background:"#ffffff",border:"1px solid #d5dfeb",borderRadius:7,color:"#15243a",boxShadow:"0 5px 18px rgb(24 43 68 / 12%)"}} formatter={v=>[v+"%","RF attack probability"]}/><Area type="monotone" dataKey="probability" stroke="#168d84" strokeWidth={2} fill="url(#trendFill)"/></AreaChart></ResponsiveContainer></div>;
}

const DEMO_CASES=[
  {caseKey:"DEMO-024",title:"Repeated connection attempts",priority:"HIGH",status:"INVESTIGATING",updatedAt:"12m ago"},
  {caseKey:"DEMO-023",title:"Unusual outbound flow",priority:"MEDIUM",status:"OPEN",updatedAt:"38m ago"},
  {caseKey:"DEMO-022",title:"Service discovery pattern",priority:"LOW",status:"OPEN",updatedAt:"1h ago"},
];
const CASE_STATUS_LABELS={OPEN:"Open",INVESTIGATING:"Investigating",RESOLVED:"Resolved",CLOSED:"Closed"};

function relativeCaseTime(value){
  if(!value)return "Time unavailable";
  const timestamp=new Date(value).getTime();
  if(!Number.isFinite(timestamp))return value;
  const minutes=Math.max(0,Math.floor((Date.now()-timestamp)/60000));
  if(minutes<1)return "Just now";
  if(minutes<60)return `${minutes}m ago`;
  const hours=Math.floor(minutes/60);
  if(hours<24)return `${hours}h ago`;
  return `${Math.floor(hours/24)}d ago`;
}

function RecentCasesPanel({demoMode,session,state,go,setDemoMode}){
  const demoPreview=demoMode&&!session?.accessToken;
  const rows=demoPreview?DEMO_CASES:state.cases;
  return <section className="panel recent-cases"><div className="panel-head"><div><h2>Recent cases</h2><p>{demoPreview?"Fictional investigation examples · demo":"Persistent investigation records"}</p></div><button className="text-btn" onClick={()=>go("/cases")}>View all <ChevronRight size={12}/></button></div>
    {demoPreview?<div className="demo-cases">{rows.map(item=><div key={item.caseKey}><b>{item.title}</b><small>{item.caseKey} · {CASE_STATUS_LABELS[item.status]}</small><span className={"severity "+item.priority.toLowerCase()}>{item.priority}</span><em>{item.updatedAt}</em></div>)}</div>
      :session?.accessToken?state.status==="loading"?<Empty icon={Archive} title="Loading cases" text="Checking saved case records from the platform API."/>:state.status==="online"?rows.length?<div className="demo-cases">{rows.map(item=><div key={item.id}><b>{item.title}</b><small>{item.caseKey} · {CASE_STATUS_LABELS[item.status]||item.status}</small><span className={"severity "+String(item.priority||"low").toLowerCase()}>{item.priority}</span><em>{relativeCaseTime(item.updatedAt)}</em></div>)}</div>:<Empty icon={Archive} title="No saved cases yet" text="Open a case after analyst review to track its status and investigation notes."><button className="text-btn" onClick={()=>go("/cases")}>Create a case <ChevronRight size={12}/></button></Empty>:<Empty icon={Archive} title="Cases could not be loaded" text={state.error||"The platform API did not return case records."}><button className="text-btn" onClick={()=>go(state.requiresSignIn?"/login":"/cases")}>{state.requiresSignIn?"Sign in again":"Open case management"} <ChevronRight size={12}/></button></Empty>
      :<Empty icon={Archive} title="Sign in to view saved cases" text="Persistent cases are protected by analyst sign-in. Demo examples are clearly marked as simulated."><div className="case-preview-actions"><button className="secondary-btn small" onClick={()=>go("/login")}>Sign in</button><button className="text-btn" onClick={()=>setDemoMode(true)}>Show demo cases</button></div></Empty>}
  </section>;
}

function DashboardAlertDistribution({demoMode,session,state,go}){
  const colors={CRITICAL:"#ef5368",HIGH:"#f29435",MEDIUM:"#5c99f5",LOW:"#7c6be8"};
  if(demoMode)return <div className="demo-distribution"><div className="donut-wrap"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={DEMO_SEVERITIES} dataKey="value" nameKey="name" innerRadius={43} outerRadius={63} paddingAngle={3} stroke="none">{DEMO_SEVERITIES.map(x=><Cell key={x.name} fill={x.color}/>)}</Pie><Tooltip contentStyle={{background:"#ffffff",border:"1px solid #d5dfeb",borderRadius:7,color:"#15243a",boxShadow:"0 5px 18px rgb(24 43 68 / 12%)"}}/></PieChart></ResponsiveContainer><span><b>18</b><small>DEMO</small></span></div><div className="severity-legend">{DEMO_SEVERITIES.map(x=><div key={x.name}><i style={{background:x.color}}/>{x.name}<b>{x.value}</b></div>)}</div></div>;
  if(!session?.accessToken)return <Empty icon={LockKeyhole} title="Sign in to view review alerts" text="Persistent severity counts are available to authenticated analysts."><button className="text-btn" onClick={()=>go("/login")}>Sign in <ChevronRight size={12}/></button></Empty>;
  if(state.status==="loading")return <Empty icon={Database} title="Loading review alerts" text="Checking persistent analyst review records."/>;
  if(state.status!=="online")return <Empty icon={Database} title="Review alerts unavailable" text="The platform API could not return alert records."><button className="text-btn" onClick={()=>go("/alerts")}>Open alerts <ChevronRight size={12}/></button></Empty>;
  if(!state.alerts.length)return <Empty icon={Shield} title="No review alerts saved" text="Capture predictions become review alerts only after an analyst promotes a flagged signal."><button className="text-btn" onClick={()=>go("/alerts")}>Review capture signals <ChevronRight size={12}/></button></Empty>;
  const severities=["CRITICAL","HIGH","MEDIUM","LOW"].map(name=>({name,value:state.alerts.filter(alert=>alert.severity===name).length,color:colors[name]}));
  return <div className="demo-distribution"><div className="donut-wrap"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={severities} dataKey="value" nameKey="name" innerRadius={43} outerRadius={63} paddingAngle={3} stroke="none">{severities.map(x=><Cell key={x.name} fill={x.color}/>)}</Pie><Tooltip contentStyle={{background:"#ffffff",border:"1px solid #d5dfeb",borderRadius:7,color:"#15243a",boxShadow:"0 5px 18px rgb(24 43 68 / 12%)"}}/></PieChart></ResponsiveContainer><span><b>{state.alerts.length}</b><small>REVIEW</small></span></div><div className="severity-legend">{severities.map(x=><div key={x.name}><i style={{background:x.color}}/>{x.name}<b>{x.value}</b></div>)}</div></div>;
}

function DashboardRecentAlerts({demoMode,session,state,go}){
  if(demoMode)return <div className="demo-alert-list">{DEMO_ALERTS.map(x=><div className="demo-alert" key={x.time}><span className="demo-time">{x.time}</span><b>{x.name}</b><span className={"severity "+x.severity.toLowerCase()}>{x.severity}</span><small>{x.source} → {x.destination}</small><em>{x.status}</em><span className="sim-tag">SIM</span></div>)}</div>;
  if(!session?.accessToken)return <Empty icon={LockKeyhole} title="Sign in to view saved alerts" text="Analyst review records are private to platform sessions."><button className="text-btn" onClick={()=>go("/login")}>Sign in <ChevronRight size={12}/></button></Empty>;
  if(state.status==="loading")return <Empty icon={Database} title="Loading review alerts" text="Checking the platform alert queue."/>;
  if(state.status!=="online")return <Empty icon={Database} title="Alert records unavailable" text="Check that the platform API is running and sign in again."/>;
  if(!state.alerts.length)return <Empty icon={Bell} title="No analyst review alerts yet" text="Review flagged capture predictions and promote one for analyst triage."><button className="text-btn" onClick={()=>go("/alerts")}>Open alerts <ChevronRight size={12}/></button></Empty>;
  return <div className="demo-alert-list">{state.alerts.slice(0,4).map(alert=><div className="demo-alert" key={alert.id}><span className="demo-time">{new Date(alert.createdAt).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"})}</span><b>{alert.title}</b><span className={"severity "+String(alert.severity).toLowerCase()}>{alert.severity}</span><small>{alert.alertKey}</small><em>{String(alert.status).replaceAll("_"," ")}</em></div>)}</div>;
}

const DEMO_ALERTS=[
  {time:"10:32:45",name:"Repeated connection attempts",severity:"Critical",source:"10.0.0.24",destination:"10.0.0.8",status:"Review"},
  {time:"10:31:12",name:"High-volume outbound flow",severity:"High",source:"10.0.0.18",destination:"203.0.113.42",status:"New"},
  {time:"10:30:05",name:"Unusual service access",severity:"Medium",source:"10.0.0.31",destination:"10.0.0.12",status:"Investigating"},
  {time:"10:29:47",name:"Repeated connection attempts",severity:"High",source:"198.51.100.23",destination:"10.0.0.8",status:"New"},
];
const DEMO_SEVERITIES=[{name:"Critical",value:2,color:"#ef5368"},{name:"High",value:5,color:"#f29435"},{name:"Medium",value:7,color:"#5c99f5"},{name:"Low",value:4,color:"#7c6be8"}];
function StoredDetections({state}){
  const formatTime=value=>{if(!value)return "Time unavailable";const date=new Date(value);return Number.isNaN(date.getTime())?value:date.toLocaleString([], {month:"short",day:"numeric",hour:"2-digit",minute:"2-digit",second:"2-digit"});};
  return <section className="panel real-detections"><div className="panel-head"><div><h2>Stored detection records</h2><p>Saved predictions · archived PCAP or live capture · not alerts</p></div><span className={"record-status "+state.status}>{state.status==="online"?"SAVED HISTORY":state.status==="loading"?"LOADING":"API OFFLINE"}</span></div>
    {state.status==="loading"&&!state.events.length?<Empty icon={Database} title="Loading stored results" text="Checking the demo events service."/>:
    state.status==="offline"&&!state.events.length?<Empty icon={Database} title="Stored results unavailable" text="The events API is offline or not ready. Simulated demo alerts remain separate."/>:
    !state.events.length?<Empty icon={Activity} title="No saved predictions yet" text="Start network capture on Ubuntu. Completed model outputs will appear here when the events API stores them."/>:
    <div className="stored-event-list">{state.events.slice(0,8).map(event=><article className="stored-event" key={event.id}><div className="stored-event-meta"><b>{formatTime(event.recorded_at)}</b><span>{event.capture_mode==="pcap"?"PCAP replay":event.capture_mode==="live"?"Live capture":"Capture mode unknown"}</span><small>{event.input_source||"Source unavailable"}</small><small>{event.capture_session_id?"Session "+event.capture_session_id.slice(0,8):"Session not recorded"}</small><small>{event.model_version||"Model version unavailable"}</small></div><div className="stored-model"><span>Random Forest</span><b className={event.rf_flagged?"severity critical":"severity low"}>{event.rf_classification||"UNKNOWN"}</b><small>{Number.isFinite(event.rf_probability)?(event.rf_probability*100).toFixed(1)+"% probability":"score unavailable"}{Number.isFinite(event.rf_threshold)?" · threshold "+(event.rf_threshold*100).toFixed(1)+"%":""}</small></div><div className="stored-model"><span>Isolation Forest</span><b className={event.if_flagged?"severity high":"severity low"}>{event.if_classification||"UNKNOWN"}</b><small>{Number.isFinite(event.if_score)?event.if_score.toFixed(4)+" anomaly score":"score unavailable"}{Number.isFinite(event.if_threshold)?" · threshold "+event.if_threshold.toFixed(4):""}</small></div><small className="agreement-tag">{(event.detector_agreement||"agreement unknown").replaceAll("_"," ")}</small></article>)}</div>}
    <div className="stored-foot">{state.count} saved record{state.count===1?"":"s"} · refreshes every 10 seconds{state.status==="offline"&&state.events.length?" · showing last successful response":""}</div>
  </section>;
}

function StoredAnalyses({state,session}){
  const formatTime=value=>{if(!value)return "Time unavailable";const date=new Date(value);return Number.isNaN(date.getTime())?value:date.toLocaleString([], {month:"short",day:"numeric",hour:"2-digit",minute:"2-digit",second:"2-digit"});};
  return <section className="panel real-detections"><div className="panel-head"><div><h2>Stored flow analyses</h2><p>Authenticated model results · raw flow features are not retained</p></div><span className={"record-status "+state.status}>{state.status==="online"?"PLATFORM RECORDS":state.status==="loading"?"LOADING":state.status==="signedout"?"SIGN IN":"API OFFLINE"}</span></div>
    {state.status==="signedout"?<Empty icon={LockKeyhole} title="Sign in to view saved analyses" text="Only authenticated platform sessions can read the analysis history."><NavLink className="text-btn" to="/login">Sign in</NavLink></Empty>:
    state.status==="loading"&&!state.records.length?<Empty icon={Database} title="Loading analysis history" text="Checking the platform API."/>:
    state.status==="offline"&&!state.records.length?<Empty icon={Database} title="Analysis history unavailable" text="The platform API is offline or the session has expired."/>:
    !state.records.length?<Empty icon={Activity} title="No flow analyses saved yet" text="Submit an authenticated flow analysis to add its model results here."/>:
    <div className="stored-event-list">{state.records.slice(0,8).map(record=><article className="stored-event" key={record.id}><div className="stored-event-meta"><b>{formatTime(record.analyzedAt)}</b><span>{record.submittedBy||"Analyst unavailable"}</span><small>{record.modelVersion||"Model version unavailable"}</small></div><div className="stored-model"><span>Random Forest</span><b className={record.rfFlagged?"severity critical":"severity low"}>{record.rfClassification||"UNKNOWN"}</b><small>{Number.isFinite(record.rfAttackProbability)?(record.rfAttackProbability*100).toFixed(1)+"% probability":"score unavailable"}</small></div><div className="stored-model"><span>Isolation Forest</span><b className={record.ifFlagged?"severity high":"severity low"}>{record.ifClassification||"UNKNOWN"}</b><small>{Number.isFinite(record.ifAnomalyScore)?record.ifAnomalyScore.toFixed(4)+" anomaly score":"score unavailable"}</small></div><small className="agreement-tag">{(record.detectorAgreement||"agreement unknown").replaceAll("_"," ")}</small></article>)}</div>}
    <div className="stored-foot">{state.count} saved analysis{state.count===1?"":"es"} · refreshes every 10 seconds{state.status==="offline"&&state.records.length?" · showing last successful response":""}</div>
  </section>;
}

function Dashboard({engine,detections,demoMode,setDemoMode,session,captureStatus}){
  const go=useNavigate(),online=Boolean(engine?.health?.status==="healthy"&&engine?.models);
  const [eventState,setEventState]=useState({status:"loading",events:[],count:0});
  const [analysisState,setAnalysisState]=useState({status:"signedout",records:[],count:0});
  const [caseState,setCaseState]=useState({status:session?.accessToken?"loading":"signedout",cases:[],error:"",requiresSignIn:false});
  const [alertState,setAlertState]=useState({status:session?.accessToken?"loading":"signedout",alerts:[]});
  const [incidentState,setIncidentState]=useState({status:session?.accessToken?"loading":"signedout",incidents:[]});
  useEffect(()=>{let active=true;if(!session?.accessToken){setAnalysisState({status:"signedout",records:[],count:0});return()=>{active=false;};}setAnalysisState(current=>({...current,status:"loading"}));async function refresh(){try{const records=await loadRecentAnalyses(session.accessToken,50);if(active)setAnalysisState({status:"online",records:Array.isArray(records)?records:[],count:Array.isArray(records)?records.length:0});}catch{if(active)setAnalysisState(current=>({...current,status:"offline"}));}}refresh();const timer=setInterval(refresh,10000);return()=>{active=false;clearInterval(timer);};},[session?.accessToken,detections.length]);
  useEffect(()=>{let active=true;async function refresh(){try{const data=await loadDemoEvents(50);if(!active)return;const events=Array.isArray(data.events)?data.events.filter(event=>event.simulated===false):[];setEventState({status:"online",events,count:Number.isFinite(data.count)?data.count:events.length});}catch{if(active)setEventState(current=>({...current,status:"offline"}));}}refresh();const timer=setInterval(refresh,10000);return()=>{active=false;clearInterval(timer);};},[]);
  useEffect(()=>{let active=true;if(!session?.accessToken){setCaseState({status:"signedout",cases:[],error:"",requiresSignIn:false});return()=>{active=false;};}setCaseState({status:"loading",cases:[],error:"",requiresSignIn:false});async function refresh(){try{const cases=await loadCases(session.accessToken,4);if(active)setCaseState({status:"online",cases:Array.isArray(cases)?cases:[],error:"",requiresSignIn:false});}catch(error){if(active){const detail=error.response?.data?.detail,unauthorized=error.response?.status===401;setCaseState({status:"offline",cases:[],error:typeof detail==="string"?detail:unauthorized?"Your platform sign-in may have expired. Sign in again to load cases.":"Could not reach the platform case service.",requiresSignIn:unauthorized});}}}refresh();const timer=setInterval(refresh,15000);return()=>{active=false;clearInterval(timer);};},[session?.accessToken]);
  useEffect(()=>{let active=true;if(!session?.accessToken){setAlertState({status:"signedout",alerts:[]});setIncidentState({status:"signedout",incidents:[]});return()=>{active=false;};}setAlertState({status:"loading",alerts:[]});setIncidentState({status:"loading",incidents:[]});async function refresh(){const [alertsResult,incidentsResult]=await Promise.allSettled([loadAlerts(session.accessToken,100),loadIncidents(session.accessToken,100)]);if(!active)return;setAlertState(alertsResult.status==="fulfilled"?{status:"online",alerts:Array.isArray(alertsResult.value)?alertsResult.value:[]}:{status:"offline",alerts:[]});setIncidentState(incidentsResult.status==="fulfilled"?{status:"online",incidents:Array.isArray(incidentsResult.value)?incidentsResult.value:[]}:{status:"offline",incidents:[]});}refresh();const timer=setInterval(refresh,15000);return()=>{active=false;clearInterval(timer);};},[session?.accessToken]);
  const openIncidents=incidentState.incidents.filter(item=>!(["RESOLVED","CLOSED"].includes(item.status))).length;
  const rfSignals=eventState.events.filter(item=>item.rf_flagged).length;
  const ifSignals=eventState.events.filter(item=>item.if_flagged).length;
  const alertMetric=demoMode?"18":alertState.status==="online"?String(alertState.alerts.length):alertState.status==="loading"?"Loading":alertState.status==="offline"?"Unavailable":"Sign in";
  const incidentMetric=demoMode?"3":incidentState.status==="online"?String(openIncidents):incidentState.status==="loading"?"Loading":incidentState.status==="offline"?"Unavailable":"Sign in";
  const captureState=captureStatus?.status||"unavailable";
  return <div className="page">
    <PageHead title="Operations Dashboard"><div className="demo-actions"><span className={"demo-badge "+(demoMode?"simulated":"live")}>{demoMode?"SIMULATION ON":"LIVE DATA ONLY"}</span><button className={demoMode?"secondary-btn":"primary-btn"} onClick={()=>setDemoMode(!demoMode)}>{demoMode?"Hide simulation":"Show demo data"}</button><button className="primary-btn" onClick={()=>go("/detection")}><Activity size={14}/>Analyze a real flow</button></div></PageHead>
    {demoMode&&<div className="simulation-banner"><span className="sim-pulse"/>SIMULATED SOC SCENARIO <small>Sample alerts and severity counts below are fictional demo data; no events were observed on your network.</small></div>}
    <div className="metric-grid">
      <Metric icon={ShieldAlert} label={demoMode?"Demo alerts":"Review alerts"} value={alertMetric} detail={demoMode?"Seeded sample events · not observed":alertState.status==="online"?"Persistent analyst review records":alertState.status==="offline"?"Platform API unavailable":alertState.status==="loading"?"Loading saved records":"Sign in to view saved alerts"} color="red" state={demoMode?"none":alertState.status==="online"?"online":alertState.status==="offline"?"offline":null}/>
      <Metric icon={Siren} label="Open incidents" value={incidentMetric} detail={demoMode?"Simulated investigation cases":incidentState.status==="online"?"Persistent investigation records":incidentState.status==="offline"?"Platform API unavailable":incidentState.status==="loading"?"Loading saved records":"Sign in to view incidents"} color="purple" state={demoMode?"none":incidentState.status==="online"?"online":incidentState.status==="offline"?"offline":null}/>
      <Metric icon={Server} label="Assets monitored" value={demoMode?"24":"No inventory"} detail={demoMode?"Demo inventory · fictional":"No asset source is linked"} color="blue" state="none"/>
      <Metric icon={Bot} label="AI engine" value={online?"Operational":"Unavailable"} detail={engine?.models?"2 detectors · "+engine.models.feature_count+" input features":"Model status unavailable"} color="green" state={online?"online":"offline"}/>
    </div>
    <div className="dash-grid">
      <section className="panel telemetry"><div className="panel-head"><div><h2>{demoMode?"Simulated attack activity":"Capture prediction activity"}</h2><p>{demoMode?"Illustrative activity map · no geographic attribution":"Saved flow model results · no addresses or packet contents"}</p></div><span className="range"><Clock3 size={12}/>{demoMode?"DEMO SCENARIO":eventState.status==="online"?`${eventState.events.length} RECENT RECORDS`:eventState.status==="loading"?"LOADING":"API OFFLINE"}</span></div>
        {demoMode?<div className="telemetry-body demo-map"><span className="orbit orbit-one"/><span className="orbit orbit-two"/><i className="map-node node-a"/><i className="map-node node-b"/><i className="map-node node-c"/><i className="map-arc arc-a"/><i className="map-arc arc-b"/><span className="telemetry-core"><Network size={23}/></span><div className="telemetry-empty"><b>Illustrative network activity</b><p>Fictional source-to-destination paths for dashboard demonstration.</p><button className="secondary-btn small" onClick={()=>go("/network")}><Activity size={13}/>Open Network Watch</button></div></div>:<div className="telemetry-body telemetry-live-body"><div className="telemetry-live"><div className="telemetry-live-stats"><div><small>Saved predictions</small><b>{eventState.status==="online"?eventState.count:"—"}</b></div><div><small>RF flagged</small><b>{eventState.status==="online"?rfSignals:"—"}</b></div><div><small>IF flagged</small><b>{eventState.status==="online"?ifSignals:"—"}</b></div></div>{eventState.status==="loading"?<div className="telemetry-live-empty">Loading saved capture results…</div>:eventState.status==="offline"?<div className="telemetry-live-empty">Capture history is unavailable while the AI Engine is offline.</div>:!eventState.events.length?<div className="telemetry-live-empty">No saved capture predictions yet. Run the Ubuntu capture tool to start collecting flow results.</div>:<div className="telemetry-live-last"><span><b>Most recent prediction</b><small>{new Date(eventState.events[0].recorded_at).toLocaleString()} · {eventState.events[0].capture_mode==="live"?"Live capture":eventState.events[0].capture_mode==="pcap"?"PCAP replay":"capture mode unknown"}</small></span><span className="telemetry-model-tags"><i>RF {eventState.events[0].rf_classification||"UNKNOWN"}</i><i>IF {eventState.events[0].if_classification||"UNKNOWN"}</i></span></div>}<button className="secondary-btn small" onClick={()=>go("/monitor")}><Activity size={13}/>Open Real-time Monitor</button></div></div>}
        <div className="panel-foot"><span><Dot state={demoMode?"offline":captureState==="running"?"online":captureState==="stale"?"offline":"muted"}/>{demoMode?"Simulated events · not live":captureState==="running"?"Capture runner active":captureState==="stale"?"Capture heartbeat stale":"Manual capture is not running"}</span><span>{demoMode?"Fictional paths · no network data":"Stored model outputs · not analyst alerts"}</span></div></section>
      <section className="panel distribution"><div className="panel-head"><div><h2>Alert distribution</h2><p>{demoMode?"Fictional sample severity counts":"Persistent analyst review records"}</p></div><ListFilter size={15}/></div><DashboardAlertDistribution demoMode={demoMode} session={session} state={alertState} go={go}/></section>
      <RecentCasesPanel demoMode={demoMode} session={session} state={caseState} go={go} setDemoMode={setDemoMode}/>
      <section className="panel trend"><div className="panel-head"><div><h2>Analysis activity</h2><p>Real Random Forest score from this browser session</p></div><span className="range">Session · {detections.length} analyzed</span></div><SessionTrend detections={detections}/></section>
      <section className="panel recent-alerts"><div className="panel-head"><div><h2>{demoMode?"Demo alerts":"Recent alerts"}</h2><p>{demoMode?"Fictional examples · clearly marked":"Analyst triage queue · saved review records"}</p></div><button className="text-btn" onClick={()=>go("/alerts")}>View alerts <ChevronRight size={12}/></button></div><DashboardRecentAlerts demoMode={demoMode} session={session} state={alertState} go={go}/></section>
      <StoredDetections state={eventState}/><StoredAnalyses state={analysisState} session={session}/>
    </div>
    <div className="integrity"><LockKeyhole size={12}/>{demoMode?"Demo mode mixes fictional SOC examples with real engine health and flow analysis; labels identify each source.":"Capture outputs are experimental model predictions. Alerts and incidents require analyst review; no response actions run automatically."}</div>
  </div>;
}

function Detector({name,kind,icon:Icon,classification,flagged,value,label,threshold,fill,violet}){
  return <div className="detector"><div className="detector-head"><span className={"detector-icon "+(violet?"violet":"")}><Icon size={14}/></span><div><b>{name}</b><small>{kind}</small></div><span className={"class-tag "+(flagged?"flag":"ok")}>{classification}</span></div><div className="score"><span>{label}</span><b>{value}</b></div><div className="score-bar"><i className={violet?"violet":""} style={{width:Math.max(0,Math.min(100,fill))+"%"}}/></div><small className="threshold">{threshold}</small></div>;
}

function LiveCaptureGuide(){
  const [copied,setCopied]=useState(false);
  const command="cd /mnt/neurosphere/NeuroSphere/ai-engine && sudo .venv/bin/python -m app.feature_extraction.run_reference_capture -i enp0s31f6 -u http://127.0.0.1:8000/api/v1/detect/cicflowmeter-python";
  async function copy(){try{await navigator.clipboard.writeText(command);setCopied(true);setTimeout(()=>setCopied(false),1800);}catch{}}
  return <section className="panel capture-guide" aria-labelledby="capture-title">
    <div className="capture-guide-head"><div><span className="live-badge"><Dot state="online"/> LIVE CAPTURE</span><h2 id="capture-title">Analyze real network traffic</h2><p>Capture runs on Ubuntu in a terminal. The dashboard never starts privileged packet capture.</p></div><button className="secondary-btn small" onClick={copy}>{copied?"Copied":"Copy command"}</button></div>
    <ol><li>In an Ubuntu SSH session, check interfaces with <code>ip -brief link</code>.</li><li>Confirm <code>enp0s31f6</code> is the interface you are authorized to monitor, then run:</li></ol>
    <pre className="capture-command">{command}</pre>
    <p className="capture-caution"><AlertTriangle size={13}/>This captures actual packets and prints experimental model predictions in the terminal. Press Ctrl+C to stop. Detection metadata appears under Stored detection records; IPs, ports, and raw features are not retained.</p>
  </section>;
}

function Detection({engine,detections,setDetections,session}){
  const [text,setText]=useState(""),[busy,setBusy]=useState(false),[error,setError]=useState(""),[result,setResult]=useState(null),names=engine?.models?.feature_names||[];
  function loadTemplate(){if(!names.length){setError("Model feature schema is not available.");return;}setText(JSON.stringify(Object.fromEntries(names.map(n=>[n,null])),null,2));setError("");}
  async function submit(e){e.preventDefault();setError("");if(!session?.accessToken){setError("Sign in to the platform API before submitting a flow.");return;}let features;try{features=JSON.parse(text);}catch{setError("Enter a valid JSON object.");return;}if(!features||Array.isArray(features)||typeof features!=="object"){setError("Input must be keyed by CIC-IDS2017 feature names.");return;}setBusy(true);try{const data=await analyzeFlow(features,session.accessToken),item={id:crypto.randomUUID(),time:new Date().toISOString(),probability:data.detection.random_forest.attack_probability};setResult(data);setDetections(current=>[item,...current].slice(0,50));}catch(err){const d=err.response?.data?.detail;setError(typeof d==="string"?d:d?JSON.stringify(d):err.response?.status?"Platform API returned HTTP "+err.response.status:"Could not reach the platform API. Check service status and retry.");}finally{setBusy(false);}}
  const rf=result?.detection.random_forest,iso=result?.detection.isolation_forest,flagged=Boolean(rf?.flagged||iso?.flagged);
  return <div className="page"><PageHead kicker="Network security · AI analysis" title="Flow analysis" subtitle="Submit a 67-feature flow through the authenticated platform API, or use network capture on Ubuntu for actual packets."/><LiveCaptureGuide/><div className="analysis-grid">
    <section className="panel editor"><div className="panel-head"><div><h2>Input flow features</h2><p>{names.length?names.length+" required named features":"Waiting for model schema"}</p></div><span className="range"><LockKeyhole size={12}/>{session?"Authenticated platform API":"Sign-in required"}</span></div>{!session&&<div className="login-notice"><LockKeyhole size={13}/>Sign in to submit a flow through the protected platform API. <NavLink className="text-btn" to="/login">Sign in</NavLink></div>}
      <form onSubmit={submit}><textarea className="json-input" value={text} onChange={e=>setText(e.target.value)} spellCheck="false" aria-label="Flow feature JSON" placeholder={'Paste a full feature object, e.g.\\n{\\n  "Destination Port": 443,\\n  ...\\n}'}/>
        <div className="form-foot"><div><button className="primary-btn" disabled={busy||!engine?.models||!session?.accessToken}>{busy?"Analyzing…":<><Activity size={13}/>Run detection</>}</button><button type="button" className="secondary-btn" onClick={loadTemplate}><FileSearch size={13}/>Load schema</button><label className="file-btn"><Upload size={13}/>Choose JSON<input type="file" accept=".json,application/json" onChange={async e=>{const f=e.target.files?.[0];if(f){setText(await f.text());setError("");}}}/></label></div><small>{detections.length} analyses this session</small></div>
        {error&&<div className="error"><AlertTriangle size={13}/>{error}</div>}</form>
      <div className="warning"><AlertTriangle size={14}/><div><b>Research-only model output</b><p>Feature parity and attack-family generalization remain limited. Do not use these scores for automatic blocking or alert escalation.</p></div></div><p className="footnote">Schema template values are null placeholders. Replace them with actual flow measurements before submitting.</p>
    </section>
    <section className="panel result"><div className="panel-head"><div><h2>Detection result</h2><p>Separate signals from both configured models</p></div>{result&&<span className={"result-tag "+(flagged?"flag":"ok")}>{flagged?"Review signal":"No model alert"}</span>}</div>
      {!result?<Empty icon={Radar} title="Waiting for a flow" text="Submit a valid feature record to see model outputs and detector agreement."/>:<div className="result-stack">
        <Detector name="Random Forest" kind="Supervised classifier" icon={Bot} classification={rf.classification} flagged={rf.flagged} value={(rf.attack_probability*100).toFixed(2)+"%"} label="Attack probability" threshold={"Frozen threshold "+(rf.threshold*100).toFixed(1)+"%"} fill={rf.attack_probability*100}/>
        <Detector name="Isolation Forest" kind="Anomaly detector" icon={Radar} classification={iso.classification} flagged={iso.flagged} value={iso.anomaly_score.toFixed(4)} label="Anomaly score" threshold={"Frozen threshold "+iso.threshold.toFixed(4)} fill={iso.anomaly_score*100} violet/>
        <div className="agreement"><span>Detector agreement</span><b>{result.risk_assessment.detector_agreement.replaceAll("_"," ")}</b><small>{result.risk_assessment.investigation_category.replaceAll("_"," ")}</small></div>
        <details className="raw"><summary>Full model response</summary><pre>{JSON.stringify(result,null,2)}</pre></details>
      </div>}
    </section>
  </div></div>;
}

function LoginPage({session,onLogin,onSignOut,logoutWarning}){
  const [username,setUsername]=useState(""),[password,setPassword]=useState(""),[busy,setBusy]=useState(false),[error,setError]=useState(""),[notice,setNotice]=useState("");
  async function submit(event){
    event.preventDefault();setError("");setNotice("");setBusy(true);
    try{
      const result=await loginToPlatform(username.trim(),password);
      if(!result||typeof result.access_token!=="string"||result.token_type!=="Bearer"||!Number.isFinite(result.expires_in)||!Array.isArray(result.roles))throw new Error("The platform API returned an unexpected login response.");
      onLogin({accessToken:result.access_token,tokenType:result.token_type,expiresAt:Date.now()+result.expires_in*1000,roles:result.roles.map(String),username:username.trim()});
      setPassword("");setNotice("Signed in. This session is held in memory and ends when it expires or the page refreshes.");
    }catch(err){
      const detail=err.response?.data?.detail;
      setError(typeof detail==="string"?detail:err.message||"Could not reach the platform API. Check that it is running and retry.");
    }finally{setBusy(false);}
  }
  return <div className="login-page"><section className="panel login-card"><div className="brand-mark login-mark"><ShieldCheck size={22}/></div><div className="kicker">PLATFORM ACCESS</div><h1>Sign in to NeuroSphere</h1><p className="login-intro">The research dashboard stays available without sign-in. A platform session is required for authenticated flow analysis.</p>{logoutWarning&&<div className="login-notice" role="alert">{logoutWarning}</div>}
    {session?<div className="login-session"><span className="session-check">●</span><div><b>Platform session active</b><small>{session.username} · {session.roles.join(", ")||"User"} · expires {new Date(session.expiresAt).toLocaleTimeString()}</small></div><button className="secondary-btn" onClick={onSignOut}>Sign out</button></div>:<form className="login-form" onSubmit={submit}><label>Username<input required autoComplete="username" value={username} onChange={e=>setUsername(e.target.value)} placeholder="Enter your platform username"/></label><label>Password<input required type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Enter your password"/></label><button className="primary-btn login-submit" disabled={busy}>{busy?"Signing in…":<><LogIn size={14}/>Sign in</>}</button><NavLink className="password-recovery-link" to="/reset-password">Forgot your password?</NavLink>{error&&<div className="error login-error"><AlertTriangle size={13}/>{error}</div>}{notice&&<div className="login-notice">{notice}</div>}</form>}
    <div className="login-foot"><LockKeyhole size={13}/><span>API: {PLATFORM_API_URL}<br/>Token stays in memory only. Refreshing signs you out.</span></div>
  </section></div>;
}

function PasswordResetPage({onPasswordReset}){
  const [recoveryCode,setRecoveryCode]=useState(""),[newPassword,setNewPassword]=useState(""),[confirmPassword,setConfirmPassword]=useState(""),[busy,setBusy]=useState(false),[error,setError]=useState(""),[success,setSuccess]=useState(false);
  async function submit(event){
    event.preventDefault();setError("");
    if(newPassword.length<16){setError("Use at least 16 characters for the new password.");return;}
    if(newPassword!==confirmPassword){setError("The new passwords do not match.");return;}
    setBusy(true);
    try{await resetPlatformPassword(recoveryCode.trim(),newPassword);setSuccess(true);setRecoveryCode("");setNewPassword("");setConfirmPassword("");onPasswordReset();}
    catch(err){const detail=err.response?.data?.detail;setError(typeof detail==="string"?detail:"Could not reach the platform API. Check that it is running and retry.");}
    finally{setBusy(false);}
  }
  return <div className="login-page"><section className="panel login-card"><div className="brand-mark login-mark"><ShieldCheck size={22}/></div><div className="kicker">ACCOUNT RECOVERY</div><h1>Reset your password</h1><p className="login-intro">Enter the one-time recovery code issued by the server administrator. Codes expire after 30 minutes and can only be used once.</p>{success?<div className="login-notice" role="status">Password reset. Sign in with your new password.<NavLink className="password-recovery-link reset-signin-link" to="/login">Return to sign in</NavLink></div>:<form className="login-form" onSubmit={submit}><label>One-time recovery code<input required type="text" autoComplete="off" autoCapitalize="none" spellCheck="false" maxLength={64} value={recoveryCode} onChange={e=>setRecoveryCode(e.target.value)} placeholder="Paste your 64-character code"/></label><label>New password<input required minLength={16} maxLength={128} type="password" autoComplete="new-password" value={newPassword} onChange={e=>setNewPassword(e.target.value)} placeholder="At least 16 characters"/></label><label>Confirm new password<input required minLength={16} maxLength={128} type="password" autoComplete="new-password" value={confirmPassword} onChange={e=>setConfirmPassword(e.target.value)} placeholder="Enter it again"/></label><button className="primary-btn login-submit" disabled={busy}>{busy?"Resetting…":"Reset password"}</button>{error&&<div className="error login-error" role="alert"><AlertTriangle size={13}/>{error}</div>}<NavLink className="password-recovery-link" to="/login">Back to sign in</NavLink></form>}<div className="login-foot"><LockKeyhole size={13}/><span>Recovery codes are generated on the Ubuntu server. NeuroSphere does not send password reset emails.</span></div></section></div>;
}

function SettingsPage({engine,platformStatus,captureStatus,endpointTelemetry,cowrieStatus,threatFeedStatus,demoMode,setDemoMode,session,onSignOut,onPasswordChanged}){
  const [currentPassword,setCurrentPassword]=useState(""),[newPassword,setNewPassword]=useState(""),[confirmPassword,setConfirmPassword]=useState(""),[passwordBusy,setPasswordBusy]=useState(false),[passwordError,setPasswordError]=useState("");
  const engineOnline=engine?.health?.status==="healthy"&&Boolean(engine?.models);
  const platformOnline=platformStatus?.status==="healthy"&&platformStatus?.database==="connected";
  const captureState=captureStatus?.status||"checking";
  const captureLabel=captureState==="running"?"Running":captureState==="stale"?"Stale":captureState==="stopped"?"Stopped":captureState==="idle"?"Not started":captureState==="unavailable"?"Unavailable":"Checking";
  const endpointOnline=endpointTelemetry?.status==="connected";
  const cowrieOnline=cowrieStatus?.status==="connected";
  const threatFeedOnline=threatFeedStatus?.status==="connected";
  const services=[
    {name:"AI detection engine",detail:"FastAPI · model readiness",state:engineOnline?"Operational":"Unavailable",ok:engineOnline},
    {name:"Platform API and database",detail:"Spring Boot · MySQL",state:platformOnline?"Operational":platformStatus?.status==="healthy"?"Database unavailable":"Unavailable",ok:platformOnline},
    {name:"Network capture",detail:captureStatus?.capture_mode==="live"?"Live capture":captureStatus?.capture_mode==="pcap"?"PCAP replay":"Manual CLI · no source configured",state:captureLabel,ok:captureState==="running"},
    {name:"Endpoint telemetry",detail:endpointOnline?`${endpointTelemetry.hostname} · local Linux journal aggregates`:"Local Linux host telemetry",state:endpointOnline?"Connected":"Not linked",ok:endpointOnline},
    {name:"Deception sensor",detail:cowrieOnline?"Cowrie · loopback lab sensor":"Cowrie · localhost only",state:cowrieOnline?"Connected":cowrieStatus?.status==="unsafe_bind"?"Unsafe bind":"Not linked",ok:cowrieOnline},
    {name:"Threat intelligence",detail:threatFeedStatus?.indicator_count!=null?`Emerging Threats · ${threatFeedStatus.indicator_count} IP indicators · refreshes every 15 min`:"Emerging Threats feed",state:threatFeedOnline?"Connected":threatFeedStatus?.status==="stale"?"Stale":threatFeedStatus?.status==="unavailable"?"Unavailable":"Checking",ok:threatFeedOnline},
  ];
  async function submitPasswordChange(event){
    event.preventDefault();setPasswordError("");
    if(newPassword.length<16){setPasswordError("Use at least 16 characters for the new password.");return;}
    if(newPassword!==confirmPassword){setPasswordError("The new passwords do not match.");return;}
    setPasswordBusy(true);
    try{await changePlatformPassword(session.accessToken,currentPassword,newPassword);setCurrentPassword("");setNewPassword("");setConfirmPassword("");onPasswordChanged();}
    catch(err){const detail=err.response?.data?.detail;setPasswordError(typeof detail==="string"?detail:"Could not reach the platform API. Check that it is running and retry.");}
    finally{setPasswordBusy(false);}
  }
  return <div className="page settings-page">
    <PageHead kicker="Workspace configuration" title="Settings" subtitle="Review service connections, demo display options, and the current analyst session."/>
    <div className="settings-grid">
      <section className="panel settings-card">
        <div className="settings-card-head"><span className="settings-icon"><LayoutDashboard size={16}/></span><div><h2>Dashboard display</h2><p>Choose whether the overview includes clearly labeled fictional SOC activity.</p></div></div>
        <div className="settings-option"><div><b>Simulation data</b><small>Sample alert counts and the illustrative attack map are fictional. They are not observed network events.</small></div><button type="button" role="switch" aria-checked={demoMode} className={"settings-switch "+(demoMode?"on":"")} onClick={()=>setDemoMode(!demoMode)}><span/>{demoMode?"On":"Off"}</button></div>
        <div className="settings-note"><span className="settings-dot"/>{demoMode?"Simulation is visible on the Overview page.":"Only connected service data and empty states are shown."} This preference is saved in this browser.</div>
      </section>
      <section className="panel settings-card">
        <div className="settings-card-head"><span className="settings-icon"><Activity size={16}/></span><div><h2>Service connections</h2><p>Status is read from the existing health checks. Disconnected sources stay clearly marked.</p></div></div>
        <div className="settings-services">{services.map(service=><div className="settings-service" key={service.name}><span className={"settings-dot "+(service.ok?"healthy":"")}/><div><b>{service.name}</b><small>{service.detail}</small></div><strong className={service.ok?"healthy":""}>{service.state}</strong></div>)}</div>
        <small className="settings-footnote">Engine and platform status refresh every 30 seconds. Capture status refreshes every 10 seconds.</small>
      </section>
      <section className="panel settings-card settings-session-card">
        <div className="settings-card-head"><span className="settings-icon"><LockKeyhole size={16}/></span><div><h2>Analyst session</h2><p>Session tokens stay hidden and are never displayed in this panel.</p></div></div>
        {session?<><div className="settings-session"><div><small>Signed in as</small><b>{session.username}</b></div><div><small>Roles</small><b>{session.roles?.join(", ")||"User"}</b></div><div><small>Expires</small><b>{new Date(session.expiresAt).toLocaleString()}</b></div></div><button type="button" className="secondary-btn settings-signout" onClick={onSignOut}><LogOut size={13}/>Sign out</button></>:<div className="settings-option"><div><b>No analyst session</b><small>Sign in to use persistent alerts, cases, incidents, and flow analysis.</small></div><NavLink className="secondary-btn" to="/login"><LogIn size={13}/>Sign in</NavLink></div>}
      </section>
      {session&&<section className="panel settings-card settings-password-card">
        <div className="settings-card-head"><span className="settings-icon"><LockKeyhole size={16}/></span><div><h2>Change password</h2><p>Verify your current password before choosing a new one.</p></div></div>
        <form className="login-form settings-password-form" onSubmit={submitPasswordChange}><label>Current password<input required type="password" autoComplete="current-password" maxLength={128} value={currentPassword} onChange={e=>setCurrentPassword(e.target.value)}/></label><label>New password<input required type="password" autoComplete="new-password" minLength={16} maxLength={128} value={newPassword} onChange={e=>setNewPassword(e.target.value)} placeholder="At least 16 characters"/></label><label>Confirm new password<input required type="password" autoComplete="new-password" minLength={16} maxLength={128} value={confirmPassword} onChange={e=>setConfirmPassword(e.target.value)}/></label><button className="primary-btn login-submit" disabled={passwordBusy}>{passwordBusy?"Updating…":"Update password"}</button>{passwordError&&<div className="error login-error" role="alert"><AlertTriangle size={13}/>{passwordError}</div>}<small className="password-change-note">Updating your password signs out all current sessions.</small></form>
      </section>}
      <section className="panel settings-card settings-data-card">
        <div className="settings-card-head"><span className="settings-icon"><Database size={16}/></span><div><h2>Data handling</h2><p>Current demo boundaries</p></div></div>
        <ul className="settings-data-list"><li>Capture predictions store model summaries and session metadata; raw packet payloads and flow features are not retained.</li><li>Dashboard simulation values are fictional and remain separate from stored model results.</li><li>Model predictions are research signals. The platform does not block traffic or execute response actions.</li></ul>
      </section>
    </div>
  </div>;
}

export default function App(){
  const [engine,setEngine]=useState(null),[platformStatus,setPlatformStatus]=useState(null),[captureStatus,setCaptureStatus]=useState(null),[endpointTelemetry,setEndpointTelemetry]=useState(null),[cowrieStatus,setCowrieStatus]=useState(null),[threatFeedStatus,setThreatFeedStatus]=useState(null),[detections,setDetections]=useState([]),[demoMode,setDemoMode]=useState(()=>{try{return window.localStorage.getItem("neurosphere-demo-mode")!=="off";}catch{return true;}}),[session,setSession]=useState(null),[logoutWarning,setLogoutWarning]=useState(""),location=useLocation(),navigate=useNavigate();
  async function signOut(){
    const token=session?.accessToken;
    setSession(null);
    if(!token){setLogoutWarning("");return;}
    try{await logoutFromPlatform(token);setLogoutWarning("");}
    catch{setLogoutWarning("Local sign-out succeeded, but server-side revocation failed. This token may remain usable until it expires.");}
  }
  function onPasswordChanged(){setSession(null);setLogoutWarning("Password updated. Sign in again with your new password.");navigate("/login");}
  useEffect(()=>{let active=true;const refresh=async()=>{const status=await loadEngineStatus();if(active)setEngine(status);};refresh();const id=setInterval(refresh,30000);return()=>{active=false;clearInterval(id);};},[]);
  useEffect(()=>{let active=true;const refresh=async()=>{try{const status=await loadPlatformStatus();if(active)setPlatformStatus(status);}catch{if(active)setPlatformStatus({status:"unavailable",database:"unavailable"});}};refresh();const id=setInterval(refresh,30000);return()=>{active=false;clearInterval(id);};},[]);
  useEffect(()=>{let active=true;const refresh=async()=>{try{const status=await loadCaptureRunnerStatus();if(active)setCaptureStatus(status);}catch{if(active)setCaptureStatus({status:"unavailable"});}};refresh();const id=setInterval(refresh,10000);return()=>{active=false;clearInterval(id);};},[]);
  useEffect(()=>{let active=true;const refresh=async()=>{try{const telemetry=await loadEndpointTelemetry();if(active)setEndpointTelemetry(telemetry);}catch{if(active)setEndpointTelemetry({status:"unavailable"});}};refresh();const id=setInterval(refresh,30000);return()=>{active=false;clearInterval(id);};},[]);
  useEffect(()=>{let active=true;const refresh=async()=>{try{const status=await loadCowrieStatus();if(active)setCowrieStatus(status);}catch{if(active)setCowrieStatus({status:"unavailable"});}};refresh();const id=setInterval(refresh,15000);return()=>{active=false;clearInterval(id);};},[]);
  useEffect(()=>{let active=true;const refresh=async()=>{try{const status=await loadThreatFeedStatus();if(active)setThreatFeedStatus(status);}catch{if(active)setThreatFeedStatus({status:"unavailable"});}};refresh();const id=setInterval(refresh,30000);return()=>{active=false;clearInterval(id);};},[]);
  useEffect(()=>{try{window.localStorage.setItem("neurosphere-demo-mode",demoMode?"on":"off");}catch{}},[demoMode]);
  const online=Boolean(engine?.health?.status==="healthy"&&engine?.models);
  useEffect(()=>{if(!session)return;const remaining=session.expiresAt-Date.now();if(remaining<=0){setSession(null);return;}const timer=setTimeout(()=>setSession(null),remaining);return()=>clearTimeout(timer);},[session]);
  const title=[...nav,["Audit log","/audit",ClipboardList],["Flow analysis","/detection",Activity]].find(n=>n[1]===location.pathname)?.[0]||"Overview";
  return <div className="app min-h-screen"><Header online={online} session={session} onSignOut={signOut}/><div className="workspace"><Sidebar online={online} captureStatus={captureStatus} endpointTelemetry={endpointTelemetry} cowrieStatus={cowrieStatus} threatFeedStatus={threatFeedStatus} session={session}/><main className="main"><div className="mobile-title">{title}<span><Dot state={online?"online":"offline"}/>{online?"Engine online":"Engine offline"}</span></div><Routes><Route path="/" element={<Dashboard engine={engine} detections={detections} demoMode={demoMode} setDemoMode={setDemoMode} session={session} captureStatus={captureStatus}/>}/><Route path="/detection" element={<Detection engine={engine} detections={detections} setDetections={setDetections} session={session}/>}/><Route path="/twin" element={<TwinLab/>}/><Route path="/monitor" element={<CaptureMonitor/>}/><Route path="/network" element={<NetworkWatch/>}/><Route path="/alerts" element={<AlertSignals session={session}/>}/><Route path="/incidents" element={<IncidentManagement session={session}/>}/><Route path="/cases" element={<CaseManagement session={session}/>}/><Route path="/audit" element={<AuditLog session={session}/>}/><Route path="/search" element={<CaptureSearch/>}/><Route path="/reports" element={<Reports/>}/><Route path="/endpoints" element={<EndpointSecurity/>}/><Route path="/threat-intel" element={<ThreatIntelligence/>}/><Route path="/vulnerabilities" element={<VulnerabilityManagement/>}/><Route path="/playbooks" element={<Playbooks/>}/><Route path="/settings" element={<SettingsPage engine={engine} platformStatus={platformStatus} captureStatus={captureStatus} endpointTelemetry={endpointTelemetry} cowrieStatus={cowrieStatus} threatFeedStatus={threatFeedStatus} demoMode={demoMode} setDemoMode={setDemoMode} session={session} onSignOut={signOut} onPasswordChanged={onPasswordChanged}/>}/><Route path="/login" element={<LoginPage session={session} onLogin={value=>{setLogoutWarning("");setSession(value);}} onSignOut={signOut} logoutWarning={logoutWarning}/>}/><Route path="/reset-password" element={<PasswordResetPage onPasswordReset={onPasswordChanged}/>}/><Route path="*" element={<Dashboard engine={engine} detections={detections} demoMode={demoMode} setDemoMode={setDemoMode} session={session} captureStatus={captureStatus}/>}/></Routes></main></div></div>;
}
