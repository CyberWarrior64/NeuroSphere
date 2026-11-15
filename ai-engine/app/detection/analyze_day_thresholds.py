
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "datasets" / "processed" / "day_based_training"
MODEL_FILE = BASE_DIR / "saved_models" / "random_forest_cicids2017_day_holdout.joblib"
RESULT_DIR = BASE_DIR / "datasets" / "processed" / "day_based_results"

print("=" * 70)
print("NEUROSPHERE - DETECTION THRESHOLD ANALYSIS")
print("=" * 70)

print("\nLoading model and test data...")

model = joblib.load(MODEL_FILE)

X_test = np.load(DATA_DIR / "X_test.npy")
y_test = np.load(DATA_DIR / "y_test.npy")

attack_types = np.load(
    DATA_DIR / "attack_type_test.npy",
    allow_pickle=False
)

# Predict probabilities in batches
print("\nCalculating attack probabilities...")

probabilities = []

for start in range(0, len(X_test), 100_000):
    end = min(start + 100_000, len(X_test))

    batch_prob = model.predict_proba(
        X_test[start:end]
    )[:, 1]

    probabilities.extend(batch_prob)

probabilities = np.asarray(probabilities)

thresholds = [0.50, 0.40, 0.30, 0.20, 0.10, 0.05, 0.01]

rows = []

print("\n" + "=" * 70)
print("THRESHOLD COMPARISON")
print("=" * 70)

for threshold in thresholds:

    predictions = (
        probabilities >= threshold
    ).astype(np.int8)

    tn, fp, fn, tp = confusion_matrix(
        y_test,
        predictions,
        labels=[0, 1]
    ).ravel()

    precision = precision_score(
        y_test, predictions, zero_division=0
    )

    recall = recall_score(
        y_test, predictions, zero_division=0
    )

    f1 = f1_score(
        y_test, predictions, zero_division=0
    )

    fpr = fp / (fp + tn)

    rows.append({
        "threshold": threshold,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "false_positive_rate": fpr,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn
    })

    print(
        f"\nThreshold: {threshold:.2f}"
        f"\nPrecision: {precision:.4f}"
        f"\nRecall: {recall:.4f}"
        f"\nF1 Score: {f1:.4f}"
        f"\nFalse Positive Rate: {fpr * 100:.3f}%"
        f"\nTrue Positives: {tp:,}"
        f"\nFalse Positives: {fp:,}"
        f"\nFalse Negatives: {fn:,}"
    )

# Analyze probability distribution by attack family
print("\n" + "=" * 70)
print("ATTACK PROBABILITY DISTRIBUTION")
print("=" * 70)

family_df = pd.DataFrame({
    "attack_type": attack_types,
    "actual": y_test,
    "probability": probabilities
})

for family, group in family_df.groupby("attack_type"):

    print(f"\n{family}")
    print("Records:", len(group))
    print("Mean probability:", round(group["probability"].mean(), 4))
    print("Median probability:", round(group["probability"].median(), 4))
    print("90th percentile:", round(group["probability"].quantile(0.90), 4))
    print("Maximum probability:", round(group["probability"].max(), 4))

# Save results
RESULT_DIR.mkdir(parents=True, exist_ok=True)

pd.DataFrame(rows).to_csv(
    RESULT_DIR / "threshold_comparison.csv",
    index=False
)

family_df.groupby("attack_type")["probability"].agg(
    ["count", "mean", "median", "min", "max"]
).to_csv(
    RESULT_DIR / "attack_probability_distribution.csv"
)

print("\nReports saved in:", RESULT_DIR)
print("\nThreshold analysis completed!")
