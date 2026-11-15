
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

RF_DIR = BASE_DIR / "datasets" / "processed" / "day_based_training"
IF_DIR = BASE_DIR / "datasets" / "processed" / "anomaly_training"
MODEL_DIR = BASE_DIR / "saved_models"

RESULT_DIR = (
    BASE_DIR / "datasets" / "processed" / "hybrid_results_v1"
)
RESULT_DIR.mkdir(parents=True, exist_ok=True)

BATCH_SIZE = 50_000
IF_TARGET_VALIDATION_FPR = 0.03

print("=" * 70)
print("NEUROSPHERE - HYBRID DETECTION EVALUATION V1")
print("=" * 70)

# --------------------------------------------------
# 1. Load trained models
# --------------------------------------------------

rf_model_path = (
    MODEL_DIR / "random_forest_cicids2017_day_holdout.joblib"
)

if_model_path = (
    MODEL_DIR / "isolation_forest_cicids2017_v2.joblib"
)

if not rf_model_path.exists():
    raise FileNotFoundError(rf_model_path)

if not if_model_path.exists():
    raise FileNotFoundError(if_model_path)

rf_model = joblib.load(rf_model_path)
if_model = joblib.load(if_model_path)

print("\nModels loaded successfully.")

# --------------------------------------------------
# 2. Load test data and record IDs
# --------------------------------------------------

rf_ids = np.load(RF_DIR / "test_row_id.npy")
if_ids = np.load(IF_DIR / "test_row_id.npy")

rf_X = np.load(RF_DIR / "X_test.npy", mmap_mode="r")
if_X = np.load(IF_DIR / "X_test.npy", mmap_mode="r")

rf_y = np.load(RF_DIR / "y_test.npy")
if_y = np.load(IF_DIR / "y_test.npy")

rf_attack = np.load(
    RF_DIR / "attack_type_test.npy",
    allow_pickle=True
).astype(str)

if_attack = np.load(
    IF_DIR / "attack_type_test.npy",
    allow_pickle=True
).astype(str)

# --------------------------------------------------
# 3. Verify model feature compatibility
# --------------------------------------------------

if rf_X.shape[1] != rf_model.n_features_in_:
    raise ValueError("Random Forest feature count mismatch.")

if if_X.shape[1] != if_model.n_features_in_:
    raise ValueError("Isolation Forest feature count mismatch.")

# --------------------------------------------------
# 4. Align records using original row IDs
# --------------------------------------------------

common_ids, rf_idx, if_idx = np.intersect1d(
    rf_ids,
    if_ids,
    return_indices=True
)

y_true = rf_y[rf_idx]
attack_types = rf_attack[rf_idx]

if not np.array_equal(y_true, if_y[if_idx]):
    raise ValueError("Binary labels do not match.")

if not np.array_equal(attack_types, if_attack[if_idx]):
    raise ValueError("Attack-family labels do not match.")

print("\nCommon evaluation records:", len(common_ids))
print("Random Forest features:", rf_X.shape[1])
print("Isolation Forest features:", if_X.shape[1])

# --------------------------------------------------
# 5. Generate Random Forest probabilities
# --------------------------------------------------

print("\nGenerating Random Forest predictions...")

rf_class_index = list(rf_model.classes_).index(1)

rf_scores = np.empty(len(common_ids), dtype=np.float64)

for start in range(0, len(common_ids), BATCH_SIZE):
    end = min(start + BATCH_SIZE, len(common_ids))

    batch = rf_X[rf_idx[start:end]]

    rf_scores[start:end] = rf_model.predict_proba(batch)[
        :, rf_class_index
    ]

    print(f"RF processed {end:,} / {len(common_ids):,}")

RF_THRESHOLD = 0.50

rf_pred = (rf_scores >= RF_THRESHOLD).astype(np.int8)

# --------------------------------------------------
# 6. Calibrate Isolation Forest using Thursday
# --------------------------------------------------

print("\nLoading Thursday validation data...")

X_val = np.load(
    IF_DIR / "X_validation.npy",
    mmap_mode="r"
)

print("Validation records:", len(X_val))

def calculate_if_scores(data, description):

    scores = np.empty(len(data), dtype=np.float64)

    print(f"\nScoring {description}...")

    for start in range(0, len(data), BATCH_SIZE):
        end = min(start + BATCH_SIZE, len(data))

        scores[start:end] = -if_model.score_samples(
            data[start:end]
        )

        print(f"IF processed {end:,} / {len(data):,}")

    return scores


validation_scores = calculate_if_scores(
    X_val,
    "Thursday normal validation"
)

if_threshold = float(
    np.quantile(
        validation_scores,
        1 - IF_TARGET_VALIDATION_FPR
    )
)

validation_fpr = float(
    np.mean(validation_scores >= if_threshold)
)

print("\nIsolation Forest threshold:", f"{if_threshold:.8f}")
print("Thursday validation FPR:", f"{validation_fpr * 100:.4f}%")

# --------------------------------------------------
# 7. Generate aligned Isolation Forest predictions
# --------------------------------------------------

print("\nGenerating Isolation Forest predictions...")

if_scores = np.empty(len(common_ids), dtype=np.float64)

for start in range(0, len(common_ids), BATCH_SIZE):
    end = min(start + BATCH_SIZE, len(common_ids))

    batch = if_X[if_idx[start:end]]

    if_scores[start:end] = -if_model.score_samples(batch)

    print(f"IF test processed {end:,} / {len(common_ids):,}")

if_pred = (
    if_scores >= if_threshold
).astype(np.int8)

# --------------------------------------------------
# 8. Generate hybrid decisions
# --------------------------------------------------

# OR: Either detector flags an attack
hybrid_or = np.logical_or(
    rf_pred == 1,
    if_pred == 1
).astype(np.int8)

# AND: Both detectors must flag an attack
hybrid_and = np.logical_and(
    rf_pred == 1,
    if_pred == 1
).astype(np.int8)

# --------------------------------------------------
# 9. Evaluation function
# --------------------------------------------------

def evaluate_model(name, predictions, continuous_scores=None):

    accuracy = accuracy_score(y_true, predictions)

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
        y_true,
        predictions,
        labels=[0, 1]
    ).ravel()

    fpr = fp / (fp + tn) if (fp + tn) else 0

    auc = (
        roc_auc_score(y_true, continuous_scores)
        if continuous_scores is not None
        else None
    )

    result = {
        "model": name,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": auc,
        "fpr": fpr,
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp)
    }

    print("\n" + "-" * 60)
    print(name)
    print("-" * 60)

    print(f"Accuracy  : {accuracy * 100:.2f}%")
    print(f"Precision : {precision * 100:.2f}%")
    print(f"Recall    : {recall * 100:.2f}%")
    print(f"F1 Score  : {f1 * 100:.2f}%")
    print(
        f"ROC-AUC   : {auc:.4f}"
        if auc is not None else
        "ROC-AUC   : Not calculated for binary fusion"
    )
    print(f"FPR       : {fpr * 100:.2f}%")

    print("\nTN:", tn)
    print("FP:", fp)
    print("FN:", fn)
    print("TP:", tp)

    return result


# --------------------------------------------------
# 10. Compare all four configurations
# --------------------------------------------------

results = []

results.append(
    evaluate_model(
        "Random Forest",
        rf_pred,
        rf_scores
    )
)

results.append(
    evaluate_model(
        "Isolation Forest V2",
        if_pred,
        if_scores
    )
)

results.append(
    evaluate_model(
        "Hybrid OR",
        hybrid_or
    )
)

results.append(
    evaluate_model(
        "Hybrid AND",
        hybrid_and
    )
)

# --------------------------------------------------
# 11. Attack-family analysis
# --------------------------------------------------

print("\n" + "=" * 70)
print("ATTACK-FAMILY PERFORMANCE")
print("=" * 70)

prediction_sets = {
    "Random Forest": rf_pred,
    "Isolation Forest V2": if_pred,
    "Hybrid OR": hybrid_or,
    "Hybrid AND": hybrid_and
}

family_results = []

for family in np.unique(attack_types):

    mask = attack_types == family
    total = int(mask.sum())

    print(f"\n{family} ({total:,} records)")

    for model_name, predictions in prediction_sets.items():

        detected = int(predictions[mask].sum())
        rate = detected / total if total else 0

        family_results.append({
            "attack_type": family,
            "model": model_name,
            "total_records": total,
            "detected": detected,
            "missed": total - detected,
            "detection_rate": rate
        })

        print(
            f"  {model_name:22s}: "
            f"{rate * 100:7.2f}% "
            f"({detected:,}/{total:,})"
        )

# --------------------------------------------------
# 12. Save results
# --------------------------------------------------

summary_df = pd.DataFrame(results)
family_df = pd.DataFrame(family_results)

summary_df.to_csv(
    RESULT_DIR / "hybrid_model_comparison.csv",
    index=False
)

family_df.to_csv(
    RESULT_DIR / "hybrid_attack_family_results.csv",
    index=False
)

predictions_df = pd.DataFrame({
    "row_id": common_ids,
    "actual": y_true,
    "attack_type": attack_types,
    "rf_probability": rf_scores,
    "if_anomaly_score": if_scores,
    "rf_prediction": rf_pred,
    "if_prediction": if_pred,
    "hybrid_or": hybrid_or,
    "hybrid_and": hybrid_and
})

predictions_df.to_csv(
    RESULT_DIR / "hybrid_predictions.csv",
    index=False
)

print("\n" + "=" * 70)
print("HYBRID EVALUATION COMPLETED")
print("=" * 70)

print("\nResults saved to:")
print(RESULT_DIR)

print("\n", summary_df.to_string(index=False))
