"""Train and assess an isolated 50-tree RF candidate against the current RF.

This experiment reads the existing V2 prepared arrays and active model but
never writes to the active model or result paths.  It uses the existing frozen
Thursday validation threshold from ``rf_v2_selected_threshold.json``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import time

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.metrics import precision_recall_curve


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "datasets" / "processed" / "hybrid_v2_training"
ACTIVE_MODEL_PATH = BASE_DIR / "saved_models" / "random_forest_cicids2017_hybrid_v2.joblib"
THRESHOLD_PATH = BASE_DIR / "datasets" / "processed" / "hybrid_v2_results" / "rf_v2_selected_threshold.json"

candidate_id = datetime.now(timezone.utc).strftime("rf-50-tree-%Y%m%dT%H%M%SZ")
candidate_root = BASE_DIR / "saved_models" / "candidates" / candidate_id
result_root = BASE_DIR / "datasets" / "processed" / "candidate_results" / candidate_id
candidate_root.mkdir(parents=True, exist_ok=False)
result_root.mkdir(parents=True, exist_ok=False)

print("Loading prepared arrays and active model...")
X_train = np.load(DATA_DIR / "X_train.npy")
y_train = np.load(DATA_DIR / "y_train.npy")
X_validation = np.load(DATA_DIR / "X_validation.npy")
y_validation = np.load(DATA_DIR / "y_validation.npy")

with THRESHOLD_PATH.open(encoding="utf-8") as handle:
    selected_threshold = float(json.load(handle)["selected_threshold"])

active_model = joblib.load(ACTIVE_MODEL_PATH)
if active_model.n_estimators != 100:
    raise RuntimeError(
        f"Expected the active 100-tree baseline; found {active_model.n_estimators} trees."
    )
if len({X_train.shape[1], X_validation.shape[1], active_model.n_features_in_}) != 1:
    raise RuntimeError("Training, validation, and active model feature counts differ.")
if len(X_train) != len(y_train) or len(X_validation) != len(y_validation):
    raise RuntimeError("Feature and label array lengths differ.")


def measure_probabilities(y, probabilities, threshold: float) -> dict:
    predictions = (probabilities >= threshold).astype(np.int8)
    tn, fp, fn, tp = confusion_matrix(y, predictions, labels=[0, 1]).ravel()
    return {
        "threshold": threshold,
        "accuracy": float(accuracy_score(y, predictions)),
        "precision": float(precision_score(y, predictions, zero_division=0)),
        "recall": float(recall_score(y, predictions, zero_division=0)),
        "f1": float(f1_score(y, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, probabilities)),
        "pr_auc": float(average_precision_score(y, probabilities)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "false_positive_rate": float(fp / (fp + tn)) if fp + tn else 0.0,
    }


print(f"Training records: {len(X_train):,}; features: {X_train.shape[1]}")
print(f"Thursday validation records: {len(X_validation):,}")
print(f"Using frozen threshold: {selected_threshold:.6f}")
print("Scoring active 100-tree model on Thursday validation...")
active_probabilities = active_model.predict_proba(X_validation)[:, 1]
active_metrics = measure_probabilities(y_validation, active_probabilities, selected_threshold)

candidate = RandomForestClassifier(
    n_estimators=50,
    max_depth=25,
    min_samples_leaf=2,
    class_weight="balanced",
    n_jobs=-1,
    random_state=42,
    verbose=1,
)

print("Training isolated 50-tree candidate...")
start = time.perf_counter()
candidate.fit(X_train, y_train)
training_seconds = time.perf_counter() - start

print("Scoring candidate on Thursday validation...")
candidate_probabilities = candidate.predict_proba(X_validation)[:, 1]
candidate_metrics = measure_probabilities(y_validation, candidate_probabilities, selected_threshold)
pr_precision, pr_recall, pr_thresholds = precision_recall_curve(
    y_validation, candidate_probabilities
)
calibration_f1 = (
    2 * pr_precision[:-1] * pr_recall[:-1]
    / np.maximum(pr_precision[:-1] + pr_recall[:-1], 1e-15)
)
best_threshold_index = int(np.argmax(calibration_f1))
candidate_calibrated_threshold = float(pr_thresholds[best_threshold_index])
candidate_calibrated_metrics = measure_probabilities(
    y_validation, candidate_probabilities, candidate_calibrated_threshold
)

model_path = candidate_root / "random_forest_50_trees.joblib"
joblib.dump(candidate, model_path, compress=3)
model_bytes = model_path.stat().st_size

summary = {
    "status": "candidate only; active model and production thresholds unchanged",
    "candidate_id": candidate_id,
    "candidate_model": str(model_path.relative_to(BASE_DIR)),
    "candidate_model_bytes": model_bytes,
    "training_data": str(DATA_DIR.relative_to(BASE_DIR)),
    "training_records": int(len(X_train)),
    "validation_records": int(len(X_validation)),
    "feature_count": int(X_train.shape[1]),
    "candidate_parameters": {
        "n_estimators": candidate.n_estimators,
        "max_depth": candidate.max_depth,
        "min_samples_leaf": candidate.min_samples_leaf,
        "class_weight": candidate.class_weight,
        "random_state": candidate.random_state,
        "n_jobs": candidate.n_jobs,
    },
    "training_time_seconds": round(training_seconds, 3),
    "threshold_source": str(THRESHOLD_PATH.relative_to(BASE_DIR)),
    "threshold_frozen_before_candidate_evaluation": selected_threshold,
    "candidate_threshold_selected_on_thursday": candidate_calibrated_threshold,
    "validation_day": "Thursday",
    "active_100_tree_validation_metrics": active_metrics,
    "candidate_50_tree_metrics_at_active_threshold": candidate_metrics,
    "candidate_50_tree_validation_metrics_at_own_thursday_threshold": candidate_calibrated_metrics,
    "limitations": [
        "The candidate threshold and its calibrated metrics were selected on the existing Thursday validation split, not an external capture.",
        "Friday was not used to train or select the candidate; a single frozen-threshold evaluation was run separately afterward.",
        "A shorter tree count may reduce training time but can change model quality.",
        "The candidate is not wired into the API and is not approved for operational use.",
    ],
}

summary_path = result_root / "summary.json"
summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

print("\nCandidate training complete.")
print(json.dumps(summary, indent=2))
print(f"Summary saved: {summary_path}")
