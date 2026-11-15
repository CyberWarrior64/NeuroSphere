from pathlib import Path
import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix
)

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "datasets" / "processed" / "hybrid_v2_training"
RESULT_DIR = BASE_DIR / "datasets" / "processed" / "hybrid_v2_results"

RF_THRESHOLD = 0.27
IF_THRESHOLD = 0.5210675410782588

print("=" * 75)
print("NEUROSPHERE - HYBRID V2 THURSDAY DETECTOR COMPARISON")
print("=" * 75)

# Load labels and aligned row IDs
y = np.load(DATA_DIR / "y_validation.npy")
row_ids = np.load(DATA_DIR / "validation_row_id.npy")

rf_ids = row_ids

if_ids = np.load(
    RESULT_DIR / "if_v2_validation_row_id.npy"
)

# Load detector scores
rf_scores = np.load(
    RESULT_DIR / "rf_v2_validation_probabilities.npy"
)

if_scores = np.load(
    RESULT_DIR / "if_v2_validation_scores.npy"
)

attack_types = np.load(
    DATA_DIR / "attack_type_validation.npy",
    allow_pickle=False
)

# Verify alignment
if not np.array_equal(rf_ids, if_ids):
    raise ValueError("Random Forest and Isolation Forest row IDs do not match.")

if not (
    len(y) == len(rf_scores) == len(if_scores)
    == len(attack_types)
):
    raise ValueError("Array lengths do not match.")

print("\nAligned validation records:", f"{len(y):,}")
print("Random Forest threshold:", RF_THRESHOLD)
print("Isolation Forest threshold:", IF_THRESHOLD)

# Generate predictions
rf_pred = (rf_scores >= RF_THRESHOLD).astype(np.int8)
if_pred = (if_scores >= IF_THRESHOLD).astype(np.int8)

or_pred = ((rf_pred == 1) | (if_pred == 1)).astype(np.int8)
and_pred = ((rf_pred == 1) & (if_pred == 1)).astype(np.int8)

# Evaluation helper
def evaluate(name, predictions, scores=None):

    tn, fp, fn, tp = confusion_matrix(
        y, predictions, labels=[0, 1]
    ).ravel()

    precision = precision_score(
        y, predictions, zero_division=0
    )

    recall = recall_score(
        y, predictions, zero_division=0
    )

    f1 = f1_score(
        y, predictions, zero_division=0
    )

    fpr = fp / (fp + tn) if (fp + tn) else 0

    accuracy = accuracy_score(y, predictions)

    auc = (
        roc_auc_score(y, scores)
        if scores is not None else None
    )

    print(f"\n{name}")
    print("-" * 55)
    print(f"Accuracy : {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall   : {recall:.4f}")
    print(f"F1       : {f1:.4f}")
    print(f"FPR      : {fpr * 100:.4f}%")

    if auc is not None:
        print(f"ROC-AUC  : {auc:.4f}")

    print("TN:", tn, "| FP:", fp, "| FN:", fn, "| TP:", tp)

    return {
        "model": name,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fpr": fpr,
        "roc_auc": auc,
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp)
    }


print("\n" + "=" * 75)
print("DETECTOR PERFORMANCE")
print("=" * 75)

results = []

results.append(evaluate("Random Forest V2", rf_pred, rf_scores))
results.append(evaluate("Isolation Forest V2", if_pred, if_scores))
results.append(evaluate("Hybrid OR", or_pred))
results.append(evaluate("Hybrid AND", and_pred))

pd.DataFrame(results).to_csv(
    RESULT_DIR / "hybrid_v2_thursday_metrics.csv",
    index=False
)

# Agreement categories
print("\n" + "=" * 75)
print("DETECTOR AGREEMENT ANALYSIS")
print("=" * 75)

conditions = [
    (rf_pred == 1) & (if_pred == 1),
    (rf_pred == 1) & (if_pred == 0),
    (rf_pred == 0) & (if_pred == 1),
    (rf_pred == 0) & (if_pred == 0)
]

categories = [
    "BOTH_FLAGGED",
    "RF_ONLY",
    "IF_ONLY",
    "NEITHER_FLAGGED"
]

category_array = np.select(
    conditions,
    categories,
    default="UNKNOWN"
)

agreement = pd.DataFrame({
    "row_id": row_ids,
    "attack_type": attack_types,
    "actual": y,
    "rf_probability": rf_scores,
    "if_anomaly_score": if_scores,
    "rf_prediction": rf_pred,
    "if_prediction": if_pred,
    "agreement_category": category_array
})

agreement_results = []

for category in categories:

    group = agreement[
        agreement["agreement_category"] == category
    ]

    total = len(group)
    attacks = int(group["actual"].sum())
    benign = total - attacks

    attack_rate = attacks / total if total else 0

    agreement_results.append({
        "category": category,
        "total_records": total,
        "actual_attacks": attacks,
        "actual_benign": benign,
        "attack_rate": attack_rate
    })

    print(
        f"{category:20s} | "
        f"Total: {total:8,d} | "
        f"Attacks: {attacks:7,d} | "
        f"Benign: {benign:8,d} | "
        f"Attack rate: {attack_rate * 100:7.2f}%"
    )

pd.DataFrame(agreement_results).to_csv(
    RESULT_DIR / "hybrid_v2_detector_agreement.csv",
    index=False
)

# Attack-family comparison
print("\n" + "=" * 75)
print("ATTACK-FAMILY COMPARISON")
print("=" * 75)

family_results = []

for family, group in agreement.groupby("attack_type"):

    total = len(group)
    actual_attacks = int(group["actual"].sum())

    rf_detected = int(group["rf_prediction"].sum())
    if_detected = int(group["if_prediction"].sum())
    or_detected = int(
        ((group["rf_prediction"] == 1) |
         (group["if_prediction"] == 1)).sum()
    )

    family_results.append({
        "attack_type": family,
        "total_records": total,
        "actual_attacks": actual_attacks,
        "rf_detected": rf_detected,
        "if_detected": if_detected,
        "or_detected": or_detected
    })

    if actual_attacks:
        print(
            f"{family:30s} | "
            f"RF: {rf_detected:6,d} | "
            f"IF: {if_detected:6,d} | "
            f"OR: {or_detected:6,d} | "
            f"Total: {total:6,d}"
        )

pd.DataFrame(family_results).to_csv(
    RESULT_DIR / "hybrid_v2_thursday_family_comparison.csv",
    index=False
)

agreement.to_csv(
    RESULT_DIR / "hybrid_v2_thursday_agreement_records.csv",
    index=False
)

print("\nSaved all comparison reports to:")
print(RESULT_DIR)

print("\nHYBRID V2 THURSDAY COMPARISON COMPLETED!")
