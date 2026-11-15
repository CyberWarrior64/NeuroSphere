from pathlib import Path
import time
import json
import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    classification_report
)

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "datasets" / "processed" / "hybrid_v2_training"
MODEL_DIR = BASE_DIR / "saved_models"
RESULT_DIR = BASE_DIR / "datasets" / "processed" / "hybrid_v2_results"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 75)
print("NEUROSPHERE - RANDOM FOREST V2")
print("=" * 75)

# Load training and Thursday validation data
print("\nLoading datasets...")

X_train = np.load(DATA_DIR / "X_train.npy")
y_train = np.load(DATA_DIR / "y_train.npy")

X_validation = np.load(DATA_DIR / "X_validation.npy")
y_validation = np.load(DATA_DIR / "y_validation.npy")

row_ids = np.load(DATA_DIR / "validation_row_id.npy")
attack_types = np.load(
    DATA_DIR / "attack_type_validation.npy",
    allow_pickle=False
)

source_files = np.load(
    DATA_DIR / "source_file_validation.npy",
    allow_pickle=False
)

assert X_train.shape[1] == X_validation.shape[1]
assert len(X_validation) == len(y_validation) == len(row_ids)
assert len(attack_types) == len(y_validation)
assert len(source_files) == len(y_validation)

print("Training:", X_train.shape)
print("Thursday validation:", X_validation.shape)

print("Training classes:", dict(zip(*np.unique(y_train, return_counts=True))))
print("Validation classes:", dict(zip(*np.unique(y_validation, return_counts=True))))

# Initialize Random Forest
print("\nInitializing Random Forest V2...")

model = RandomForestClassifier(
    n_estimators=100,
    max_depth=25,
    min_samples_leaf=2,
    class_weight="balanced",
    n_jobs=-1,
    random_state=42,
    verbose=1
)

# Train
print("\nTraining started...")
start = time.time()

model.fit(X_train, y_train)

training_time = time.time() - start

print(f"\nTraining completed in {training_time:.2f} seconds.")

# Thursday validation
print("\nEvaluating on Thursday validation data...")

probabilities = model.predict_proba(X_validation)[:, 1]

# Initial reference threshold, not yet final
threshold = 0.50
predictions = (probabilities >= threshold).astype(np.int8)

accuracy = accuracy_score(y_validation, predictions)
precision = precision_score(y_validation, predictions, zero_division=0)
recall = recall_score(y_validation, predictions, zero_division=0)
f1 = f1_score(y_validation, predictions, zero_division=0)
roc_auc = roc_auc_score(y_validation, probabilities)
pr_auc = average_precision_score(y_validation, probabilities)

tn, fp, fn, tp = confusion_matrix(
    y_validation, predictions, labels=[0, 1]
).ravel()

fpr = fp / (fp + tn) if (fp + tn) else 0

print("\n" + "=" * 75)
print("THURSDAY VALIDATION PERFORMANCE - THRESHOLD 0.50")
print("=" * 75)

print(f"Accuracy       : {accuracy:.4f} ({accuracy * 100:.2f}%)")
print(f"Precision      : {precision:.4f}")
print(f"Recall         : {recall:.4f}")
print(f"F1 Score       : {f1:.4f}")
print(f"ROC-AUC        : {roc_auc:.4f}")
print(f"PR-AUC         : {pr_auc:.4f}")
print(f"False Positive : {fpr:.4f} ({fpr * 100:.4f}%)")

print("\nConfusion Matrix:")
print("True Negatives :", tn)
print("False Positives:", fp)
print("False Negatives:", fn)
print("True Positives :", tp)

print("\nClassification Report:")
print(classification_report(
    y_validation,
    predictions,
    labels=[0, 1],
    target_names=["NORMAL", "ATTACK"],
    zero_division=0
))

# Threshold analysis using Thursday only
print("\n" + "=" * 75)
print("THURSDAY THRESHOLD ANALYSIS")
print("=" * 75)

threshold_results = []

for current_threshold in [0.50, 0.40, 0.30, 0.20, 0.10, 0.05, 0.01]:

    current_predictions = (
        probabilities >= current_threshold
    ).astype(np.int8)

    current_precision = precision_score(
        y_validation, current_predictions, zero_division=0
    )

    current_recall = recall_score(
        y_validation, current_predictions, zero_division=0
    )

    current_f1 = f1_score(
        y_validation, current_predictions, zero_division=0
    )

    current_tn, current_fp, current_fn, current_tp = confusion_matrix(
        y_validation,
        current_predictions,
        labels=[0, 1]
    ).ravel()

    current_fpr = (
        current_fp / (current_fp + current_tn)
        if (current_fp + current_tn) else 0
    )

    threshold_results.append({
        "threshold": current_threshold,
        "precision": current_precision,
        "recall": current_recall,
        "f1": current_f1,
        "false_positive_rate": current_fpr,
        "tn": int(current_tn),
        "fp": int(current_fp),
        "fn": int(current_fn),
        "tp": int(current_tp)
    })

    print(
        f"Threshold {current_threshold:.2f} | "
        f"Precision {current_precision:.4f} | "
        f"Recall {current_recall:.4f} | "
        f"F1 {current_f1:.4f} | "
        f"FPR {current_fpr * 100:.4f}%"
    )

pd.DataFrame(threshold_results).to_csv(
    RESULT_DIR / "thursday_threshold_analysis.csv",
    index=False
)

# Attack-family analysis at reference threshold 0.50
print("\n" + "=" * 75)
print("THURSDAY ATTACK-FAMILY PERFORMANCE")
print("=" * 75)

family_df = pd.DataFrame({
    "attack_type": attack_types,
    "source_file": source_files,
    "actual": y_validation,
    "predicted": predictions,
    "attack_probability": probabilities
})

family_results = []

for family, group in family_df.groupby("attack_type"):

    total = len(group)
    detected = int((group["predicted"] == 1).sum())

    result = {
        "attack_type": family,
        "total_records": total,
        "detected": detected,
        "missed": total - detected,
        "detection_rate": detected / total if total else 0
    }

    family_results.append(result)

    print(
        f"{family:30s} | "
        f"Total: {total:8,d} | "
        f"Detected: {detected:8,d} | "
        f"Detection: {result['detection_rate'] * 100:7.2f}%"
    )

pd.DataFrame(family_results).to_csv(
    RESULT_DIR / "thursday_attack_family_performance.csv",
    index=False
)

# Save Thursday validation probabilities
np.save(
    RESULT_DIR / "rf_v2_validation_probabilities.npy",
    probabilities
)

np.save(
    RESULT_DIR / "rf_v2_validation_predictions_050.npy",
    predictions
)

family_df.assign(
    row_id=row_ids
).to_csv(
    RESULT_DIR / "rf_v2_thursday_validation_predictions.csv",
    index=False
)

# Save model separately
model_path = MODEL_DIR / "random_forest_cicids2017_hybrid_v2.joblib"

joblib.dump(model, model_path, compress=3)

# Save summary
summary = {
    "model": "Random Forest V2",
    "validation_day": "Thursday",
    "reference_threshold": threshold,
    "training_records": int(len(X_train)),
    "validation_records": int(len(X_validation)),
    "features": int(X_train.shape[1]),
    "training_time_seconds": round(training_time, 2),
    "accuracy": float(accuracy),
    "precision": float(precision),
    "recall": float(recall),
    "f1": float(f1),
    "roc_auc": float(roc_auc),
    "pr_auc": float(pr_auc),
    "tn": int(tn),
    "fp": int(fp),
    "fn": int(fn),
    "tp": int(tp),
    "false_positive_rate": float(fpr)
}

with open(RESULT_DIR / "rf_v2_validation_summary.json", "w") as file:
    json.dump(summary, file, indent=4)

print("\nModel saved:", model_path)
print("Results saved:", RESULT_DIR)

print("\nRANDOM FOREST V2 TRAINING COMPLETED!")
print("Friday testing data was NOT used.")
