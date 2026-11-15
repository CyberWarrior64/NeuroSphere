from pathlib import Path
import json
import numpy as np
import pandas as pd

from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "datasets" / "processed" / "hybrid_v2_training"
RESULT_DIR = BASE_DIR / "datasets" / "processed" / "hybrid_v2_results"

probabilities = np.load(
    RESULT_DIR / "rf_v2_validation_probabilities.npy"
)

y_true = np.load(DATA_DIR / "y_validation.npy")

attack_types = np.load(
    DATA_DIR / "attack_type_validation.npy",
    allow_pickle=False
)

thresholds = np.round(np.arange(0.15, 0.351, 0.01), 2)

results = []

for threshold in thresholds:

    predictions = (probabilities >= threshold).astype(np.int8)

    precision = precision_score(
        y_true, predictions, zero_division=0
    )

    recall = recall_score(
        y_true, predictions, zero_division=0
    )

    f1 = f1_score(
        y_true, predictions, zero_division=0
    )

    tn, fp, fn, tp = confusion_matrix(
        y_true, predictions, labels=[0, 1]
    ).ravel()

    fpr = fp / (fp + tn) if (fp + tn) else 0

    results.append({
        "threshold": float(threshold),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": fpr,
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp)
    })

df = pd.DataFrame(results)

df.to_csv(
    RESULT_DIR / "rf_v2_fine_threshold_analysis.csv",
    index=False
)

# Select maximum F1. If tied, prefer higher precision.
best = df.sort_values(
    ["f1", "precision"],
    ascending=[False, False]
).iloc[0]

selected_threshold = float(best["threshold"])

with open(
    RESULT_DIR / "rf_v2_selected_threshold.json",
    "w"
) as file:
    json.dump({
        "selected_threshold": selected_threshold,
        "selection_method": "Maximum Thursday validation F1",
        "validation_day": "Thursday",
        "metrics": {
            key: float(best[key])
            for key in [
                "precision", "recall", "f1",
                "false_positive_rate"
            ]
        }
    }, file, indent=4)

print("=" * 75)
print("NEUROSPHERE - RANDOM FOREST V2 FINE THRESHOLD ANALYSIS")
print("=" * 75)

print("\nThreshold comparison:")

for _, row in df.iterrows():
    print(
        f"Threshold {row['threshold']:.2f} | "
        f"Precision {row['precision']:.4f} | "
        f"Recall {row['recall']:.4f} | "
        f"F1 {row['f1']:.4f} | "
        f"FPR {row['false_positive_rate'] * 100:.4f}%"
    )

print("\nSELECTED THRESHOLD")
print("Threshold:", selected_threshold)
print(f"Precision: {best['precision']:.4f}")
print(f"Recall: {best['recall']:.4f}")
print(f"F1: {best['f1']:.4f}")
print(f"FPR: {best['false_positive_rate'] * 100:.4f}%")

# Attack-family evaluation at selected threshold
predictions = (
    probabilities >= selected_threshold
).astype(np.int8)

family_df = pd.DataFrame({
    "attack_type": attack_types,
    "actual": y_true,
    "predicted": predictions
})

print("\nATTACK-FAMILY PERFORMANCE AT SELECTED THRESHOLD")

for family, group in family_df.groupby("attack_type"):

    total = len(group)
    detected = int((group["predicted"] == 1).sum())

    print(
        f"{family:30s} | "
        f"Total: {total:7,d} | "
        f"Detected: {detected:7,d} | "
        f"Detection: {detected / total * 100:7.2f}%"
    )

family_df.groupby("attack_type").apply(
    lambda group: pd.Series({
        "total_records": len(group),
        "detected": int((group["predicted"] == 1).sum()),
        "missed": int((group["predicted"] == 0).sum()),
        "detection_rate": float((group["predicted"] == 1).mean())
    }),
    include_groups=False
).to_csv(
    RESULT_DIR / "rf_v2_selected_threshold_family_results.csv"
)

print("\nResults saved to:", RESULT_DIR)
