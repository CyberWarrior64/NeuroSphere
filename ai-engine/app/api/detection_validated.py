from __future__ import annotations

from pathlib import Path
import json
import logging
import sqlite3
from typing import Any, Dict, Optional

import joblib
import numpy as np
from fastapi import APIRouter, Body, HTTPException

from app.feature_extraction.cicflowmeter_mapper import (
    FEATURE_PARITY_AUDIT,
    FEATURE_PARITY_WARNING,
    MODEL_TO_CICFLOWMETER,
    map_cicflowmeter_record,
)
from app.feature_extraction.cicflowmeter_packet_compat import REFERENCE_ADAPTER_ID
from app.demo_event_store import record_prediction

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1",
    tags=["Experimental Validated Random-Split Detection"],
)

BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = BASE_DIR / "saved_models" / "validated_randomsplit"
RESULT_FILE = BASE_DIR / "datasets" / "processed" / "validated_randomsplit_results" / "evaluation.json"
DAY_HOLDOUT_RESULT_FILE = BASE_DIR / "datasets" / "processed" / "day_based_results" / "capture_day_holdout_evaluation.json"
HYBRID_DAY_HOLDOUT_RESULT_FILE = BASE_DIR / "datasets" / "processed" / "hybrid_v2_friday_holdout_results" / "hybrid_v2_friday_holdout_summary.json"
RAW_PACKET_SAMPLE_RESULT_FILE = BASE_DIR / "datasets" / "reference_pcaps" / "friday-reference" / "Friday-attack-windows-minute-key-evaluation.json"
INVALID_IF_NEGATIVE = {
    "Flow Duration",
    "Fwd Header Length",
    "Bwd Header Length",
    "min_seg_size_forward",
}

rf_model = None
rf_preprocessor = None
if_model = None
if_imputer = None
FEATURE_COLUMNS = []
RF_THRESHOLD = None
IF_THRESHOLD = None
EVALUATION_DESIGN = None


def load_validated_models():
    global rf_model, rf_preprocessor, if_model, if_imputer
    global FEATURE_COLUMNS, RF_THRESHOLD, IF_THRESHOLD, EVALUATION_DESIGN

    required = [
        MODEL_DIR / "random_forest.joblib",
        MODEL_DIR / "random_forest_preprocessor.joblib",
        MODEL_DIR / "isolation_forest.joblib",
        MODEL_DIR / "isolation_forest_imputer.joblib",
        MODEL_DIR / "feature_columns.joblib",
        RESULT_FILE,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"Validated random-split model files are missing: {missing}")

    rf_model = joblib.load(MODEL_DIR / "random_forest.joblib")
    rf_preprocessor = joblib.load(MODEL_DIR / "random_forest_preprocessor.joblib")
    if_model = joblib.load(MODEL_DIR / "isolation_forest.joblib")
    if_imputer = joblib.load(MODEL_DIR / "isolation_forest_imputer.joblib")
    FEATURE_COLUMNS = list(joblib.load(MODEL_DIR / "feature_columns.joblib"))
    report = json.loads(RESULT_FILE.read_text())
    RF_THRESHOLD = float(report["rf"]["threshold"])
    IF_THRESHOLD = float(report["isolation_forest"]["threshold"])
    EVALUATION_DESIGN = report["evaluation_design"]

    dimensions = [
        getattr(rf_model, "n_features_in_", None),
        getattr(rf_preprocessor, "n_features_in_", None),
        getattr(if_model, "n_features_in_", None),
        getattr(if_imputer, "n_features_in_", None),
    ]
    if len(FEATURE_COLUMNS) != 67 or dimensions != [67, 67, 67, 67]:
        raise RuntimeError("Validated models must all use the same 67-feature schema.")


@router.get("/models/validated-randomsplit")
def validated_model_information():
    if rf_model is None or if_model is None:
        raise HTTPException(status_code=503, detail="Experimental models are not loaded.")
    return {
        "model_version": "validated-randomsplit-experimental",
        "experimental": True,
        "feature_count": len(FEATURE_COLUMNS),
        "random_forest_threshold": RF_THRESHOLD,
        "isolation_forest_threshold": IF_THRESHOLD,
        "evaluation_design": EVALUATION_DESIGN,
        "caution": "Random-split metrics are not capture-day-disjoint and may overstate performance on unseen days.",
    }


@router.post("/detect/validated-randomsplit")
def detect_with_validated_models(traffic: Dict[str, Optional[float]] = Body(...)):
    if (
        rf_model is None
        or if_model is None
        or rf_preprocessor is None
        or if_imputer is None
    ):
        raise HTTPException(status_code=503, detail="Experimental models are not loaded.")

    received = set(traffic)
    expected = set(FEATURE_COLUMNS)
    missing = sorted(expected - received)
    extra = sorted(received - expected)
    if missing or extra:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Invalid CIC-IDS2017 feature schema.",
                "expected_feature_count": len(FEATURE_COLUMNS),
                "received_feature_count": len(traffic),
                "missing_features": missing,
                "extra_features": extra,
            },
        )

    values = []
    invalid_negative_features = []
    try:
        for feature in FEATURE_COLUMNS:
            value = traffic[feature]
            if value is None:
                values.append(np.nan)
                continue
            numeric = float(value)
            if not np.isfinite(numeric):
                raise ValueError(f"Feature '{feature}' must be finite or null.")
            if feature in INVALID_IF_NEGATIVE and numeric < 0:
                values.append(np.nan)
                invalid_negative_features.append(feature)
            else:
                values.append(numeric)
    except (TypeError, ValueError, OverflowError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    raw = np.asarray(values, dtype=np.float64).reshape(1, -1)
    try:
        rf_input = rf_preprocessor.transform(raw)
        attack_probability = float(rf_model.predict_proba(rf_input)[0, 1])
        rf_flagged = attack_probability >= RF_THRESHOLD
        if_input = if_imputer.transform(raw)
        anomaly_score = float(-if_model.score_samples(if_input)[0])
        if_flagged = anomaly_score >= IF_THRESHOLD
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Experimental inference failed.") from exc

    return {
        "model_version": "validated-randomsplit-experimental",
        "experimental": True,
        "evaluation_design": EVALUATION_DESIGN,
        "feature_count": len(FEATURE_COLUMNS),
        "input_warnings": {
            "negative_values_treated_as_missing": invalid_negative_features,
        },
        "detection": {
            "random_forest": {
                "classification": "ATTACK" if rf_flagged else "NORMAL",
                "attack_probability": round(attack_probability, 6),
                "threshold": RF_THRESHOLD,
                "flagged": bool(rf_flagged),
            },
            "isolation_forest": {
                "classification": "ANOMALOUS" if if_flagged else "NORMAL",
                "anomaly_score": round(anomaly_score, 6),
                "threshold": IF_THRESHOLD,
                "flagged": bool(if_flagged),
            },
        },
        "caution": "Experimental random-split models; not validated on a capture-day-disjoint holdout. Do not use as an automatic blocking decision.",
    }

@router.get("/capture/cicflowmeter-python/readiness")
def cicflowmeter_python_readiness():
    """Describe adapter support and current evaluation evidence."""
    day_holdout = None
    if DAY_HOLDOUT_RESULT_FILE.is_file():
        report = json.loads(DAY_HOLDOUT_RESULT_FILE.read_text())
        day_holdout = {
            "report": str(DAY_HOLDOUT_RESULT_FILE.relative_to(BASE_DIR)),
            "evaluation_name": report.get("evaluation_name"),
            "status": report.get("status"),
            "training_days": report.get("training_days"),
            "test_day": report.get("test_day"),
            "train_rows": report.get("train_rows"),
            "test_rows": report.get("test_rows"),
            "threshold_0_5_metrics": report.get("threshold_0_5_metrics"),
            "roc_auc": report.get("roc_auc"),
            "average_precision": report.get("average_precision"),
            "attack_family_at_threshold_0_5": report.get("attack_family_at_threshold_0_5"),
            "limitations": report.get("limitations"),
        }
    hybrid_holdout = None
    if HYBRID_DAY_HOLDOUT_RESULT_FILE.is_file():
        report = json.loads(HYBRID_DAY_HOLDOUT_RESULT_FILE.read_text())
        hybrid_holdout = {
            "report": str(HYBRID_DAY_HOLDOUT_RESULT_FILE.relative_to(BASE_DIR)),
            "evaluation": report.get("evaluation"),
            "status": report.get("status"),
            "training_days": report.get("training_days"),
            "validation_day": report.get("validation_day"),
            "test_day": report.get("test_day"),
            "training_rows": report.get("training_rows"),
            "validation_rows": report.get("validation_rows"),
            "test_rows": report.get("test_rows"),
            "feature_count": report.get("feature_count"),
            "rf_threshold": report.get("rf_threshold"),
            "if_threshold": report.get("if_threshold"),
            "thresholds_frozen_before_friday": report.get("thresholds_frozen_before_friday"),
            "metrics": report.get("metrics"),
            "attack_family_metrics": report.get("attack_family_metrics"),
            "limitations": report.get("limitations"),
        }
    raw_packet_sample = None
    if RAW_PACKET_SAMPLE_RESULT_FILE.is_file():
        report = json.loads(RAW_PACKET_SAMPLE_RESULT_FILE.read_text())
        parity = report.get("feature_parity", {})
        raw_packet_sample = {
            "report": str(RAW_PACKET_SAMPLE_RESULT_FILE.relative_to(BASE_DIR)),
            "evaluation": report.get("evaluation"),
            "status": report.get("status"),
            "input_pcap": report.get("input_pcap"),
            "matching_method": report.get("matching_method"),
            "reference_timestamp_resolution": report.get("reference_timestamp_resolution"),
            "selected_windows_utc": report.get("selected_windows_utc"),
            "generated_flows": report.get("generated_flows"),
            "unique_direct_matches": report.get("unique_direct_matches"),
            "matched_label_counts": report.get("matched_label_counts"),
            "attack_family_match_coverage_in_selected_windows": report.get("attack_family_match_coverage_in_selected_windows"),
            "feature_parity": {
                "feature_cell_agreement": parity.get("feature_cell_agreement"),
                "exact_core_fraction": parity.get("exact_core_fraction"),
                "complete_67_feature_rows": parity.get("complete_67_feature_rows"),
                "feature_parity_verified": parity.get("feature_parity_verified"),
                "lowest_agreement_features": [
                    {"feature": name, "agreement": float(value)}
                    for name, value in sorted(
                        parity.get("per_feature_agreement", {}).items(), key=lambda item: item[1]
                    )[:10]
                ],
            },
            "hybrid_v2_models_on_direct_matches": report.get("hybrid_v2_models_on_direct_matches"),
            "limitations": report.get("limitations"),
        }

    blockers = [
        "The Monday first-100,000-packet comparison found 92.17% feature-cell agreement across 5,831 unique direct flows; 4,547 full 67-feature vectors matched.",
        "The four-window Monday capture comparison found 88.90% cell agreement across 3,905 direct matches and 2,700 full vectors; an upstream-FIN candidate reached 89.85% but remains inactive.",
        "The primary Hybrid V2 API models were evaluated on a Friday capture-day holdout with thresholds frozen on Thursday: Random Forest recall was 28.84% at 0.29% FPR; Isolation Forest recall was 19.71% at 5.13% FPR. PortScan and Bot recall remained near zero. The separate 0.5-threshold Random Forest baseline is also reported above.",
        "These holdouts use derived flow tables from the same CICIDS2017 benchmark, not raw-PCAP replay through the packet adapter or an external network. The exact CICFlowMeter build, full flow-boundary/timeout/closure parity, external-capture quality, and single-flow calibration remain unverified.",
    ]
    if raw_packet_sample:
        family_coverage = raw_packet_sample.get("attack_family_match_coverage_in_selected_windows", {})
        detectors = raw_packet_sample.get("hybrid_v2_models_on_direct_matches", {}).get("detectors", {})
        rf = detectors.get("random_forest", {})
        isolation = detectors.get("isolation_forest", {})
        coverage_summary = ", ".join(
            f"{family} {family_coverage[family]['direct_match_rate']:.2%}"
            for family in ("DDoS", "PortScan", "Bot")
            if family in family_coverage and family_coverage[family].get("direct_match_rate") is not None
        )
        if coverage_summary and rf.get("recall") is not None and isolation.get("recall") is not None:
            blockers.append(
                "The multi-window Friday raw-PCAP sample matched "
                f"{raw_packet_sample.get('unique_direct_matches')} unique flows (attack-family coverage: {coverage_summary}); "
                f"frozen-threshold RF recall was {rf['recall']:.2%} at {rf['false_positive_rate']:.2%} FPR and "
                f"Isolation Forest recall was {isolation['recall']:.2%} at {isolation['false_positive_rate']:.2%} FPR. "
                "Feature parity and full-day representativeness remain unverified."
            )
            weakest = raw_packet_sample.get("feature_parity", {}).get("lowest_agreement_features", [])
            if weakest:
                summary = ", ".join(f"{item['feature']} {item['agreement']:.1%}" for item in weakest[:4])
                blockers.append(f"The weakest raw-PCAP feature agreements are {summary}; investigate these against the exact training-generator build before changing formulas.")
        else:
            blockers.append("A targeted Friday raw-PCAP sample is available, but its current report does not contain complete match-coverage and model metrics.")

    return {
        "capture_tool": "cicflowmeter-python-0.5.0",
        "adapter_available": True,
        "adapter_id": REFERENCE_ADAPTER_ID,
        "model_feature_count": len(FEATURE_COLUMNS),
        "mapped_feature_count": len(MODEL_TO_CICFLOWMETER),
        "feature_parity_verified": False,
        "packet_level_reference_adapter": {
            "available": True,
            "command": ".venv/bin/python -m app.feature_extraction.run_reference_capture -i <INTERFACE> -u http://127.0.0.1:8000/api/v1/detect/cicflowmeter-python",
            "recalculates_from_raw_packets": [
                "payload-based packet lengths and byte totals",
                "header-derived fields with packet-order inference; exact semantics remain unverified",
                "flow and directional IAT statistics",
                "ratio, subflow, and initial-window fields",
                "active and idle timing",
            ],
            "parity_verified": False,
        },
        "feature_parity_audit": FEATURE_PARITY_AUDIT,
        "comparison_report": "datasets/reference_pcaps/Monday-first-100000-feature-parity.json",
        "distributed_window_report": "datasets/reference_pcaps/spaced-windows-25k/results-final/spaced-windows-parity-summary.json",
        "capture_day_holdout": day_holdout,
        "hybrid_v2_capture_day_holdout": hybrid_holdout,
        "raw_packet_adapter_sample": raw_packet_sample,
        "blockers": blockers,
        "safe_use": "Experimental research only; do not automate blocking or alert escalation from these predictions.",
    }


@router.post("/detect/cicflowmeter-python")
def detect_cicflowmeter_python_record(traffic: Dict[str, Any] = Body(...)):
    """Accept one CICFlowMeter Python 0.5.0 flow record and map it to the model schema."""
    try:
        mapped, negative_as_missing = map_cicflowmeter_record(traffic)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result = detect_with_validated_models(mapped)
    reference_adapter = traffic.get("_feature_extractor") == REFERENCE_ADAPTER_ID
    result["input_source"] = (
        REFERENCE_ADAPTER_ID
        if reference_adapter
        else "cicflowmeter-python-0.5.0"
    )
    capture_mode = traffic.get("_capture_mode")
    if not isinstance(capture_mode, str) or capture_mode not in {"live", "pcap"}:
        capture_mode = "unspecified"
    result["capture_mode"] = capture_mode
    result["feature_parity_verified"] = False
    result["packet_level_reference_features"] = reference_adapter
    result["input_warnings"]["negative_values_treated_as_missing"] = negative_as_missing
    if reference_adapter:
        result["input_warnings"]["unverified_feature_groups"] = [
            "header-derived feature parity",
            "flow segmentation, timeout, and FIN/RST closure semantics",
            "exact CICFlowMeter release used for training",
            "single-flow calibration and independent-capture generalization",
        ]
        result["caution"] = (
            "Packet features use a training-table-calibrated experimental port. The 100,000-packet comparison showed 92.17% feature-cell agreement, with 4,547 of 5,831 matched flows agreeing on all 67 fields. Among 4,899 core-exact flows, cell agreement was 99.62%. "
            "Header parity, exact generator version, and broader flow-boundary behavior remain unverified. Research only; do not automate blocking."
        )
    else:
        result["input_warnings"]["unverified_feature_groups"] = [
            "packet lengths and byte totals",
            "IP/transport header lengths",
            "inter-arrival times",
            "ratio and subflow statistics",
            "active/idle statistics",
        ]
        result["caution"] = (
            FEATURE_PARITY_WARNING
            + " This endpoint is experimental and must not be used for automatic blocking."
        )
    try:
        record_prediction(result["input_source"], result, capture_mode)
    except sqlite3.Error:
        logger.exception("Could not save metadata-only demo prediction history.")
    return result
