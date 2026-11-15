from pathlib import Path
import json
import time
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

DATA_FILE = BASE_DIR / "datasets" / "processed" / "cic_ids2017_with_day.parquet"

HYBRID_DIR = BASE_DIR / "datasets" / "processed" / "hybrid_v2_training"
ANOMALY_DIR = BASE_DIR / "datasets" / "processed" / "anomaly_training"
RESULT_DIR = BASE_DIR / "datasets" / "processed" / "hybrid_v2_results"

MODEL_DIR = BASE_DIR / "saved_models"

RESULT_DIR.mkdir(parents=True, exist_ok=True)

BATCH_SIZE = 100_000
TARGET_VALIDATION_FPR = 0.01

print("=" * 75)
print("NEUROSPHERE - ISOLATION FOREST V2 VALIDATION ALIGNMENT")
print("=" * 75)

# --------------------------------------------------
# 1. Load model and preprocessing artifacts
# --------------------------------------------------

print("\nLoading Isolation Forest V2...")

model = joblib.load(
    MODEL_DIR / "isolation_forest_cicids2017_v2.joblib"
)

imputer = joblib.load(
    ANOMALY_DIR / "imputer.joblib"
)

if_features = joblib.load(
    ANOMALY_DIR / "feature_columns.joblib"
)

rf_features = joblib.load(
    HYBRID_DIR / "feature_columns.joblib"
)

if model.n_features_in_ != len(if_features):
    raise ValueError("Isolation Forest feature count mismatch.")

if rf_features != if_features:
    raise ValueError("Random Forest and Isolation Forest feature order differs.")

print("Model features:", model.n_features_in_)
print("Feature order verified.")

# --------------------------------------------------
# 2. Load exact Random Forest Thursday validation IDs
# --------------------------------------------------

print("\nLoading Random Forest V2 validation records...")

validation_ids = np.load(
    HYBRID_DIR / "validation_row_id.npy"
)

y_validation = np.load(
    HYBRID_DIR / "y_validation.npy"
)

attack_types = np.load(
    HYBRID_DIR / "attack_type_validation.npy",
    allow_pickle=False
)

if not (
    len(validation_ids)
    == len(y_validation)
    == len(attack_types)
):
    raise ValueError("Validation array lengths do not match.")

if len(np.unique(validation_ids)) != len(validation_ids):
    raise ValueError("Duplicate validation row IDs found.")

print("Validation records:", f"{len(validation_ids):,}")
print("Validation classes:", dict(zip(
    *np.unique(y_validation, return_counts=True)
)))

# --------------------------------------------------
# 3. Retrieve original raw records by stable row ID
# --------------------------------------------------

print("\nLoading original CIC-IDS2017 records...")

df = pd.read_parquet(DATA_FILE)

df["_row_id"] = np.arange(len(df), dtype=np.int64)

raw_validation = (
    df.set_index("_row_id")
      .reindex(validation_ids)
)

if raw_validation.index.has_duplicates:
    raise ValueError("Duplicate original row IDs found.")

if raw_validation[if_features].isna().all(axis=1).any():
    raise ValueError("Some validation records could not be retrieved.")

if raw_validation[if_features].shape[1] != model.n_features_in_:
    raise ValueError("Raw validation feature count mismatch.")

X_raw = raw_validation[if_features].copy()

del df, raw_validation

X_raw = X_raw.replace([np.inf, -np.inf], np.nan)

print("Raw feature matrix:", X_raw.shape)

# --------------------------------------------------
# 4. Apply Isolation Forest's original imputer
# --------------------------------------------------

print("\nApplying Isolation Forest median imputer...")

X_processed = imputer.transform(X_raw)

if X_processed.shape[1] != model.n_features_in_:
    raise ValueError("Processed feature count mismatch.")

X_processed = np.asarray(X_processed, dtype=np.float32)

del X_raw

# --------------------------------------------------
# 5. Calculate anomaly scores in batches
# --------------------------------------------------

print("\nCalculating Thursday anomaly scores...")

scores = []

start_time = time.time()

for start in range(0, len(X_processed), BATCH_SIZE):

    end = min(start + BATCH_SIZE, len(X_processed))

    batch_scores = -model.score_samples(
        X_processed[start:end]
    )

    scores.append(batch_scores)

    print(f"Processed {end:,} / {len(X_processed):,}")

scores = np.concatenate(scores)

del X_processed

print("Scoring time:", f"{time.time() - start_time:.2f} seconds")

# --------------------------------------------------
# 6. Calibrate threshold using Thursday normal traffic
# --------------------------------------------------

print("\nCalibrating on Thursday normal records only...")

normal_mask = y_validation == 0

normal_scores = scores[normal_mask]

if len(normal_scores) == 0:
    raise ValueError("No normal validation records available.")

threshold = float(
    np.quantile(
        normal_scores,
        1 - TARGET_VALIDATION_FPR
    )
)

predictions = (scores >= threshold).astype(np.int8)

# --------------------------------------------------
# 7. Evaluate Thursday validation
# --------------------------------------------------

tn, fp, fn, tp = confusion_matrix(
    y_validation,
    predictions,
    labels=[0, 1]
).ravel()

accuracy = accuracy_score(y_validation, predictions)
precision = precision_score(
    y_validation, predictions, zero_division=0
)
recall = recall_score(
    y_validation, predictions, zero_division=0
)
f1 = f1_score(
    y_validation, predictions, zero_division=0
)
roc_auc = roc_auc_score(y_validation, scores)

fpr = fp / (fp + tn) if (fp + tn) else 0

print("\n" + "=" * 75)
print("ISOLATION FOREST V2 - THURSDAY VALIDATION")
print("=" * 75)

print("Threshold:", f"{threshold:.8f}")
print("Target benign FPR:", f"{TARGET_VALIDATION_FPR * 100:.2f}%")
print("Actual benign FPR:", f"{fpr * 100:.4f}%")

print(f"\nAccuracy : {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall   : {recall:.4f}")
print(f"F1       : {f1:.4f}")
print(f"ROC-AUC  : {roc_auc:.4f}")

print("\nConfusion Matrix:")
print("TN:", tn)
print("FP:", fp)
print("FN:", fn)
print("TP:", tp)

# --------------------------------------------------
# 8. Attack-family analysis
# --------------------------------------------------

family_df = pd.DataFrame({
    "attack_type": attack_types,
    "actual": y_validation,
    "predicted": predictions,
    "anomaly_score": scores
})

family_results = []

print("\nThursday attack-family detection:")

for family, group in family_df.groupby("attack_type"):

    total = len(group)
    detected = int(group["predicted"].sum())

    rate = detected / total if total else 0

    family_results.append({
        "attack_type": family,
        "total_records": total,
        "detected": detected,
        "missed": total - detected,
        "detection_rate": rate
    })

    print(
        f"{family:30s} | "
        f"Total: {total:7,d} | "
        f"Detected: {detected:7,d} | "
        f"Detection: {rate * 100:7.2f}%"
    )

# --------------------------------------------------
# 9. Save aligned scores and calibration
# --------------------------------------------------

print("\nSaving aligned validation results...")

np.save(
    RESULT_DIR / "if_v2_validation_scores.npy",
    scores
)

np.save(
    RESULT_DIR / "if_v2_validation_predictions.npy",
    predictions
)

np.save(
    RESULT_DIR / "if_v2_validation_row_id.npy",
    validation_ids
)

pd.DataFrame(family_results).to_csv(
    RESULT_DIR / "if_v2_thursday_family_results.csv",
    index=False
)

family_df.assign(
    row_id=validation_ids
).to_csv(
    RESULT_DIR / "if_v2_thursday_validation_predictions.csv",
    index=False
)

calibration = {
    "model": "Isolation Forest V2",
    "validation_day": "Thursday",
    "target_benign_fpr": TARGET_VALIDATION_FPR,
    "threshold": threshold,
    "actual_benign_fpr": float(fpr),
    "validation_records": int(len(scores)),
    "normal_validation_records": int(normal_mask.sum()),
    "feature_count": int(model.n_features_in_),
    "row_id_aligned_with_random_forest_v2": True
}

with open(
    RESULT_DIR / "if_v2_validation_calibration.json",
    "w"
) as file:
    json.dump(calibration, file, indent=4)

print("\nResults directory:", RESULT_DIR)
print("\nISOLATION FOREST V2 ALIGNMENT COMPLETED!")
