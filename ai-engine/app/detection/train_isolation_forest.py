
from pathlib import Path
import time
import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    roc_auc_score
)

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "datasets" / "processed" / "anomaly_training"
MODEL_DIR = BASE_DIR / "saved_models"
RESULT_DIR = BASE_DIR / "datasets" / "processed" / "anomaly_results_v2"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_VALIDATION_FPR = 0.01
BATCH_SIZE = 100_000

print("=" * 70)
print("NEUROSPHERE - ISOLATION FOREST TRAINING")
print("=" * 70)

# Load data
print("\nLoading anomaly detection data...")

X_train = np.load(DATA_DIR / "X_train.npy")
X_val = np.load(DATA_DIR / "X_validation.npy")
X_test = np.load(DATA_DIR / "X_test.npy")
y_test = np.load(DATA_DIR / "y_test.npy")

attack_types = np.load(
    DATA_DIR / "attack_type_test.npy",
    allow_pickle=True
)

print("Training shape:", X_train.shape)
print("Validation shape:", X_val.shape)
print("Testing shape:", X_test.shape)

# Train model
print("\nInitializing Isolation Forest...")

model = IsolationForest(
    n_estimators=300,
    max_samples=4096,
    contamination="auto",
    max_features=1.0,
    bootstrap=False,
    n_jobs=-1,
    random_state=42,
    verbose=1
)

print("\nTraining started...")
start_time = time.time()

model.fit(X_train)

training_time = time.time() - start_time

print(f"\nTraining completed in {training_time:.2f} seconds.")

# Calculate anomaly scores in batches
# Higher score means more anomalous.
def calculate_anomaly_scores(data, description):

    scores = []

    print(f"\nCalculating scores: {description}")

    for start in range(0, len(data), BATCH_SIZE):
        end = min(start + BATCH_SIZE, len(data))

        batch_scores = -model.score_samples(data[start:end])

        scores.append(batch_scores)

        print(f"Processed {end:,} / {len(data):,}")

    return np.concatenate(scores)


# Calibrate using Thursday normal traffic
validation_scores = calculate_anomaly_scores(
    X_val,
    "Thursday validation"
)

threshold = float(
    np.quantile(
        validation_scores,
        1 - TARGET_VALIDATION_FPR
    )
)

validation_predictions = (
    validation_scores >= threshold
).astype(np.int8)

validation_fpr = float(validation_predictions.mean())

print("\n" + "=" * 70)
print("THRESHOLD CALIBRATION")
print("=" * 70)

print("Target validation FPR:", f"{TARGET_VALIDATION_FPR * 100:.2f}%")
print("Calibrated anomaly threshold:", f"{threshold:.8f}")
print("Actual validation FPR:", f"{validation_fpr * 100:.4f}%")

# Evaluate on Friday
test_scores = calculate_anomaly_scores(
    X_test,
    "Friday unseen traffic"
)

y_pred = (
    test_scores >= threshold
).astype(np.int8)

accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred, zero_division=0)
recall = recall_score(y_test, y_pred, zero_division=0)
f1 = f1_score(y_test, y_pred, zero_division=0)
roc_auc = roc_auc_score(y_test, test_scores)

tn, fp, fn, tp = confusion_matrix(
    y_test,
    y_pred,
    labels=[0, 1]
).ravel()

fpr = fp / (fp + tn) if (fp + tn) else 0

print("\n" + "=" * 70)
print("ISOLATION FOREST - FRIDAY EVALUATION")
print("=" * 70)

print(f"Accuracy       : {accuracy:.4f} ({accuracy * 100:.2f}%)")
print(f"Precision      : {precision:.4f}")
print(f"Recall         : {recall:.4f}")
print(f"F1 Score       : {f1:.4f}")
print(f"ROC-AUC        : {roc_auc:.4f}")
print(f"False Positive : {fpr:.4f} ({fpr * 100:.2f}%)")

print("\nConfusion Matrix:")
print("True Negatives :", tn)
print("False Positives:", fp)
print("False Negatives:", fn)
print("True Positives :", tp)

print("\nClassification Report:")
print(classification_report(
    y_test,
    y_pred,
    labels=[0, 1],
    target_names=["NORMAL", "ATTACK"],
    zero_division=0
))

# Attack-family performance
print("\n" + "=" * 70)
print("ATTACK-FAMILY ANOMALY DETECTION")
print("=" * 70)

family_df = pd.DataFrame({
    "attack_type": attack_types,
    "actual": y_test,
    "predicted": y_pred,
    "anomaly_score": test_scores
})

family_results = []

for family, group in family_df.groupby("attack_type"):

    total = len(group)
    detected = int(group["predicted"].sum())
    missed = total - detected

    detection_rate = detected / total if total else 0

    family_results.append({
        "attack_type": family,
        "total_records": total,
        "detected": detected,
        "missed": missed,
        "detection_rate": detection_rate,
        "mean_anomaly_score": group["anomaly_score"].mean()
    })

    print(
        f"{family:15s} | "
        f"Total: {total:8,d} | "
        f"Detected: {detected:8,d} | "
        f"Missed: {missed:8,d} | "
        f"Detection: {detection_rate * 100:7.2f}%"
    )

# Save model and calibration metadata
model_path = MODEL_DIR / "isolation_forest_cicids2017_v2.joblib"

joblib.dump(model, model_path, compress=3)

joblib.dump({
    "threshold": threshold,
    "target_validation_fpr": TARGET_VALIDATION_FPR,
    "actual_validation_fpr": validation_fpr,
    "feature_count": X_train.shape[1]
}, MODEL_DIR / "isolation_forest_calibration.joblib")

pd.DataFrame(family_results).to_csv(
    RESULT_DIR / "attack_family_performance.csv",
    index=False
)

pd.DataFrame({
    "actual": y_test,
    "predicted": y_pred,
    "anomaly_score": test_scores,
    "attack_type": attack_types
}).to_csv(
    RESULT_DIR / "friday_predictions.csv",
    index=False
)

print("\nModel saved:", model_path)
print("\nResults saved:", RESULT_DIR)

print("\nTraining time:", f"{training_time:.2f} seconds")
print("\nISOLATION FOREST TRAINING COMPLETED!")

