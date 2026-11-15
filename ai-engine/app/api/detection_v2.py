
from pathlib import Path
from typing import Dict, Optional

import json
import joblib
import numpy as np

from fastapi import APIRouter, Body, HTTPException


# ============================================================
# NEUROSPHERE V2 - CIC-IDS2017 HYBRID DETECTION API
# ============================================================

router = APIRouter(
    prefix="/api/v1",
    tags=["NeuroSphere V2 Detection"]
)

BASE_DIR = Path(__file__).resolve().parents[2]

MODEL_DIR = BASE_DIR / "saved_models"

DATA_DIR = BASE_DIR / "datasets" / "processed"

HYBRID_DIR = DATA_DIR / "hybrid_v2_training"

ANOMALY_DIR = DATA_DIR / "anomaly_training"

RESULT_DIR = DATA_DIR / "hybrid_v2_results"


# Model objects
rf_model = None
rf_preprocessor = None

if_model = None
if_imputer = None

FEATURE_COLUMNS = []

RF_THRESHOLD = None
IF_THRESHOLD = None


# ============================================================
# LOAD TRAINED MODELS
# ============================================================

def load_v2_models():

    global rf_model
    global rf_preprocessor
    global if_model
    global if_imputer
    global FEATURE_COLUMNS
    global RF_THRESHOLD
    global IF_THRESHOLD

    print("\nLoading NeuroSphere Hybrid V2 models...")

    # Random Forest
    rf_model = joblib.load(
        MODEL_DIR / "random_forest_cicids2017_hybrid_v2.joblib"
    )

    rf_preprocessor = joblib.load(
        HYBRID_DIR / "preprocessor.joblib"
    )

    # Isolation Forest
    if_model = joblib.load(
        MODEL_DIR / "isolation_forest_cicids2017_v2.joblib"
    )

    if_imputer = joblib.load(
        ANOMALY_DIR / "imputer.joblib"
    )

    # Feature schema
    FEATURE_COLUMNS = joblib.load(
        HYBRID_DIR / "feature_columns.joblib"
    )

    if_features = joblib.load(
        ANOMALY_DIR / "feature_columns.joblib"
    )

    if list(FEATURE_COLUMNS) != list(if_features):
        raise RuntimeError(
            "Random Forest and Isolation Forest feature order mismatch."
        )

    if len(FEATURE_COLUMNS) != 67:
        raise RuntimeError(
            "Unexpected feature count. Expected 67."
        )

    # Load frozen Random Forest threshold
    with open(
        RESULT_DIR / "rf_v2_selected_threshold.json",
        "r"
    ) as file:

        rf_config = json.load(file)

    RF_THRESHOLD = float(
        rf_config["selected_threshold"]
    )

    # Load frozen Isolation Forest threshold
    if_calibration = joblib.load(
        MODEL_DIR / "isolation_forest_calibration.joblib"
    )

    IF_THRESHOLD = float(
        if_calibration["threshold"]
    )

    # Verify model input dimensions
    if rf_model.n_features_in_ != len(FEATURE_COLUMNS):
        raise RuntimeError("Random Forest feature count mismatch.")

    if if_model.n_features_in_ != len(FEATURE_COLUMNS):
        raise RuntimeError("Isolation Forest feature count mismatch.")

    if getattr(rf_preprocessor, "n_features_in_", None) != len(FEATURE_COLUMNS):
        raise RuntimeError("Random Forest preprocessor feature count mismatch.")

    if getattr(if_imputer, "n_features_in_", None) != len(FEATURE_COLUMNS):
        raise RuntimeError("Isolation Forest imputer feature count mismatch.")

    print("Random Forest V2 loaded.")
    print("Isolation Forest V2 loaded.")
    print("Feature count:", len(FEATURE_COLUMNS))
    print("RF threshold:", RF_THRESHOLD)
    print("IF threshold:", IF_THRESHOLD)

    print("NeuroSphere Hybrid V2 ready.")


# ============================================================
# DETECTION ENDPOINT
# ============================================================

@router.post("/detect/v2")
def detect_network_traffic(
    traffic: Dict[str, Optional[float]] = Body(...)
):

    if (
        rf_model is None
        or if_model is None
        or rf_preprocessor is None
        or if_imputer is None
    ):
        raise HTTPException(
            status_code=503,
            detail="NeuroSphere V2 models are not loaded."
        )

    # --------------------------------------------------------
    # 1. Validate feature names
    # --------------------------------------------------------

    received_features = set(traffic.keys())
    expected_features = set(FEATURE_COLUMNS)

    missing_features = sorted(
        expected_features - received_features
    )

    extra_features = sorted(
        received_features - expected_features
    )

    if missing_features or extra_features:

        raise HTTPException(
            status_code=422,
            detail={
                "message": "Invalid CIC-IDS2017 feature schema.",
                "expected_feature_count": len(FEATURE_COLUMNS),
                "received_feature_count": len(traffic),
                "missing_features": missing_features,
                "extra_features": extra_features
            }
        )

    # --------------------------------------------------------
    # 2. Prepare features in exact training order
    # --------------------------------------------------------

    try:

        values = []

        for feature in FEATURE_COLUMNS:

            value = traffic[feature]

            if value is None:
                values.append(np.nan)
                continue

            numeric_value = float(value)

            if not np.isfinite(numeric_value):
                raise ValueError(
                    f"Feature '{feature}' must be finite or null."
                )

            values.append(numeric_value)

        raw_matrix = np.asarray(
            values,
            dtype=np.float64
        ).reshape(1, -1)

    except (TypeError, ValueError, OverflowError) as exc:

        raise HTTPException(
            status_code=422,
            detail=str(exc)
        )

    # --------------------------------------------------------
    # 3. Random Forest preprocessing and prediction
    # --------------------------------------------------------

    try:

        rf_input = rf_preprocessor.transform(
            raw_matrix
        )

        attack_probability = float(
            rf_model.predict_proba(rf_input)[0, 1]
        )

        rf_flagged = (
            attack_probability >= RF_THRESHOLD
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Random Forest inference failed: {exc}"
        )

    # --------------------------------------------------------
    # 4. Isolation Forest preprocessing and prediction
    # --------------------------------------------------------

    try:

        if_input = if_imputer.transform(
            raw_matrix
        )

        anomaly_score = float(
            -if_model.score_samples(if_input)[0]
        )

        if_flagged = (
            anomaly_score >= IF_THRESHOLD
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Isolation Forest inference failed: {exc}"
        )

    # --------------------------------------------------------
    # 5. Detector agreement and investigation category
    # --------------------------------------------------------

    if rf_flagged and if_flagged:

        agreement = "BOTH_FLAGGED"

        investigation_category = (
            "HIGH_CONFIDENCE_INVESTIGATION_CANDIDATE"
        )

    elif rf_flagged:

        agreement = "RF_ONLY"

        investigation_category = (
            "PRIMARY_DETECTOR_ALERT"
        )

    elif if_flagged:

        agreement = "IF_ONLY"

        investigation_category = (
            "ANOMALY_REVIEW"
        )

    else:

        agreement = "NEITHER_FLAGGED"

        investigation_category = (
            "NO_ALERT_FROM_CONFIGURED_DETECTORS"
        )

    # --------------------------------------------------------
    # 6. API response
    # --------------------------------------------------------

    return {

        "project": "NeuroSphere V2",

        "service": "AI Cybersecurity Detection Engine",

        "model_version": "Hybrid V2 - CIC-IDS2017",

        "feature_count": len(FEATURE_COLUMNS),

        "detection": {

            "random_forest": {

                "classification": (
                    "ATTACK" if rf_flagged else "NORMAL"
                ),

                "attack_probability": round(
                    attack_probability, 6
                ),

                "threshold": RF_THRESHOLD,

                "flagged": bool(rf_flagged)

            },

            "isolation_forest": {

                "classification": (
                    "ANOMALOUS" if if_flagged else "NORMAL"
                ),

                "anomaly_score": round(
                    anomaly_score, 6
                ),

                "threshold": IF_THRESHOLD,

                "flagged": bool(if_flagged)

            }

        },

        "risk_assessment": {

            "detector_agreement": agreement,

            "investigation_category": (
                investigation_category
            ),

            "automatic_blocking": False

        },

        "disclaimer": (
            "Model outputs are detection signals, not "
            "guarantees of safety or calibrated risk probabilities."
        )

    }


# ============================================================
# MODEL INFORMATION ENDPOINT
# ============================================================

@router.get("/models/v2")
def model_information():

    if rf_model is None or if_model is None:

        raise HTTPException(
            status_code=503,
            detail="Models are not loaded."
        )

    return {

        "project": "NeuroSphere V2",

        "model_version": "Hybrid V2",

        "feature_count": len(FEATURE_COLUMNS),

        "feature_names": list(FEATURE_COLUMNS),

        "random_forest": {
            "status": "loaded",
            "threshold": RF_THRESHOLD
        },

        "isolation_forest": {
            "status": "loaded",
            "threshold": IF_THRESHOLD
        }

    }
