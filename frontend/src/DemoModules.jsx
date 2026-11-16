import { useMemo, useState } from "react";
import { Activity, AlertTriangle, BookOpenCheck, Check, ClipboardCheck, Copy, Cpu, FileSearch, Globe2, Search, Server, ShieldAlert, ShieldCheck } from "lucide-react";
import { NavLink } from "react-router-dom";
import "./demo-modules.css";

function ModuleHead({title,icon:Icon,description}){
  return <div className="page-head demo-module-head"><div className="demo-module-title"><span><Icon size={18}/></span><div><div className="kicker">SOC training environment</div><h1>{title}</h1><p>{description}</p></div></div><span className="demo-source-badge"><i/>SIMULATION DATA</span></div>;
}
function SimulationNotice({children}){
  return <div className="demo-source-notice"><ShieldAlert size={14}/><span><b>Fictional training data.</b> {children}</span></div>;
}
function DemoStat({label,value,detail,icon:Icon}){
  return <article className="panel demo-module-stat"><span><Icon size={15}/></span><small>{label}</small><b>{value}</b><em>{detail}</em></article>;
}
function LocalSearch({value,onChange,placeholder="Search simulated records"}){
  return <label className="demo-module-search"><Search size={13}/><input value={value} onChange={event=>onChange(event.target.value)} placeholder={placeholder}/></label>;
}

const endpointRows=[
  {id:"SIM-WS-014",name:"Design workstation",platform:"Windows 11 · Engineering",owner:"Engineering",status:"Online",risk:"Low",seen:"Just now"},
  {id:"SIM-SRV-002",name:"Web application host",platform:"Ubuntu · Demo service",owner:"Platform team",status:"Review",risk:"High",seen:"2 min ago"},
  {id:"SIM-WS-021",name:"Analyst workstation",platform:"Windows 11 · Security",owner:"Security",status:"Online",risk:"Low",seen:"4 min ago"},
  {id:"SIM-SRV-005",name:"Database host",platform:"Ubuntu · Demo database",owner:"Platform team",status:"Online",risk:"Medium",seen:"5 min ago"},
  {id:"SIM-LAP-008",name:"Training laptop",platform:"Ubuntu · Lab",owner:"Training",status:"Offline",risk:"Low",seen:"28 min ago"},
];
export function EndpointSecurity(){
  const [query,setQuery]=useState(""),[filter,setFilter]=useState("All"),[reviewed,setReviewed]=useState([]);
  const rows=useMemo(()=>endpointRows.filter(row=>(filter==="All"||row.status===filter)&&`${row.id} ${row.name} ${row.platform} ${row.owner}`.toLowerCase().includes(query.toLowerCase())),[filter,query]);
  return <div className="page demo-module-page"><ModuleHead title="Endpoint Security" icon={Cpu} description="A small endpoint response walkthrough using an isolated fictional inventory."/><SimulationNotice>These sample hosts are not connected to endpoint telemetry. Review marks stay in this page and do not change a real device.</SimulationNotice>
    <div className="demo-module-stats"><DemoStat icon={Server} label="Training endpoints" value="5" detail="Fictional inventory"/><DemoStat icon={ShieldCheck} label="Online in scenario" value="3" detail="Sample state only"/><DemoStat icon={AlertTriangle} label="Needs analyst review" value="1" detail="No live host alert"/></div>
    <section className="panel demo-module-panel"><div className="demo-module-toolbar"><div><h2>Endpoint inventory</h2><p>Use the filters to walk through an analyst review.</p></div><LocalSearch value={query} onChange={setQuery} placeholder="Search name, host ID, or owner"/></div><div className="demo-module-filters">{["All","Online","Review","Offline"].map(value=><button key={value} className={filter===value?"active":""} onClick={()=>setFilter(value)}>{value}</button>)}</div>
      <div className="demo-table-wrap"><table className="demo-table"><thead><tr><th>Endpoint</th><th>Platform / owner</th><th>Scenario state</th><th>Risk</th><th>Last seen</th><th>Analyst review</th></tr></thead><tbody>{rows.map(row=><tr key={row.id}><td><b>{row.name}</b><small>{row.id}</small></td><td>{row.platform}<small>{row.owner}</small></td><td><span className={`demo-pill ${row.status.toLowerCase()}`}>{row.status}</span></td><td><span className={`demo-risk ${row.risk.toLowerCase()}`}>{row.risk}</span></td><td>{row.seen}</td><td><button className="demo-row-action" onClick={()=>setReviewed(current=>current.includes(row.id)?current.filter(id=>id!==row.id):[...current,row.id])}>{reviewed.includes(row.id)?<><Check size={12}/>Reviewed</>:"Mark reviewed"}</button></td></tr>)}</tbody></table></div>
      {!rows.length&&<div className="demo-table-empty">No simulated endpoints match this search.</div>}
      <div className="demo-table-foot">{reviewed.length} review mark{reviewed.length===1?"":"s"} in this page session · no endpoint action is sent.</div>
    </section></div>;
}

const indicators=[
  {value:"203.0.113.42",type:"IPv4 address",label:"Repeated login attempts",severity:"Critical",confidence:"High",source:"Training feed A"},
  {value:"198.51.100.23",type:"IPv4 address",label:"Unusual outbound connection",severity:"High",confidence:"Medium",source:"Training feed A"},
  {value:"malware-lab.example",type:"Domain",label:"Sample payload hosting",severity:"High",confidence:"High",source:"Training feed B"},
  {value:"phish-login.example",type:"Domain",label:"Credential collection exercise",severity:"Medium",confidence:"Medium",source:"Training feed B"},
  {value:"192.0.2.77",type:"IPv4 address",label:"Port-scan exercise",severity:"Low",confidence:"Low",source:"Training feed A"},
];
export function ThreatIntelligence(){
  const [query,setQuery]=useState(""),[filter,setFilter]=useState("All"),[copied,setCopied]=useState("");
  const rows=useMemo(()=>indicators.filter(item=>(filter==="All"||item.type===filter)&&`${item.value} ${item.label} ${item.source}`.toLowerCase().includes(query.toLowerCase())),[filter,query]);
  async function copy(value){try{await navigator.clipboard.writeText(value);setCopied(value);setTimeout(()=>setCopied(""),1400);}catch{setCopied("unavailable");setTimeout(()=>setCopied(""),1400);}}
  return <div className="page demo-module-page"><ModuleHead title="Threat Intelligence" icon={Globe2} description="Explore sample indicators and practice an IOC review workflow."/><SimulationNotice>All indicators and source names below are fabricated training records. No external threat feed is configured or queried.</SimulationNotice>
    <div className="demo-module-stats"><DemoStat icon={Globe2} label="Training indicators" value={indicators.length} detail="Local sample list"/><DemoStat icon={AlertTriangle} label="High / critical" value="3" detail="Scenario labels"/><DemoStat icon={Activity} label="Feed connections" value="0" detail="No external feed"/></div>
    <section className="panel demo-module-panel"><div className="demo-module-toolbar"><div><h2>Indicator review</h2><p>Search the local sample list or copy an indicator for a training pivot.</p></div><LocalSearch value={query} onChange={setQuery}/></div><div className="demo-module-filters">{["All","IPv4 address","Domain"].map(value=><button key={value} className={filter===value?"active":""} onClick={()=>setFilter(value)}>{value}</button>)}</div>
      <div className="demo-table-wrap"><table className="demo-table"><thead><tr><th>Indicator</th><th>Type</th><th>Scenario context</th><th>Severity</th><th>Confidence</th><th>Source</th><th/></tr></thead><tbody>{rows.map(item=><tr key={item.value}><td><code>{item.value}</code></td><td>{item.type}</td><td>{item.label}</td><td><span className={`demo-risk ${item.severity.toLowerCase()}`}>{item.severity}</span></td><td>{item.confidence}</td><td>{item.source}</td><td><button className="demo-copy" onClick={()=>copy(item.value)} aria-label={`Copy ${item.value}`} title="Copy indicator">{copied===item.value?<Check size={13}/>:<Copy size={13}/>}</button></td></tr>)}</tbody></table></div>
      {!rows.length&&<div className="demo-table-empty">No training indicators match this search.</div>}<div className="demo-table-foot">{copied==="unavailable"?"Clipboard access is unavailable in this browser.":"Indicator values use reserved documentation addresses and example domains."}</div>
    </section></div>;
}

const vulnerabilityRows=[
  {id:"DEMO-VULN-001",title:"Unsupported package version",asset:"SIM-SRV-002 · Web application host",severity:"Critical",status:"Open",due:"Immediate review"},
  {id:"DEMO-VULN-002",title:"Weak TLS policy in lab profile",asset:"SIM-SRV-005 · Database host",severity:"High",status:"Open",due:"Planned remediation"},
  {id:"DEMO-VULN-003",title:"Missing workstation update",asset:"SIM-WS-014 · Design workstation",severity:"Medium",status:"In review",due:"Next maintenance window"},
  {id:"DEMO-VULN-004",title:"Excessive local permissions",asset:"SIM-LAP-008 · Training laptop",severity:"Low",status:"Accepted in scenario",due:"Training exception"},
];
export function VulnerabilityManagement(){
  const [query,setQuery]=useState(""),[filter,setFilter]=useState("All");
  const rows=useMemo(()=>vulnerabilityRows.filter(item=>(filter==="All"||item.severity===filter)&&`${item.id} ${item.title} ${item.asset}`.toLowerCase().includes(query.toLowerCase())),[filter,query]);
  return <div className="page demo-module-page"><ModuleHead title="Vulnerability Management" icon={FileSearch} description="Review a fictional asset-and-finding list for the SOC demonstration."/><SimulationNotice>The findings, host IDs, and remediation dates are synthetic. No scanner or asset inventory is connected; no CVE assessment is implied.</SimulationNotice>
    <div className="demo-module-stats"><DemoStat icon={AlertTriangle} label="Scenario findings" value={vulnerabilityRows.length} detail="Sample records"/><DemoStat icon={ShieldAlert} label="Critical / high" value="2" detail="Training priorities"/><DemoStat icon={Server} label="Sample assets" value="4" detail="Not monitored hosts"/></div>
    <section className="panel demo-module-panel"><div className="demo-module-toolbar"><div><h2>Finding queue</h2><p>Filter by sample severity and inspect the scenario remediation state.</p></div><LocalSearch value={query} onChange={setQuery} placeholder="Search finding or sample asset"/></div><div className="demo-module-filters">{["All","Critical","High","Medium","Low"].map(value=><button key={value} className={filter===value?"active":""} onClick={()=>setFilter(value)}>{value}</button>)}</div>
      <div className="demo-table-wrap"><table className="demo-table"><thead><tr><th>Finding</th><th>Asset</th><th>Severity</th><th>Scenario status</th><th>Plan</th></tr></thead><tbody>{rows.map(item=><tr key={item.id}><td><b>{item.title}</b><small>{item.id}</small></td><td>{item.asset}</td><td><span className={`demo-risk ${item.severity.toLowerCase()}`}>{item.severity}</span></td><td><span className="demo-pill review">{item.status}</span></td><td>{item.due}</td></tr>)}</tbody></table></div>
      {!rows.length&&<div className="demo-table-empty">No sample findings match this filter.</div>}<div className="demo-table-foot">No remediation is scheduled or applied by this demo.</div>
    </section></div>;
}

const playbooks={
  outbound:{title:"Unusual outbound traffic",context:"Use when a reviewed flow shows an unexpected outbound destination.",steps:["Record the flow time, source host, destination, and model signal in the case.","Check the host owner and whether the destination is expected for the workload.","Compare with approved network logs or a separately verified intelligence source.","Document the evidence and ask the incident lead to review the proposed response.","If containment is approved, follow your organization’s existing endpoint procedure."]},
  repeated:{title:"Repeated login attempts",context:"Use when several authentication failures need an analyst review.",steps:["Confirm the affected account and time window from an approved log source.","Check for a successful sign-in after the failures and note the source context.","Ask the account owner to verify whether the activity was expected.","Record the findings in a case and notify the designated incident lead.","Apply account controls only through an approved identity-management process."]},
  suspicious:{title:"Suspicious endpoint activity",context:"A guided review checklist for a host that needs investigation.",steps:["Confirm the endpoint identity and current owner in the asset inventory.","Preserve relevant host and process evidence using your approved tools.","Check whether the activity matches a change window or approved test.","Create or update the investigation case with evidence and timestamps.","Request approval before any isolation, quarantine, or remediation action."]},
};
export function Playbooks(){
  const [selected,setSelected]=useState("outbound"),[checked,setChecked]=useState({});
  const playbook=playbooks[selected],done=(checked[selected]||[]).length;
  function toggle(index){setChecked(current=>{const currentSteps=current[selected]||[];return {...current,[selected]:currentSteps.includes(index)?currentSteps.filter(step=>step!==index):[...currentSteps,index]};});}
  return <div className="page demo-module-page"><ModuleHead title="Playbooks" icon={BookOpenCheck} description="Practice analyst response steps without sending commands to a host or network."/><SimulationNotice>This checklist is guidance for a demo. It does not isolate endpoints, change accounts, block traffic, or execute automation.</SimulationNotice>
    <div className="playbook-layout"><section className="panel playbook-picker"><div className="panel-head"><div><h2>Available checklists</h2><p>Choose a scenario to review.</p></div></div>{Object.entries(playbooks).map(([id,item])=><button key={id} className={`playbook-choice ${selected===id?"selected":""}`} onClick={()=>setSelected(id)}><span><BookOpenCheck size={14}/></span><div><b>{item.title}</b><small>{(checked[id]||[]).length}/{item.steps.length} steps reviewed</small></div></button>)}<div className="playbook-link"><NavLink to="/cases">Open case management <span>›</span></NavLink></div></section>
      <section className="panel playbook-detail"><div className="playbook-detail-head"><div><div className="kicker">MANUAL REVIEW CHECKLIST</div><h2>{playbook.title}</h2><p>{playbook.context}</p></div><span className="playbook-progress">{done}/{playbook.steps.length}</span></div><div className="playbook-steps">{playbook.steps.map((step,index)=><button key={step} className={`playbook-step ${(checked[selected]||[]).includes(index)?"complete":""}`} onClick={()=>toggle(index)}><span className="playbook-check">{(checked[selected]||[]).includes(index)?<Check size={13}/>:index+1}</span><span>{step}</span></button>)}</div><div className="playbook-foot"><ClipboardCheck size={13}/><span>Progress is local to this page session. A reviewer must authorize any action outside the checklist.</span></div></section>
    </div></div>;
}
