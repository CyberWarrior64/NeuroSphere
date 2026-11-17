import axios from "axios";
export const AI_API_URL = import.meta.env.VITE_AI_API_URL || "http://127.0.0.1:8000";
const http = axios.create({ baseURL: AI_API_URL, timeout: 6000 });
export const PLATFORM_API_URL = import.meta.env.VITE_PLATFORM_API_URL || "http://127.0.0.1:8081";
const platformHttp = axios.create({ baseURL: PLATFORM_API_URL, timeout: 20000 });
const platformStatusHttp = axios.create({ baseURL: PLATFORM_API_URL, timeout: 5000 });

export async function loadPlatformStatus() {
  return (await platformStatusHttp.get("/api/v1/platform/status")).data;
}

export async function loginToPlatform(username, password) {
  return (await platformHttp.post("/api/v1/auth/login", { username, password })).data;
}
export async function logoutFromPlatform(accessToken) {
  if (!accessToken) return;
  await platformHttp.post("/api/v1/auth/logout", null, {
    headers: { Authorization: "Bearer " + accessToken },
  });
}
export async function loadEngineStatus() {
  const results = await Promise.allSettled([http.get("/health"), http.get("/api/v1/models/v2"), http.get("/gpu")]);
  return { health: results[0].status === "fulfilled" ? results[0].value.data : null, models: results[1].status === "fulfilled" ? results[1].value.data : null, gpu: results[2].status === "fulfilled" ? results[2].value.data : null };
}
export async function analyzeFlow(features, accessToken) {
  if (!accessToken) throw new Error("Sign in to use platform flow analysis.");
  return (await platformHttp.post("/api/v1/platform/flows/analyze", features, {
    headers: { Authorization: "Bearer " + accessToken },
  })).data;
}

export async function loadCaptureReadiness() {
  return (await http.get("/api/v1/capture/cicflowmeter-python/readiness")).data;
}

export async function loadCaptureRunnerStatus() {
  return (await http.get("/api/v1/capture/runner/status")).data;
}

export async function loadEndpointTelemetry() {
  return (await http.get("/api/v1/endpoint/telemetry")).data;
}

export async function loadDemoEvents(limit = 8) {
  return (await http.get("/api/v1/demo/events", { params: { limit } })).data;
}

export async function loadIncidents(accessToken, limit = 100, status) {
  if (!accessToken) throw new Error("Sign in to view incidents.");
  return (await platformHttp.get("/api/v1/platform/incidents", {
    params: { limit, ...(status ? { status } : {}) },
    headers: { Authorization: "Bearer " + accessToken },
  })).data;
}

export async function createIncident(accessToken, payload) {
  return (await platformHttp.post("/api/v1/platform/incidents", payload, {
    headers: { Authorization: "Bearer " + accessToken },
  })).data;
}

export async function loadIncident(accessToken, id) {
  return (await platformHttp.get("/api/v1/platform/incidents/" + id, {
    headers: { Authorization: "Bearer " + accessToken },
  })).data;
}

export async function changeIncidentStatus(accessToken, id, status) {
  return (await platformHttp.patch("/api/v1/platform/incidents/" + id + "/status", { status }, {
    headers: { Authorization: "Bearer " + accessToken },
  })).data;
}

export async function addIncidentNote(accessToken, id, note) {
  return (await platformHttp.post("/api/v1/platform/incidents/" + id + "/notes", { note }, {
    headers: { Authorization: "Bearer " + accessToken },
  })).data;
}

export async function linkAlertToIncident(accessToken, incidentId, alertId) {
  return (await platformHttp.post("/api/v1/platform/incidents/" + incidentId + "/alerts/" + alertId, null, {
    headers: { Authorization: "Bearer " + accessToken },
  })).data;
}

export async function loadAlerts(accessToken, limit = 100, status) {
  if (!accessToken) throw new Error("Sign in to view review alerts.");
  return (await platformHttp.get("/api/v1/platform/alerts", {
    params: { limit, ...(status ? { status } : {}) },
    headers: { Authorization: "Bearer " + accessToken },
  })).data;
}

export async function createAlertFromCapture(accessToken, predictionId, payload) {
  return (await platformHttp.post("/api/v1/platform/alerts/from-capture/" + encodeURIComponent(predictionId), payload, {
    headers: { Authorization: "Bearer " + accessToken },
  })).data;
}

export async function changeAlertStatus(accessToken, id, status) {
  return (await platformHttp.patch("/api/v1/platform/alerts/" + id + "/status", { status }, {
    headers: { Authorization: "Bearer " + accessToken },
  })).data;
}

export async function loadCases(accessToken, limit = 50, status) {
  if (!accessToken) throw new Error("Sign in to view cases.");
  return (await platformHttp.get("/api/v1/platform/cases", {
    params: { limit, ...(status ? { status } : {}) },
    headers: { Authorization: "Bearer " + accessToken },
  })).data;
}

export async function createCase(accessToken, payload) {
  return (await platformHttp.post("/api/v1/platform/cases", payload, {
    headers: { Authorization: "Bearer " + accessToken },
  })).data;
}

export async function loadCase(accessToken, id) {
  return (await platformHttp.get("/api/v1/platform/cases/" + id, {
    headers: { Authorization: "Bearer " + accessToken },
  })).data;
}

export async function changeCaseStatus(accessToken, id, status) {
  return (await platformHttp.patch("/api/v1/platform/cases/" + id + "/status", { status }, {
    headers: { Authorization: "Bearer " + accessToken },
  })).data;
}

export async function addCaseNote(accessToken, id, note) {
  return (await platformHttp.post("/api/v1/platform/cases/" + id + "/notes", { note }, {
    headers: { Authorization: "Bearer " + accessToken },
  })).data;
}

export async function loadRecentAnalyses(accessToken, limit = 10) {
  if (!accessToken) throw new Error("Sign in to view stored analyses.");
  return (await platformHttp.get("/api/v1/platform/flows/recent", {
    params: { limit },
    headers: { Authorization: "Bearer " + accessToken },
  })).data;
}
