import { useMemo, useState } from "react";
import { AlertTriangle, ChevronDown, ChevronRight, Clock3, RotateCcw, ShieldAlert } from "lucide-react";
import "./incident-demo.css";

const DEMO_INCIDENTS = [
  {
    id: "DEMO-024",
    title: "Repeated sign-in attempts",
    severity: "High",
    category: "Credential access",
    asset: "demo-gateway-01",
    age: "12 minutes ago",
    summary: "A fictional burst of failed sign-ins against a demonstration gateway.",
    timeline: ["09:14 · Scenario begins with repeated rejected sign-ins.", "09:16 · Analyst review is simulated; no authentication logs were queried.", "09:18 · Scenario outcome is left for the presenter to discuss."],
  },
  {
    id: "DEMO-023",
    title: "Unusual outbound transfer",
    severity: "Medium",
    category: "Network activity",
    asset: "demo-workstation-03",
    age: "38 minutes ago",
    summary: "A fictional workstation sends an unusual amount of data to a reserved example destination.",
    timeline: ["08:42 · Example transfer pattern appears in the scenario.", "08:45 · No packet capture or endpoint source is connected to this example.", "08:47 · Analyst review is simulated."],
  },
  {
    id: "DEMO-022",
    title: "Unexpected service discovery",
    severity: "Low",
    category: "Reconnaissance",
    asset: "demo-lab-segment",
    age: "1 hour ago",
    summary: "A fictional host checks several demo services as part of a training scenario.",
    timeline: ["08:02 · Scenario records service checks across demo assets.", "08:05 · No live network observation is associated with this item."],
  },
];

const INITIAL_STATUS = Object.fromEntries(DEMO_INCIDENTS.map((incident) => [incident.id, "New"]));

export default function IncidentSimulation() {
  const [statuses, setStatuses] = useState(INITIAL_STATUS);
  const [expanded, setExpanded] = useState(DEMO_INCIDENTS[0].id);
  const [severity, setSeverity] = useState("All");

  const visible = useMemo(() => DEMO_INCIDENTS.filter((incident) => severity === "All" || incident.severity === severity), [severity]);
  const counts = useMemo(() => ({
    total: DEMO_INCIDENTS.length,
    open: Object.values(statuses).filter((status) => status !== "Resolved in demo").length,
    investigating: Object.values(statuses).filter((status) => status === "Investigating").length,
    resolved: Object.values(statuses).filter((status) => status === "Resolved in demo").length,
  }), [statuses]);

  function setStatus(id, status) {
    setStatuses((current) => ({ ...current, [id]: status }));
  }

  return <div className="page incident-demo">
    <div className="page-head"><div><div className="kicker">Incidents · simulated analyst workflow</div><h1>Incident Queue</h1><p>Practice reviewing fictional scenarios. This queue is separate from live capture predictions.</p></div><button className="secondary-btn" onClick={() => setStatuses(INITIAL_STATUS)}><RotateCcw size={13}/>Reset demo</button></div>
    <div className="incident-simulation-banner"><AlertTriangle size={15}/><span><b>SIMULATION ONLY</b> These sample incidents are fictional. They were not detected on your network, and status changes are stored only in this page’s memory.</span></div>
    <div className="incident-stat-grid">
      <article className="panel incident-stat"><small>Demo incidents</small><b>{counts.total}</b><span>Seeded training examples</span></article>
      <article className="panel incident-stat"><small>Open in demo</small><b>{counts.open}</b><span>No real incident queue</span></article>
      <article className="panel incident-stat"><small>Investigating</small><b>{counts.investigating}</b><span>Browser-only status</span></article>
      <article className="panel incident-stat"><small>Resolved in demo</small><b>{counts.resolved}</b><span>No containment action</span></article>
    </div>
    <section className="panel incident-queue">
      <div className="panel-head"><div><h2>Sample incident scenarios</h2><p>Fictional records for dashboard walkthroughs</p></div><label className="history-mode"><select value={severity} onChange={(event) => setSeverity(event.target.value)}><option>All</option><option>High</option><option>Medium</option><option>Low</option></select><ChevronDown size={12}/></label></div>
      <div className="incident-list">{visible.map((incident) => {
        const status = statuses[incident.id];
        const isExpanded = expanded === incident.id;
        return <article className="incident-card" key={incident.id}>
          <button className="incident-summary" onClick={() => setExpanded(isExpanded ? "" : incident.id)} aria-expanded={isExpanded}>
            <span className={"incident-severity " + incident.severity.toLowerCase()}><ShieldAlert size={14}/></span>
            <span className="incident-title"><b>{incident.title}</b><small>{incident.id} · {incident.category} · {incident.asset}</small></span>
            <span className={"incident-status " + status.toLowerCase().replaceAll(" ", "-")}>{status}</span>
            <span className={"severity " + incident.severity.toLowerCase()}>{incident.severity}</span>
            <span className="incident-age"><Clock3 size={11}/>{incident.age}</span>
            {isExpanded ? <ChevronDown size={14}/> : <ChevronRight size={14}/>}
          </button>
          {isExpanded && <div className="incident-detail">
            <p>{incident.summary}</p>
            <div className="incident-timeline">{incident.timeline.map((entry) => <div key={entry}><i/>{entry}</div>)}</div>
            <div className="incident-actions"><small>Training controls only · no alerts or response actions are sent.</small>{status === "New" && <button className="secondary-btn small" onClick={() => setStatus(incident.id, "Investigating")}>Start demo review</button>}{status === "Investigating" && <button className="primary-btn small" onClick={() => setStatus(incident.id, "Resolved in demo")}>Resolve demo item</button>}{status === "Resolved in demo" && <button className="secondary-btn small" onClick={() => setStatus(incident.id, "New")}>Reopen demo item</button>}</div>
          </div>}
        </article>;
      })}</div>
      {!visible.length && <div className="incident-empty">No sample scenarios match this severity.</div>}
    </section>
  </div>;
}

