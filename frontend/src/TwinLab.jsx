import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, ArrowRight, Box, Clock3, Download, Play, RotateCcw, ShieldCheck, Waypoints } from "lucide-react";
import "./twin-lab.css";

const ASSETS = [
  { id: "gateway", name: "Edge Gateway", role: "Virtual perimeter", address: "10.20.0.1" },
  { id: "workstation", name: "Analyst Workstation", role: "Virtual endpoint", address: "10.20.1.24" },
  { id: "analytics", name: "Analytics Node", role: "Virtual service", address: "10.20.2.12" },
  { id: "decoy", name: "Decoy Service", role: "Isolated virtual decoy", address: "10.20.3.8" },
];

const SCENARIOS = [
  { id: "recon", name: "External reconnaissance", description: "A fictional scanner probes the virtual perimeter and encounters an isolated decoy.", actor: "203.0.113.50 · simulated actor", events: [
    { offset: "T+00s", title: "Port sweep begins", path: "Simulated actor → Edge Gateway", detail: "12 virtual service probes generated.", asset: "gateway", kind: "probe" },
    { offset: "T+02s", title: "Unusual service path", path: "Edge Gateway → Decoy Service", detail: "A virtual request reaches the isolated decoy.", asset: "decoy", kind: "decoy" },
    { offset: "T+04s", title: "Scenario observation recorded", path: "Decoy Service → Twin timeline", detail: "The simulated event is added to this run only.", asset: "decoy", kind: "record" },
  ]},
  { id: "spray", name: "Credential spray", description: "Repeated fictional logins target the virtual analyst workstation.", actor: "198.51.100.19 · simulated actor", events: [
    { offset: "T+00s", title: "Login attempt", path: "Simulated actor → Analyst Workstation", detail: "A failed virtual login is generated.", asset: "workstation", kind: "auth" },
    { offset: "T+02s", title: "Repeated login attempts", path: "Simulated actor → Analyst Workstation", detail: "Three more failed attempts appear in the scenario.", asset: "workstation", kind: "auth" },
    { offset: "T+04s", title: "Virtual lockout threshold reached", path: "Analyst Workstation → Twin timeline", detail: "The scenario marks the virtual account as locked.", asset: "workstation", kind: "state" },
  ]},
  { id: "movement", name: "Suspicious data movement", description: "A fictional archive moves between virtual services toward the simulated perimeter.", actor: "Scenario-generated activity", events: [
    { offset: "T+00s", title: "Archive staged", path: "Analyst Workstation → Analytics Node", detail: "A 24 MB virtual archive is staged.", asset: "analytics", kind: "data" },
    { offset: "T+02s", title: "Outbound route requested", path: "Analytics Node → Edge Gateway", detail: "A simulated transfer request reaches the gateway.", asset: "gateway", kind: "data" },
    { offset: "T+04s", title: "Transfer held in simulation", path: "Edge Gateway → Twin timeline", detail: "The twin records the scenario outcome; no network transfer occurs.", asset: "gateway", kind: "state" },
  ]},
];

const HISTORY_KEY = "neurosphere-twin-runs-v1";

function loadSavedRuns() {
  try {
    const saved = JSON.parse(window.localStorage.getItem(HISTORY_KEY) || "[]");
    return Array.isArray(saved) ? saved.slice(0, 10) : [];
  } catch {
    return [];
  }
}

export default function TwinLab() {
  const [scenarioId, setScenarioId] = useState("recon");
  const [step, setStep] = useState(0);
  const [running, setRunning] = useState(false);
  const [runNumber, setRunNumber] = useState(0);
  const [runId, setRunId] = useState(null);
  const [history, setHistory] = useState(loadSavedRuns);
  const savedRun = useRef(null);
  const scenario = SCENARIOS.find((item) => item.id === scenarioId) || SCENARIOS[0];
  const visibleEvents = useMemo(() => scenario.events.slice(0, step), [scenario, step]);
  const complete = step === scenario.events.length && step > 0;

  useEffect(() => {
    if (!running || step >= scenario.events.length) {
      if (running) setRunning(false);
      return undefined;
    }
    const timer = window.setTimeout(() => setStep((value) => value + 1), 900);
    return () => window.clearTimeout(timer);
  }, [running, scenario, step]);

  useEffect(() => {
    if (!complete || !runId) return;
    const runKey = runId;
    if (savedRun.current === runKey) return;
    savedRun.current = runKey;
    const report = {
      run_id: runKey,
      run_number: runNumber,
      scenario_id: scenario.id,
      scenario: scenario.name,
      created_at: new Date().toISOString(),
      simulation_only: true,
      assets: ASSETS,
      events: scenario.events,
    };
    setHistory((current) => {
      const next = [report, ...current].slice(0, 10);
      try { window.localStorage.setItem(HISTORY_KEY, JSON.stringify(next)); } catch { /* keep the current run visible if storage is unavailable */ }
      return next;
    });
  }, [complete, runId, runNumber, scenario]);

  function startRun() {
    setStep(0);
    setRunNumber((value) => value + 1);
    setRunId(window.crypto.randomUUID());
    setRunning(true);
  }

  function resetRun() {
    setRunning(false);
    setStep(0);
  }

  function exportRun(report) {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "neurosphere-twin-" + report.run_id + ".json";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return <div className="page twin-page">
    <div className="page-head"><div><div className="kicker">Phase 4 preview · isolated simulation</div><h1>Digital Twin Lab</h1><p>Run repeatable scenarios against virtual assets and inspect their generated event timeline.</p></div><span className="twin-mode"><Activity size={12}/>SIMULATION ONLY</span></div>
    <div className="twin-boundary"><ShieldCheck size={15}/><span><b>Isolated from live systems.</b> This runner creates fictional events in the browser. It does not capture packets, call the AI model, send traffic, or perform response actions.</span></div>
    <section className="panel twin-controls">
      <label htmlFor="twin-scenario">Scenario<select id="twin-scenario" value={scenarioId} disabled={running} onChange={(event) => { setStep(0); setScenarioId(event.target.value); }}>
        {SCENARIOS.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
      </select></label>
      <div className="twin-summary"><b>{scenario.name}</b><span>{scenario.description}</span></div>
      <div className="twin-buttons"><button className="primary-btn" onClick={startRun} disabled={running}><Play size={13}/>{running ? "Running…" : "Run scenario"}</button><button className="secondary-btn" onClick={resetRun} disabled={!step && !running}><RotateCcw size={13}/>Reset</button></div>
    </section>
    <div className="twin-stats">
      <article className="panel twin-stat"><small>Virtual assets</small><b>{ASSETS.length}</b><span>Scenario environment</span></article>
      <article className="panel twin-stat"><small>Run state</small><b>{running ? "Running" : complete ? "Complete" : "Ready"}</b><span>{runNumber ? "Run " + runNumber : "No run started"}</span></article>
      <article className="panel twin-stat"><small>Scenario progress</small><b>{step}/{scenario.events.length}</b><span>{visibleEvents.length} generated events</span></article>
    </div>
    <section className="panel twin-topology-panel">
      <div className="panel-head"><div><h2>Virtual environment</h2><p>Fictional topology · addresses are documentation-only examples</p></div><span className="range"><Waypoints size={12}/>LOCAL TWIN</span></div>
      <div className="twin-topology"><div className="twin-actor"><span><Activity size={15}/></span><b>Scenario actor</b><small>{scenario.actor}</small></div><ArrowRight className="twin-link" size={17}/>
        {ASSETS.map((asset) => { const observed = visibleEvents.some((event) => event.asset === asset.id); return <article className={"twin-asset" + (observed ? " observed" : "")} key={asset.id}>
          <span className="twin-asset-icon"><Box size={16}/></span><div><b>{asset.name}</b><small>{asset.role}</small><small className="twin-address">{asset.address}</small></div><span className={"twin-asset-state" + (observed ? " active" : "")}>{observed ? "Scenario event" : "Idle"}</span>
        </article>; })}
      </div>
    </section>
    <section className="panel twin-timeline">
      <div className="panel-head"><div><h2>Scenario event timeline</h2><p>Generated events · run {runNumber || "not started"}</p></div><span className={"record-status " + (running ? "loading" : complete ? "online" : "loading")}>{running ? "RUNNING" : complete ? "COMPLETED" : "WAITING"}</span></div>
      {!visibleEvents.length ? <div className="twin-empty"><Clock3 size={17}/><b>Ready to simulate</b><span>Choose a scenario and run it to create a local, repeatable event sequence.</span></div> :
        <div className="twin-event-list">{visibleEvents.map((event, index) => <article className="twin-event" key={scenario.id + "-" + runNumber + "-" + index}>
          <span className="twin-event-time">{event.offset}</span><span className={"twin-event-marker " + event.kind}><Activity size={12}/></span><div><b>{event.title}</b><small>{event.path}</small><p>{event.detail}</p></div><span className="twin-event-source">SIMULATED</span>
        </article>)}</div>}
    </section>
    <section className="panel twin-history">
      <div className="panel-head"><div><h2>Saved scenario runs</h2><p>Stored only in this browser · latest 10 · exportable JSON</p></div><span className="range">LOCAL HISTORY</span></div>
      {!history.length ? <div className="twin-empty"><Clock3 size={17}/><b>No saved runs yet</b><span>Completed scenarios will appear here. This history is not sent to NeuroSphere services.</span></div> :
        <div className="twin-history-list">{history.map((report) => <article className="twin-history-row" key={report.run_id}>
          <div><b>{report.scenario}</b><small>{new Date(report.created_at).toLocaleString()} · {report.events.length} simulated events · {report.assets.length} virtual assets</small></div>
          <button className="secondary-btn small" onClick={() => exportRun(report)}><Download size={12}/>Export JSON</button>
        </article>)}</div>}
    </section>
  </div>;
}