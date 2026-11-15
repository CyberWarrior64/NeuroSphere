import { useCallback, useEffect, useState } from "react";
import { Activity, AlertTriangle, ArrowRight, CheckCircle2, Clock3, Radio, RefreshCw, ShieldCheck, Waypoints } from "lucide-react";
import { NavLink } from "react-router-dom";
import { loadCaptureReadiness, loadCaptureRunnerStatus } from "./api.js";
import "./network-watch.css";

function CaptureState({ status }) {
  const labels = { running: "Runner active", stale: "Heartbeat stale", stopped: "Last runner stopped", idle: "Not running" };
  const tone = status === "running" ? "online" : status === "stale" ? "offline" : "loading";
  return <span className={"record-status " + tone}>{(labels[status] || "Status unavailable").toUpperCase()}</span>;
}

export default function NetworkWatch() {
  const [readiness, setReadiness] = useState(null);
  const [runner, setRunner] = useState(null);
  const [error, setError] = useState("");
  const [updated, setUpdated] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    const [adapterResult, runnerResult] = await Promise.allSettled([loadCaptureReadiness(), loadCaptureRunnerStatus()]);
    if (adapterResult.status === "fulfilled") {
      setReadiness(adapterResult.value);
      setError("");
    } else {
      setError("Capture adapter readiness is unavailable. Check the AI engine connection.");
    }
    if (runnerResult.status === "fulfilled") setRunner(runnerResult.value);
    else setRunner({ status: "unavailable" });
    setUpdated(new Date().toISOString());
    setRefreshing(false);
  }, []);

  useEffect(() => {
    let active = true;
    const update = () => { if (active) refresh(); };
    update();
    const timer = window.setInterval(update, 30000);
    return () => { active = false; window.clearInterval(timer); };
  }, [refresh]);

  const comparison = readiness?.feature_parity_audit?.empirical_comparison;
  const directFeatures = readiness?.packet_level_reference_adapter?.recalculates_from_raw_packets || [];
  const blockers = readiness?.blockers || [];

  return <div className="page network-watch">
    <div className="page-head"><div><div className="kicker">Network watch · capture readiness</div><h1>Network Watch</h1><p>Manual capture tooling and model-adapter readiness for this research host.</p></div><button className="secondary-btn" onClick={refresh} disabled={refreshing}><RefreshCw size={13}/>{refreshing ? "Refreshing…" : "Refresh"}</button></div>
    <div className="network-watch-boundary"><AlertTriangle size={15}/><span><b>Manual capture only.</b> No continuously connected sensor is configured. The CLI runner reports its own status; this page does not claim independent traffic monitoring.</span></div>
    {error && <div className="error network-watch-error">{error}</div>}
    <div className="network-watch-grid">
      <article className="panel network-watch-stat"><div><Radio size={15}/><small>Capture runner</small></div><b>{runner?.status === "running" ? "Running" : runner?.status === "stale" ? "Stale" : runner?.status === "stopped" ? "Stopped" : runner?.status === "idle" ? "Not run" : "Unavailable"}</b><span>{runner?.capture_mode === "live" ? "Live interface mode" : runner?.capture_mode === "pcap" ? "PCAP replay mode" : "No active capture mode"}</span></article>
      <article className="panel network-watch-stat"><div><CheckCircle2 size={15}/><small>Adapter</small></div><b>{readiness?.adapter_available ? "Available" : readiness ? "Unavailable" : "Loading"}</b><span>{readiness?.capture_tool || "CICFlowMeter adapter"}</span></article>
      <article className="panel network-watch-stat"><div><Waypoints size={15}/><small>Feature mapping</small></div><b>{readiness ? readiness.mapped_feature_count + " / " + readiness.model_feature_count : "Loading"}</b><span>Named model features mapped</span></article>
      <article className="panel network-watch-stat"><div><ShieldCheck size={15}/><small>Parity certification</small></div><b>{readiness?.feature_parity_verified ? "Verified" : readiness ? "Unverified" : "Loading"}</b><span>Experimental research adapter</span></article>
    </div>
    <section className="panel network-runner">
      <div className="panel-head"><div><h2>Runner status</h2><p>Heartbeat is runner-reported; stale after 45 seconds without an update.</p></div><CaptureState status={runner?.status}/></div>
      <div className="network-runner-meta"><span><Clock3 size={13}/>{runner?.last_heartbeat_at ? "Last heartbeat " + new Date(runner.last_heartbeat_at).toLocaleString() : "No heartbeat recorded"}</span><span>{runner?.active_sessions || 0} active runner session{runner?.active_sessions === 1 ? "" : "s"}</span><span>{updated ? "Readiness checked " + new Date(updated).toLocaleTimeString() : "Checking readiness"}</span></div>
    </section>
    {comparison && <section className="panel network-comparison">
      <div className="panel-head"><div><h2>Reference comparison</h2><p>Evidence from a bounded training-source capture sample; not independent deployment validation.</p></div><span className="range">SOURCE-CORRELATED</span></div>
      <div className="network-comparison-grid"><div><small>Feature-cell agreement</small><b>{(comparison.feature_cell_agreement * 100).toFixed(2)}%</b></div><div><small>Direct flow matches</small><b>{comparison.unique_direct_flow_matches?.toLocaleString() || "Unavailable"}</b></div><div><small>Complete 67-feature rows</small><b>{comparison.complete_67_feature_vectors?.toLocaleString() || "Unavailable"}</b></div></div>
      <p className="network-sample-note">{comparison.sample_capture || "Reference sample"} · evidence is partial and does not certify parity or detection quality on independent captures.</p>
    </section>}
    <section className="panel network-feature-panel">
      <div className="panel-head"><div><h2>Adapter calculations</h2><p>Candidate packet-derived groups; exact parity remains unverified.</p></div><span className="range">{directFeatures.length} GROUPS</span></div>
      {directFeatures.length ? <ul className="network-feature-list">{directFeatures.map((item) => <li key={item}><CheckCircle2 size={13}/>{item}</li>)}</ul> : <p className="network-muted">Adapter detail unavailable.</p>}
    </section>
    <section className="panel network-blockers">
      <div className="panel-head"><div><h2>Open parity blockers</h2><p>Resolve and validate these before operational use.</p></div><span className="network-blocker-count">{blockers.length} OPEN</span></div>
      {blockers.length ? <ul>{blockers.map((item) => <li key={item}><AlertTriangle size={13}/><span>{item}</span></li>)}</ul> : <p className="network-muted">{readiness ? "No blockers were returned." : "Loading blocker status."}</p>}
      <div className="network-safe-use">{readiness?.safe_use || "Experimental research only; do not automate blocking or alert escalation."}</div>
    </section>
    <div className="network-watch-footer">Need actual prediction records? <NavLink to="/monitor">Open Real-time Monitor <ArrowRight size={12}/></NavLink></div>
  </div>;
}