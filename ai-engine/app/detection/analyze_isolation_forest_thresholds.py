
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix
)

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "datasets" / "processed" / "anomaly_training"
MODEL_DIR = BASE_DIR / "saved_models"
RESULT_DIR = BASE_DIR / "datasets" / "processed" / "anomaly_threshold_results"

RESULT_DIR.mkdir(parents=True, exist_ok=True)

BATCH_SIZE = 100_000

# Candidate false-positive rates on Thursday normal validation data
TARGET_FPRS = [0.005, 0.01, 0.02, 0.03, 0.05]

print("=" * 70)
print("NEUROSPHERE - ISOLATION FOREST THRESHOLD ANALYSIS")
print("=" * 70)

# Load V2 model and datasets
model = joblib.load(
    MODEL_DIR / "isolation_forest_cicids2017_v2.joblib"
)

X_val = np.load(DATA_DIR / "X_validation.npy")
X_test = np.load(DATA_DIR / "X_test.npy")
y_test = np.load(DATA_DIR / "y_test.npy")

attack_types = np.load(
    DATA_DIR / "attack_type_test.npy",
    allow_pickle=True
)

if X_val.shape[1] != X_test.shape[1]:
    raise ValueError("Validation and test feature counts do not match.")

if len(X_test) != len(y_test) or len(X_test) != len(attack_types):
    raise ValueError("Test data lengths do not match.")

print("Validation shape:", X_val.shape)
print("Test shape:", X_test.shape)


def calculate_scores(data, description):
    scores = []

    print(f"\nScoring {description}...")

    for start in range(0, len(data), BATCH_SIZE):
        end = min(start + BATCH_SIZE, len(data))

        batch_scores = -model.score_samples(data[start:end])
        scores.append(batch_scores)

        print(f"Processed {end:,} / {len(data):,}")

    return np.concatenate(scores)


# Score validation and test datasets
validation_scores = calculate_scores(
    X_val, "Thursday validation"
)

test_scores = calculate_scores(
    X_test, "Friday test"
)

# Evaluate thresholds
summary = []
family_summary = []

print("\n" + "=" * 70)
print("THRESHOLD COMPARISON")
print("=" * 70)

for target_fpr in TARGET_FPRS:

    # Calibrate using Thursday normal traffic only
    threshold = float(
        np.quantile(validation_scores, 1 - target_fpr)
    )

    val_predictions = (
        validation_scores >= threshold
    ).astype(np.int8)

    actual_val_fpr = float(val_predictions.mean())

    # Evaluate on Friday
    predictions = (
        test_scores >= threshold
    ).astype(np.int8)

    accuracy = accuracy_score(y_test, predictions)
    precision = precision_score(
        y_test, predictions, zero_division=0
    )
    recall = recall_score(
        y_test, predictions, zero_division=0
    )
    f1 = f1_score(
        y_test, predictions, zero_division=0
    )

    tn, fp, fn, tp = confusion_matrix(
        y_test,
        predictions,
        labels=[0, 1]
    ).ravel()

    friday_fpr = fp / (fp + tn) if (fp + tn) else 0

    summary.append({
        "target_validation_fpr": target_fpr,
        "threshold": threshold,
        "actual_validation_fpr": actual_val_fpr,
        "friday_accuracy": accuracy,
        "friday_precision": precision,
        "friday_recall": recall,
        "friday_f1": f1,
        "friday_fpr": friday_fpr,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp
    })

    print(
        f"\nTarget Thursday FPR: {target_fpr * 100:.2f}%"
    )
    print(f"Threshold       : {threshold:.8f}")
    print(f"Actual Val FPR  : {actual_val_fpr * 100:.2f}%")
    print(f"Friday Precision: {precision * 100:.2f}%")
    print(f"Friday Recall   : {recall * 100:.2f}%")
    print(f"Friday F1       : {f1 * 100:.2f}%")
    print(f"Friday FPR      : {friday_fpr * 100:.2f}%")

    # Attack-family results at this threshold
    family_df = pd.DataFrame({
        "attack_type": attack_types,
        "predicted": predictions
    })

    for family, group in family_df.groupby("attack_type"):
        total = len(group)
        detected = int(group["predicted"].sum())

        family_summary.append({
            "target_validation_fpr": target_fpr,
            "threshold": threshold,
            "attack_type": family,
            "total_records": total,
            "detected": detected,
            "missed": total - detected,
            "detection_rate": detected / total if total else 0
        })


# Save results
summary_df = pd.DataFrame(summary)
family_df = pd.DataFrame(family_summary)

summary_path = RESULT_DIR / "threshold_comparison.csv"
family_path = RESULT_DIR / "attack_family_threshold_comparison.csv"

summary_df.to_csv(summary_path, index=False)
family_df.to_csv(family_path, index=False)

print("\n" + "=" * 70)
print("FINAL THRESHOLD SUMMARY")
print("=" * 70)

print(
    summary_df[
        [
            "target_validation_fpr",
            "actual_validation_fpr",
            "friday_precision",
            "friday_recall",
            "friday_f1",
            "friday_fpr"
        ]
    ].to_string(index=False)
)

print("\nResults saved:")
print(summary_path)
print(family_path)

print("\nTHRESHOLD ANALYSIS COMPLETED!")
