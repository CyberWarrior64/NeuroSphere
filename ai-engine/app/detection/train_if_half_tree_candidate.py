"""Fit an isolated 150-tree Isolation Forest candidate and evaluate it once.

Uses the normal-only prepared training data, calibrates on Thursday normals,
and performs one frozen-threshold Friday evaluation. Active artifacts are read
for comparison but are never overwritten.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "datasets" / "processed" / "anomaly_training"
ACTIVE_MODEL_PATH = BASE_DIR / "saved_models" / "isolation_forest_cicids2017_v2.joblib"
ACTIVE_CALIBRATION_PATH = BASE_DIR / "saved_models" / "isolation_forest_calibration.joblib"

candidate_id = datetime.now(timezone.utc).strftime("if-150-tree-%Y%m%dT%H%M%SZ")
candidate_root = BASE_DIR / "saved_models" / "candidates" / candidate_id
result_root = BASE_DIR / "datasets" / "processed" / "candidate_results" / candidate_id
candidate_root.mkdir(parents=True, exist_ok=False)
result_root.mkdir(parents=True, exist_ok=False)

print("Loading prepared arrays and active Isolation Forest...")
X_train = np.load(DATA_DIR / "X_train.npy")
X_validation = np.load(DATA_DIR / "X_validation.npy", mmap_mode="r")
X_test = np.load(DATA_DIR / "X_test.npy", mmap_mode="r")
y_test = np.load(DATA_DIR / "y_test.npy", mmap_mode="r")
attack_types = np.load(DATA_DIR / "attack_type_test.npy", allow_pickle=True)

active_model = joblib.load(ACTIVE_MODEL_PATH)
active_calibration = joblib.load(ACTIVE_CALIBRATION_PATH)
active_threshold = float(active_calibration["threshold"])
if active_model.n_estimators != 300:
    raise RuntimeError(f"Expected active 300-tree model; found {active_model.n_estimators} trees.")
if len({X_train.shape[1], X_validation.shape[1], X_test.shape[1], active_model.n_features_in_}) != 1:
    raise RuntimeError("Training, validation, test, and active model feature counts differ.")
if len(X_validation) == 0 or len(X_test) != len(y_test) or len(y_test) != len(attack_types):
    raise RuntimeError("Validation/test arrays are empty or misaligned.")


def score_batches(model, data, description: str) -> np.ndarray:
    batch_size = 100_000
    scores = np.empty(len(data), dtype=np.float64)
    for start in range(0, len(data), batch_size):
        end = min(start + batch_size, len(data))
        scores[start:end] = -model.score_samples(data[start:end])
        print(f"{description}: {end:,}/{len(data):,}")
    return scores


def metrics(y_true, scores: np.ndarray, threshold: float) -> dict:
    predictions = (scores >= threshold).astype(np.int8)
    tn, fp, fn, tp = confusion_matrix(y_true, predictions, labels=[0, 1]).ravel()
    return {
        "threshold": threshold,
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, scores)),
        "pr_auc": float(average_precision_score(y_true, scores)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "false_positive_rate": float(fp / (fp + tn)) if fp + tn else 0.0,
    }


parameters = {
    "max_samples": 4096,
    "contamination": "auto",
    "max_features": 1.0,
    "bootstrap": False,
    "n_jobs": -1,
    "random_state": 42,
}

print(f"Training normal rows: {len(X_train):,}; features: {X_train.shape[1]}")
print(f"Thursday normal validation rows: {len(X_validation):,}; Friday rows: {len(X_test):,}")

candidate = IsolationForest(n_estimators=150, verbose=1, **parameters)
print("Training isolated 150-tree candidate...")
start = time.perf_counter()
candidate.fit(X_train)
candidate_fit_seconds = time.perf_counter() - start

candidate_model_path = candidate_root / "isolation_forest_150_trees.joblib"
joblib.dump(candidate, candidate_model_path, compress=3)

print("Calibrating candidate on Thursday normals at 1% target FPR...")
candidate_validation_scores = score_batches(candidate, X_validation, "Candidate Thursday calibration")
candidate_threshold = float(np.quantile(candidate_validation_scores, 0.99))
candidate_validation_fpr = float(np.mean(candidate_validation_scores >= candidate_threshold))

print("Scoring active model on same Thursday and Friday arrays...")
active_validation_scores = score_batches(active_model, X_validation, "Active Thursday calibration audit")
active_actual_validation_fpr = float(np.mean(active_validation_scores >= active_threshold))

print("Scoring both models on Friday once with Thursday-frozen thresholds...")
candidate_test_scores = score_batches(candidate, X_test, "Candidate Friday holdout")
active_test_scores = score_batches(active_model, X_test, "Active Friday holdout")

active_validation_metrics = {
    "stored_threshold": active_threshold,
    "actual_fpr_on_regenerated_thursday_normals": active_actual_validation_fpr,
}
candidate_validation_metrics = {
    "target_fpr": 0.01,
    "threshold": candidate_threshold,
    "actual_fpr": candidate_validation_fpr,
}

candidate_predictions = candidate_test_scores >= candidate_threshold
active_predictions = active_test_scores >= active_threshold
family_frame = pd.DataFrame({
    "attack_type": attack_types.astype(str),
    "actual": y_test,
    "active_prediction": active_predictions,
    "candidate_prediction": candidate_predictions,
})
family_rows = []
for family, group in family_frame.groupby("attack_type"):
    attack_rows = int(group["actual"].sum())
    family_rows.append({
        "attack_type": str(family),
        "total_rows": int(len(group)),
        "attack_rows": attack_rows,
        "active_detected": int(group["active_prediction"].sum()),
        "candidate_detected": int(group["candidate_prediction"].sum()),
        "active_attack_recall": float((group["active_prediction"] & group["actual"]).sum() / attack_rows) if attack_rows else None,
        "candidate_attack_recall": float((group["candidate_prediction"] & group["actual"]).sum() / attack_rows) if attack_rows else None,
    })

family_path = result_root / "friday_attack_family_metrics.csv"
pd.DataFrame(family_rows).to_csv(family_path, index=False)

friday_candidate_metrics = metrics(y_test, candidate_test_scores, candidate_threshold)
friday_active_metrics = metrics(y_test, active_test_scores, active_threshold)
summary = {
    "status": "isolated candidate; active model and API artifacts unchanged",
    "candidate_id": candidate_id,
    "training_rows": int(len(X_train)),
    "validation_normal_rows": int(len(X_validation)),
    "friday_rows": int(len(X_test)),
    "feature_count": int(X_train.shape[1]),
    "candidate_parameters": {"n_estimators": 150, **parameters},
    "candidate_fit_time_seconds": round(candidate_fit_seconds, 3),
    "candidate_model": str(candidate_model_path.relative_to(BASE_DIR)),
    "candidate_model_bytes": candidate_model_path.stat().st_size,
    "active_model_bytes": ACTIVE_MODEL_PATH.stat().st_size,
    "candidate_thursday_calibration": candidate_validation_metrics,
    "active_thursday_calibration_audit": active_validation_metrics,
    "candidate_friday_metrics": friday_candidate_metrics,
    "active_friday_metrics": friday_active_metrics,
    "family_metrics_csv": str(family_path.relative_to(BASE_DIR)),
    "limitations": [
        "Candidate threshold was calibrated on Thursday normal traffic and frozen before Friday scoring.",
        "Friday comes from the CICIDS2017 benchmark; it is not an external network capture.",
        "Model quality and feature parity limitations remain; research only, no automated blocking or alert escalation.",
    ],
}
summary_path = result_root / "summary.json"
summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

print("\nCandidate run complete.")
print(json.dumps(summary, indent=2))
print(f"Summary saved: {summary_path}")

print("\nTraining a separate 300-tree timing baseline with the same parameters...")
baseline = IsolationForest(n_estimators=300, verbose=0, **parameters)
start = time.perf_counter()
baseline.fit(X_train)
baseline_fit_seconds = time.perf_counter() - start
summary["same_data_300_tree_fit_benchmark_seconds"] = round(baseline_fit_seconds, 3)
summary["fit_time_reduction_fraction"] = float(1 - candidate_fit_seconds / baseline_fit_seconds)
summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(f"SAME_CONFIG_300_TREE_FIT_SECONDS={baseline_fit_seconds:.3f}")
print(f"FIT_TIME_REDUCTION={summary['fit_time_reduction_fraction']:.4%}")
