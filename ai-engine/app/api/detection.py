
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
import joblib

from app.detection.isolation_forest import (
    detect_threat,
    FEATURE_COLUMNS
)

router = APIRouter(prefix="/api/v1", tags=["Threat Detection"])

MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "saved_models"
    / "isolation_forest.joblib"
)

model = None


def load_detection_model():
    global model

    if not MODEL_PATH.exists():
        raise RuntimeError(
            "Isolation Forest model not found. Train it first."
        )

    model = joblib.load(MODEL_PATH)


class NetworkTraffic(BaseModel):
    duration_seconds: float = Field(ge=0)
    source_bytes: float = Field(ge=0)
    destination_bytes: float = Field(ge=0)
    packet_count: int = Field(ge=0)
    failed_connections: int = Field(ge=0)
    connections_per_minute: float = Field(ge=0)


@router.post("/detect")
def detect_network_threat(traffic: NetworkTraffic):

    if model is None:
        raise HTTPException(
            status_code=503,
            detail="Detection model is not loaded"
        )

    result = detect_threat(
        model,
        traffic.model_dump()
    )

    return {
        "project": "NeuroSphere V2",
        "detection_engine": "Isolation Forest",
        "features": FEATURE_COLUMNS,
        "result": result
    }
