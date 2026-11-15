
from pathlib import Path
import time
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
    confusion_matrix,
    classification_report
)

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = (
    BASE_DIR / "datasets" / "processed" / "day_based_training"
)

MODEL_DIR = BASE_DIR / "saved_models"
RESULT_DIR = BASE_DIR / "datasets" / "processed" / "day_based_results"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("NEUROSPHERE - RANDOM FOREST UNSEEN-DAY EVALUATION")
print("=" * 70)

# Load prepared data
print("\nLoading day-based training data...")

X_train = np.load(DATA_DIR / "X_train.npy")
X_test = np.load(DATA_DIR / "X_test.npy")
y_train = np.load(DATA_DIR / "y_train.npy")
y_test = np.load(DATA_DIR / "y_test.npy")

attack_types = np.load(
    DATA_DIR / "attack_type_test.npy",
    allow_pickle=False
)

source_files = np.load(
    DATA_DIR / "source_file_test.npy",
    allow_pickle=False
)

print("Training shape:", X_train.shape)
print("Testing shape:", X_test.shape)

print("\nTraining class distribution:")
print(dict(zip(*np.unique(y_train, return_counts=True))))

print("\nTesting class distribution:")
print(dict(zip(*np.unique(y_test, return_counts=True))))

# Train Random Forest
print("\nInitializing Random Forest...")

model = RandomForestClassifier(
    n_estimators=100,
    max_depth=25,
    min_samples_leaf=2,
    class_weight="balanced",
    n_jobs=-1,
    random_state=42,
    verbose=1
)

print("\nTraining started...")
start_time = time.time()

model.fit(X_train, y_train)

training_time = time.time() - start_time

print(f"\nTraining completed in {training_time:.2f} seconds.")

# Evaluate on Friday
print("\nEvaluating on unseen Friday traffic...")

y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred, zero_division=0)
recall = recall_score(y_test, y_pred, zero_division=0)
f1 = f1_score(y_test, y_pred, zero_division=0)
roc_auc = roc_auc_score(y_test, y_prob)

tn, fp, fn, tp = confusion_matrix(
    y_test, y_pred, labels=[0, 1]
).ravel()

fpr = fp / (fp + tn) if (fp + tn) else 0

print("\n" + "=" * 70)
print("UNSEEN-DAY MODEL PERFORMANCE")
print("=" * 70)

print(f"Accuracy       : {accuracy:.4f} ({accuracy * 100:.2f}%)")
print(f"Precision      : {precision:.4f}")
print(f"Recall         : {recall:.4f}")
print(f"F1 Score       : {f1:.4f}")
print(f"ROC-AUC        : {roc_auc:.4f}")
print(f"False Positive : {fpr:.4f} ({fpr * 100:.2f}%)")

print("\nConfusion Matrix:")
print(f"True Negatives : {tn}")
print(f"False Positives: {fp}")
print(f"False Negatives: {fn}")
print(f"True Positives : {tp}")

print("\nClassification Report:")
print(classification_report(
    y_test,
    y_pred,
    labels=[0, 1],
    target_names=["NORMAL", "ATTACK"],
    zero_division=0
))

# Evaluate each Friday attack family separately
print("\n" + "=" * 70)
print("FRIDAY ATTACK-FAMILY DETECTION")
print("=" * 70)

results = pd.DataFrame({
    "attack_type": attack_types,
    "source_file": source_files,
    "actual": y_test,
    "predicted": y_pred,
    "attack_probability": y_prob
})

family_results = []

for family, group in results.groupby("attack_type"):

    total = len(group)
    detected = int((group["predicted"] == 1).sum())
    missed = total - detected

    detection_rate = detected / total if total else 0

    family_results.append({
        "attack_type": family,
        "total_records": total,
        "detected": detected,
        "missed": missed,
        "detection_rate": detection_rate
    })

    print(
        f"{family:15s} | "
        f"Total: {total:8,d} | "
        f"Detected: {detected:8,d} | "
        f"Missed: {missed:8,d} | "
        f"Detection: {detection_rate * 100:7.2f}%"
    )

family_df = pd.DataFrame(family_results)

family_df.to_csv(
    RESULT_DIR / "attack_family_performance.csv",
    index=False
)

# Save model separately
model_path = MODEL_DIR / "random_forest_cicids2017_day_holdout.joblib"

joblib.dump(model, model_path, compress=3)

print("\nModel saved to:", model_path)

print(
    "Attack-family report saved to:",
    RESULT_DIR / "attack_family_performance.csv"
)

print("\nTraining time:", f"{training_time:.2f} seconds")
print("\nUNSEEN-DAY EVALUATION COMPLETED!")
