
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import shutil
import subprocess

from app.demo_event_store import initialize_store

from app.api.detection import (
    router,
    load_detection_model
)

from app.api.detection_v2 import (
    router as v2_router,
    load_v2_models
)

from app.api.demo_events import router as demo_events_router
from app.api.capture_status import router as capture_status_router
from app.api.endpoint_telemetry import router as endpoint_telemetry_router
from app.api.deception_status import router as deception_status_router
from app.api.threat_intel import router as threat_intel_router

from app.api.detection_validated import (
    router as validated_router,
    load_validated_models
)


app = FastAPI(
    title="NeuroSphere AI Engine",
    description="AI-powered cybersecurity threat detection service",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8765",
        "http://localhost:8765",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.on_event("startup")
def startup_event():

    initialize_store()

    load_detection_model()

    load_v2_models()

    load_validated_models()


app.include_router(router)

app.include_router(v2_router)

app.include_router(validated_router)

app.include_router(demo_events_router)
app.include_router(capture_status_router)
app.include_router(endpoint_telemetry_router)
app.include_router(deception_status_router)
app.include_router(threat_intel_router)


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@app.get("/", include_in_schema=False)
def home():
    built_index = FRONTEND_DIST / "index.html"
    if built_index.is_file():
        return FileResponse(built_index)
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "neurosphere-ai-engine"
    }


@app.get("/gpu")
def gpu_status():

    pytorch_version = "Not installed"
    cuda_available = False
    gpu = "Not detected"
    nvidia_smi = shutil.which("nvidia-smi")
    nvidia_gpus = []

    if nvidia_smi:
        try:
            result = subprocess.run(
                [
                    nvidia_smi,
                    "--query-gpu=name",
                    "--format=csv,noheader"
                ],
                capture_output=True,
                text=True,
                timeout=3,
                check=False
            )
            if result.returncode == 0:
                nvidia_gpus = [
                    line.strip()
                    for line in result.stdout.splitlines()
                    if line.strip()
                ]
        except (OSError, subprocess.TimeoutExpired):
            pass

    try:
        import torch
    except (ImportError, OSError):
        pass
    else:
        pytorch_version = torch.__version__
        try:
            cuda_available = bool(torch.cuda.is_available())
            if cuda_available:
                gpu = torch.cuda.get_device_name(0)
        except Exception:
            cuda_available = False

    if gpu == "Not detected" and nvidia_gpus:
        gpu = ", ".join(nvidia_gpus)

    return {
        "pytorch": pytorch_version,
        "cuda_available": cuda_available,
        "gpu": gpu,
        "nvidia_smi_available": nvidia_smi is not None,
        "nvidia_gpus": nvidia_gpus
    }


# Built React dashboard assets are served from the same loopback-only origin.
app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="frontend-assets")


# Whitelisted React routes support direct links and browser refreshes without
# turning unknown API paths into successful HTML responses.
SPA_ROUTES = {
    "detection", "login", "monitor", "search", "alerts", "incidents",
    "endpoints", "network", "twin", "threat-intel", "vulnerabilities",
    "cases", "reports", "playbooks", "settings",
}


@app.get("/{spa_path:path}", include_in_schema=False)
def frontend_route(spa_path: str):
    if spa_path not in SPA_ROUTES:
        raise HTTPException(status_code=404, detail="Not found")
    return home()
