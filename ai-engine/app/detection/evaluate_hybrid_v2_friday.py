
import json
import joblib
import numpy as np
import pandas as pd

from pathlib import Path
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix
)

# ============================================================
# NEUROSPHERE - HYBRID V2 FRIDAY INDEPENDENT EVALUATION
# ============================================================

BASE = Path(__file__).resolve().parents[2]

DATA_DIR = BASE / "datasets" / "processed"
HYBRID_DIR = DATA_DIR / "hybrid_v2_training"
RESULT_DIR = DATA_DIR / "hybrid_v2_results"

MODEL_DIR = BASE / "saved_models"

RESULT_DIR.mkdir(parents=True, exist_ok=True)

# Frozen thresholds selected using Thursday validation only
RF_THRESHOLD = 0.27
IF_THRESHOLD = 0.5210675410782588

BATCH_SIZE = 50000

print("=" * 75)
print("NEUROSPHERE - HYBRID V2 FRIDAY INDEPENDENT EVALUATION")
print("=" * 75)

# ============================================================
# 1. LOAD FRIDAY TEST DATA
# ============================================================

print("\n[1] Loading Friday test data...")

X_test = np.load(HYBRID_DIR / "X_test.npy")
y_test = np.load(HYBRID_DIR / "y_test.npy")
test_ids = np.load(HYBRID_DIR / "test_row_id.npy")

attack_types = np.load(
    HYBRID_DIR / "attack_type_test.npy",
    allow_pickle=True
)

print("Test matrix:", X_test.shape)
print("Test labels:", y_test.shape)
print("Test IDs:", test_ids.shape)

if not (
    len(X_test) == len(y_test) == len(test_ids) == len(attack_types)
):
    raise ValueError("Friday test arrays have different lengths.")

if len(np.unique(test_ids)) != len(test_ids):
    raise ValueError("Duplicate row IDs found in Friday test data.")

# ============================================================
# 2. LOAD MODELS AND PREPROCESSORS
# ============================================================

print("\n[2] Loading trained models...")

rf_model = joblib.load(
    MODEL_DIR / "random_forest_cicids2017_hybrid_v2.joblib"
)

rf_preprocessor = joblib.load(
    HYBRID_DIR / "preprocessor.joblib"
)

if_model = joblib.load(
    MODEL_DIR / "isolation_forest_cicids2017_v2.joblib"
)

if_imputer = joblib.load(
    DATA_DIR / "anomaly_training" / "imputer.joblib"
)

if_features = joblib.load(
    DATA_DIR / "anomaly_training" / "feature_columns.joblib"
)

rf_features = joblib.load(
    HYBRID_DIR / "feature_columns.joblib"
)

if list(rf_features) != list(if_features):
    raise ValueError("RF and IF feature orders do not match.")

if X_test.shape[1] != len(rf_features):
    raise ValueError("Friday test feature count does not match models.")

print("Random Forest loaded.")
print("Isolation Forest loaded.")
print("Feature count:", len(rf_features))
print("Feature order verified.")

# ============================================================
# 3. RANDOM FOREST PREDICTIONS
# ============================================================

print("\n[3] Running Random Forest predictions...")

rf_probabilities = rf_model.predict_proba(X_test)[:, 1]

rf_predictions = (
    rf_probabilities >= RF_THRESHOLD
).astype(int)

print("Random Forest predictions completed.")

# ============================================================
# 4. RECONSTRUCT RAW FRIDAY FEATURES FOR ISOLATION FOREST
# ============================================================

print("\n[4] Preparing raw features for Isolation Forest...")

parquet_path = DATA_DIR / "cic_ids2017_with_day.parquet"

df = pd.read_parquet(parquet_path)

df["_row_id"] = np.arange(len(df))

friday_raw = (
    df.set_index("_row_id")
      .reindex(test_ids)
)

if friday_raw.index.isna().any():
    raise ValueError("Could not align all Friday row IDs.")

if friday_raw[rf_features].isna().all(axis=1).any():
    raise ValueError("Some Friday rows have no feature values.")

raw_matrix = friday_raw[if_features].copy()

for column in if_features:
    raw_matrix[column] = pd.to_numeric(
        raw_matrix[column],
        errors="coerce"
    )

raw_matrix = raw_matrix.replace(
    [np.inf, -np.inf],
    np.nan
)

# Isolation Forest uses its own imputer.
# Do not use the Random Forest scaled matrix here.
X_if = if_imputer.transform(raw_matrix)

print("Raw Friday matrix:", raw_matrix.shape)
print("Isolation Forest matrix:", X_if.shape)

# ============================================================
# 5. ISOLATION FOREST ANOMALY SCORES
# ============================================================

print("\n[5] Running Isolation Forest predictions...")

if_scores = np.empty(len(X_if), dtype=np.float64)

for start in range(0, len(X_if), BATCH_SIZE):
    end = min(start + BATCH_SIZE, len(X_if))

    if_scores[start:end] = -if_model.score_samples(
        X_if[start:end]
    )

if_predictions = (
    if_scores >= IF_THRESHOLD
).astype(int)

print("Isolation Forest predictions completed.")

# ============================================================
# 6. HYBRID DECISIONS
# ============================================================

print("\n[6] Creating hybrid predictions...")

or_predictions = (
    (rf_predictions == 1) |
    (if_predictions == 1)
).astype(int)

and_predictions = (
    (rf_predictions == 1) &
    (if_predictions == 1)
).astype(int)

# ============================================================
# 7. PERFORMANCE METRICS
# ============================================================

def calculate_metrics(name, predictions, score=None):

    tn, fp, fn, tp = confusion_matrix(
        y_test,
        predictions,
        labels=[0, 1]
    ).ravel()

    metrics = {
        "Detector": name,
        "Accuracy": accuracy_score(y_test, predictions),
        "Precision": precision_score(
            y_test, predictions, zero_division=0
        ),
        "Recall": recall_score(
            y_test, predictions, zero_division=0
        ),
        "F1": f1_score(
            y_test, predictions, zero_division=0
        ),
        "FPR": fp / (fp + tn) if (fp + tn) else 0,
        "ROC_AUC": (
            roc_auc_score(y_test, score)
            if score is not None
            else np.nan
        ),
        "TN": int(tn),
        "FP": int(fp),
        "FN": int(fn),
        "TP": int(tp)
    }

    return metrics


print("\n" + "=" * 75)
print("FRIDAY INDEPENDENT TEST PERFORMANCE")
print("=" * 75)

results = []

results.append(
    calculate_metrics(
        "Random Forest V2",
        rf_predictions,
        rf_probabilities
    )
)

results.append(
    calculate_metrics(
        "Isolation Forest V2",
        if_predictions,
        if_scores
    )
)

results.append(
    calculate_metrics(
        "Hybrid OR",
        or_predictions
    )
)

results.append(
    calculate_metrics(
        "Hybrid AND",
        and_predictions
    )
)

metrics_df = pd.DataFrame(results)

for _, row in metrics_df.iterrows():

    print(f"\n{row['Detector']}")
    print("-" * 55)

    for metric in [
        "Accuracy",
        "Precision",
        "Recall",
        "F1",
        "FPR",
        "ROC_AUC"
    ]:
        value = row[metric]

        if pd.notna(value):
            if metric == "FPR":
                print(f"{metric:12}: {value * 100:.4f}%")
            else:
                print(f"{metric:12}: {value:.4f}")
        else:
            print(f"{metric:12}: Not calculated")

    print(
        f"TN: {row['TN']} | FP: {row['FP']} | "
        f"FN: {row['FN']} | TP: {row['TP']}"
    )

metrics_df.to_csv(
    RESULT_DIR / "hybrid_v2_friday_metrics.csv",
    index=False
)

# ============================================================
# 8. DETECTOR AGREEMENT ANALYSIS
# ============================================================

print("\n" + "=" * 75)
print("FRIDAY DETECTOR AGREEMENT ANALYSIS")
print("=" * 75)

both = (rf_predictions == 1) & (if_predictions == 1)
rf_only = (rf_predictions == 1) & (if_predictions == 0)
if_only = (rf_predictions == 0) & (if_predictions == 1)
neither = (rf_predictions == 0) & (if_predictions == 0)

agreement_masks = {
    "BOTH_FLAGGED": both,
    "RF_ONLY": rf_only,
    "IF_ONLY": if_only,
    "NEITHER_FLAGGED": neither
}

agreement_results = []

for name, mask in agreement_masks.items():

    total = int(mask.sum())
    attacks = int(y_test[mask].sum())
    benign = total - attacks

    attack_rate = attacks / total if total else 0

    agreement_results.append({
        "Category": name,
        "Total": total,
        "Attacks": attacks,
        "Benign": benign,
        "Attack_Rate": attack_rate
    })

    print(
        f"{name:20} | Total: {total:9} | "
        f"Attacks: {attacks:8} | Benign: {benign:8} | "
        f"Attack rate: {attack_rate * 100:7.2f}%"
    )

pd.DataFrame(agreement_results).to_csv(
    RESULT_DIR / "hybrid_v2_friday_agreement.csv",
    index=False
)

# ============================================================
# 9. ATTACK FAMILY PERFORMANCE
# ============================================================

print("\n" + "=" * 75)
print("FRIDAY ATTACK-FAMILY COMPARISON")
print("=" * 75)

family_results = []

for family in sorted(np.unique(attack_types)):

    mask = attack_types == family
    actual_count = int(y_test[mask].sum())

    if actual_count == 0:
        continue

    rf_detected = int(rf_predictions[mask].sum())
    if_detected = int(if_predictions[mask].sum())
    or_detected = int(or_predictions[mask].sum())
    and_detected = int(and_predictions[mask].sum())

    family_results.append({
        "Attack_Family": str(family),
        "Total_Attacks": actual_count,
        "RF_Detected": rf_detected,
        "IF_Detected": if_detected,
        "OR_Detected": or_detected,
        "AND_Detected": and_detected,
        "RF_Recall": rf_detected / actual_count,
        "IF_Recall": if_detected / actual_count,
        "OR_Recall": or_detected / actual_count,
        "AND_Recall": and_detected / actual_count
    })

    print(
        f"{str(family):30} | "
        f"RF: {rf_detected:8} | "
        f"IF: {if_detected:8} | "
        f"OR: {or_detected:8} | "
        f"Total: {actual_count:8}"
    )

pd.DataFrame(family_results).to_csv(
    RESULT_DIR / "hybrid_v2_friday_family_comparison.csv",
    index=False
)

# ============================================================
# 10. SAVE PREDICTIONS AND METADATA
# ============================================================

np.save(
    RESULT_DIR / "friday_rf_probabilities.npy",
    rf_probabilities
)

np.save(
    RESULT_DIR / "friday_if_anomaly_scores.npy",
    if_scores
)

np.save(
    RESULT_DIR / "friday_rf_predictions.npy",
    rf_predictions
)

np.save(
    RESULT_DIR / "friday_if_predictions.npy",
    if_predictions
)

np.save(
    RESULT_DIR / "friday_hybrid_or_predictions.npy",
    or_predictions
)

np.save(
    RESULT_DIR / "friday_hybrid_and_predictions.npy",
    and_predictions
)

metadata = {
    "evaluation": "Friday independent test",
    "rf_threshold": RF_THRESHOLD,
    "if_threshold": IF_THRESHOLD,
    "test_records": int(len(y_test)),
    "feature_count": int(len(rf_features)),
    "thresholds_frozen_before_friday": True,
    "test_data_used_for_threshold_tuning": False
}

with open(
    RESULT_DIR / "hybrid_v2_friday_metadata.json",
    "w"
) as file:
    json.dump(metadata, file, indent=4)

print("\n" + "=" * 75)
print("FRIDAY INDEPENDENT EVALUATION COMPLETED")
print("=" * 75)

print("\nReports saved in:")
print(RESULT_DIR)

print("\nIMPORTANT:")
print("Do not tune thresholds using these Friday results.")
print("These results are reserved for final independent evaluation.")
