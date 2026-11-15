from __future__ import annotations
import json
import os
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, average_precision_score, classification_report,
    confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score,
    roc_curve,
)

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "datasets/processed/day_based_training"
RESULT_DIR = ROOT / "datasets/processed/day_based_results"
MODEL_PATH = ROOT / "saved_models/random_forest_cicids2017_day_holdout.joblib"
SUMMARY_PATH = RESULT_DIR / "capture_day_holdout_evaluation.json"
THRESHOLD_PATH = RESULT_DIR / "capture_day_holdout_threshold_sweep.csv"


def metrics_at(y_true: np.ndarray, scores: np.ndarray, threshold: float) -> dict:
    pred = (scores >= threshold).astype(np.int8)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, pred)),
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred, zero_division=0)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
        "false_positive_rate": float(fp / (fp + tn)) if (fp + tn) else 0.0,
        "true_negatives": int(tn), "false_positives": int(fp),
        "false_negatives": int(fn), "true_positives": int(tp),
    }


def main() -> None:
    model = joblib.load(MODEL_PATH)
    x_test = np.load(DATA_DIR / "X_test.npy", mmap_mode="r")
    y_test = np.load(DATA_DIR / "y_test.npy")
    attack_types = np.load(DATA_DIR / "attack_type_test.npy", allow_pickle=False)
    source_files = np.load(DATA_DIR / "source_file_test.npy", allow_pickle=False)
    if len(x_test) != len(y_test) or len(y_test) != len(attack_types) or len(y_test) != len(source_files):
        raise RuntimeError("Prepared test arrays have inconsistent row counts.")
    scores = model.predict_proba(x_test)[:, 1]
    y_pred = (scores >= 0.5).astype(np.int8)
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred, labels=[0, 1]).ravel()
    current = metrics_at(y_test, scores, 0.5)

    family_results = []
    for family in sorted(set(attack_types.tolist())):
        mask = attack_types == family
        detected = int(np.sum(y_pred[mask] == 1))
        total = int(mask.sum())
        family_results.append({
            "attack_type": str(family), "total_records": total,
            "detected": detected, "missed": total - detected,
            "detection_rate": detected / total if total else 0.0,
        })

    source_results = []
    for source in sorted(set(source_files.tolist())):
        mask = source_files == source
        source_results.append({
            "source_file": str(source), "total_records": int(mask.sum()),
            "attack_records": int(np.sum(y_test[mask] == 1)),
            "detected_attacks": int(np.sum((y_test[mask] == 1) & (y_pred[mask] == 1))),
            "false_positives": int(np.sum((y_test[mask] == 0) & (y_pred[mask] == 1))),
        })

    thresholds = [0.5, 0.4, 0.3, 0.25, 0.2, 0.15, 0.1, 0.05, 0.02, 0.01, 0.005, 0.001]
    threshold_rows = [metrics_at(y_test, scores, value) for value in thresholds]
    threshold_frame = pd.DataFrame(threshold_rows)
    threshold_part = THRESHOLD_PATH.with_suffix(THRESHOLD_PATH.suffix + ".part")
    threshold_frame.to_csv(threshold_part, index=False)
    os.replace(threshold_part, THRESHOLD_PATH)

    fpr_values, tpr_values, roc_thresholds = roc_curve(y_test, scores)
    acceptable = np.flatnonzero(fpr_values <= 0.01)
    constrained_index = int(acceptable[np.argmax(tpr_values[acceptable])]) if len(acceptable) else None
    report = {
        "evaluation_name": "CICIDS2017 capture-day holdout",
        "status": "experimental; separate evaluation-only model",
        "training_days": ["Monday", "Tuesday", "Wednesday", "Thursday"],
        "test_day": "Friday",
        "model_artifact": str(MODEL_PATH.relative_to(ROOT)),
        "serving_model_changed": False,
        "model_feature_count": int(x_test.shape[1]),
        "train_rows": int(np.load(DATA_DIR / "y_train.npy", mmap_mode="r").shape[0]),
        "test_rows": int(len(y_test)),
        "test_class_counts": {str(int(k)): int(v) for k, v in zip(*np.unique(y_test, return_counts=True))},
        "test_attack_family_counts": {str(k): int(v) for k, v in sorted(Counter(attack_types.tolist()).items())},
        "threshold_0_5_metrics": current,
        "roc_auc": float(roc_auc_score(y_test, scores)),
        "average_precision": float(average_precision_score(y_test, scores)),
        "classification_report": classification_report(y_test, y_pred, labels=[0, 1], target_names=["NORMAL", "ATTACK"], output_dict=True, zero_division=0),
        "attack_family_at_threshold_0_5": family_results,
        "source_file_at_threshold_0_5": source_results,
        "max_recall_with_fpr_at_most_1_percent": (
            {"threshold": float(roc_thresholds[constrained_index]), "recall": float(tpr_values[constrained_index]), "false_positive_rate": float(fpr_values[constrained_index])}
            if constrained_index is not None else None
        ),
        "threshold_sweep_csv": str(THRESHOLD_PATH.relative_to(ROOT)),
        "dataset_lineage": "Day-specific flow Parquets from the checksum-verified Hugging Face mirror; same CICIDS2017 benchmark as the existing project dataset.",
        "limitations": [
            "This is a capture-day-disjoint evaluation of labeled flow tables, not a raw-PCAP replay through the packet adapter.",
            "PortScan and Bot appear only in Friday test data and are not represented as labeled attack families in Monday-Thursday training data.",
            "Feature parity with the exact CICFlowMeter build used for the training tables is not established.",
            "Do not use for automated blocking or alert escalation.",
        ],
    }
    summary_part = SUMMARY_PATH.with_suffix(SUMMARY_PATH.suffix + ".part")
    summary_part.write_text(json.dumps(report, indent=2) + "\n")
    os.replace(summary_part, SUMMARY_PATH)
    print(json.dumps({
        "summary": str(SUMMARY_PATH),
        "threshold_sweep": str(THRESHOLD_PATH),
        "metrics_at_0_5": current,
        "roc_auc": report["roc_auc"],
        "average_precision": report["average_precision"],
        "max_recall_fpr_le_1pct": report["max_recall_with_fpr_at_most_1_percent"],
        "family_metrics": family_results,
        "threshold_sweep": threshold_rows,
    }, indent=2))


if __name__ == "__main__":
    main()
