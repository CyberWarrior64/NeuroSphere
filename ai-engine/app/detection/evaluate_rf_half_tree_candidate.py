"""One-pass Friday evaluation for an isolated half-tree RF candidate.

The candidate threshold is read from the Thursday-only calibration summary and
is not adjusted using Friday. Active model files are read but never written.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


parser = argparse.ArgumentParser()
parser.add_argument("candidate_id", help="Timestamped RF candidate folder name")
args = parser.parse_args()

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "datasets" / "processed" / "hybrid_v2_training"
RESULT_DIR = BASE_DIR / "datasets" / "processed" / "candidate_results" / args.candidate_id
CANDIDATE_DIR = BASE_DIR / "saved_models" / "candidates" / args.candidate_id
ACTIVE_PATH = BASE_DIR / "saved_models" / "random_forest_cicids2017_hybrid_v2.joblib"

summary_path = RESULT_DIR / "summary.json"
summary = json.loads(summary_path.read_text(encoding="utf-8"))
candidate_threshold = float(summary["candidate_threshold_selected_on_thursday"])
candidate_path = CANDIDATE_DIR / "random_forest_50_trees.joblib"
active_threshold_data = json.loads(
    (BASE_DIR / "datasets" / "processed" / "hybrid_v2_results" / "rf_v2_selected_threshold.json")
    .read_text(encoding="utf-8")
)
active_threshold = float(active_threshold_data["selected_threshold"])

X_test = np.load(DATA_DIR / "X_test.npy", mmap_mode="r")
y_test = np.load(DATA_DIR / "y_test.npy", mmap_mode="r")
attack_types = np.load(DATA_DIR / "attack_type_test.npy", allow_pickle=False)
source_files = np.load(DATA_DIR / "source_file_test.npy", allow_pickle=False)

active_model = joblib.load(ACTIVE_PATH)
candidate_model = joblib.load(candidate_path)
if len(X_test) != len(y_test) or len(y_test) != len(attack_types) or len(y_test) != len(source_files):
    raise RuntimeError("Friday feature, label, family, and source arrays are misaligned.")


def score_in_batches(model, threshold: float, name: str) -> tuple[dict, np.ndarray]:
    predictions = np.empty(len(y_test), dtype=np.int8)
    probabilities = np.empty(len(y_test), dtype=np.float32)
    batch_size = 100_000
    for start in range(0, len(y_test), batch_size):
        end = min(start + batch_size, len(y_test))
        batch_probabilities = model.predict_proba(X_test[start:end])[:, 1]
        probabilities[start:end] = batch_probabilities
        predictions[start:end] = batch_probabilities >= threshold
        print(f"{name}: scored {end:,}/{len(y_test):,}")

    tn, fp, fn, tp = confusion_matrix(y_test, predictions, labels=[0, 1]).ravel()
    metrics = {
        "threshold_frozen_from_thursday": threshold,
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "f1": float(f1_score(y_test, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "pr_auc": float(average_precision_score(y_test, probabilities)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
        "false_positive_rate": float(fp / (fp + tn)) if fp + tn else 0.0,
    }
    return metrics, predictions


active_metrics, active_predictions = score_in_batches(active_model, active_threshold, "Active 100-tree model")
candidate_metrics, candidate_predictions = score_in_batches(candidate_model, candidate_threshold, "Candidate 50-tree model")

family_rows = []
families = pd.DataFrame({
    "attack_type": attack_types,
    "source_file": source_files,
    "actual": y_test,
    "active_prediction": active_predictions,
    "candidate_prediction": candidate_predictions,
})
for (family, source), group in families.groupby(["attack_type", "source_file"], dropna=False):
    actual_attacks = int(group["actual"].sum())
    active_detected = int(group["active_prediction"].sum())
    candidate_detected = int(group["candidate_prediction"].sum())
    family_rows.append({
        "attack_type": str(family),
        "source_file": str(source),
        "total_rows": int(len(group)),
        "attack_rows": actual_attacks,
        "active_detected": active_detected,
        "candidate_detected": candidate_detected,
        "active_attack_recall": float((group["active_prediction"] & group["actual"]).sum() / actual_attacks) if actual_attacks else None,
        "candidate_attack_recall": float((group["candidate_prediction"] & group["actual"]).sum() / actual_attacks) if actual_attacks else None,
    })

family_path = RESULT_DIR / "friday_attack_family_metrics.csv"
pd.DataFrame(family_rows).to_csv(family_path, index=False)

friday_summary = {
    "status": "one-pass held-out Friday evaluation; no Friday threshold selection or tuning",
    "candidate_id": args.candidate_id,
    "test_day": "Friday",
    "test_rows": int(len(y_test)),
    "feature_count": int(X_test.shape[1]),
    "active_100_tree_metrics": active_metrics,
    "candidate_50_tree_metrics": candidate_metrics,
    "attack_family_report": str(family_path.relative_to(BASE_DIR)),
    "limitations": [
        "The held-out data is from CICIDS2017, the same benchmark family as training.",
        "This is not an independent network capture or proof of CICFlowMeter feature parity.",
        "Do not use the candidate for automated blocking or alert escalation.",
    ],
}
friday_path = RESULT_DIR / "friday_summary.json"
friday_path.write_text(json.dumps(friday_summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(friday_summary, indent=2))
print(f"Friday summary saved: {friday_path}")
