
import joblib
import numpy as np
import pandas as pd
import requests

from pathlib import Path

# ============================================================
# NEUROSPHERE V2 - API AND OFFLINE PREDICTION VERIFICATION
# ============================================================

BASE = Path(__file__).resolve().parents[2]

DATA_DIR = BASE / "datasets" / "processed"
HYBRID_DIR = DATA_DIR / "hybrid_v2_training"
RESULT_DIR = DATA_DIR / "hybrid_v2_results"

API_URL = "http://127.0.0.1:8000/api/v1/detect/v2"

print("=" * 75)
print("NEUROSPHERE V2 - API VERIFICATION")
print("=" * 75)

# ============================================================
# 1. LOAD FEATURE INFORMATION
# ============================================================

print("\n[1] Loading feature information...")

features = joblib.load(
    HYBRID_DIR / "feature_columns.joblib"
)

row_ids = np.load(
    HYBRID_DIR / "test_row_id.npy"
)

labels = np.load(
    HYBRID_DIR / "y_test.npy"
)

rf_expected = np.load(
    RESULT_DIR / "friday_rf_predictions.npy"
)

if_expected = np.load(
    RESULT_DIR / "friday_if_predictions.npy"
)

rf_probabilities = np.load(
    RESULT_DIR / "friday_rf_probabilities.npy"
)

if_scores = np.load(
    RESULT_DIR / "friday_if_anomaly_scores.npy"
)

arrays = [
    labels,
    rf_expected,
    if_expected,
    rf_probabilities,
    if_scores
]

if any(len(array) != len(row_ids) for array in arrays):
    raise ValueError("Friday evaluation arrays are not aligned.")

print("Features:", len(features))
print("Friday records:", len(row_ids))

# ============================================================
# 2. RECONSTRUCT FRIDAY DATA
# ============================================================

print("\n[2] Loading original Friday traffic records...")

df = pd.read_parquet(
    DATA_DIR / "cic_ids2017_with_day.parquet"
)

df["_row_id"] = np.arange(len(df))

aligned = df.set_index("_row_id")

# ============================================================
# 3. SELECT REPRESENTATIVE RECORDS
# ============================================================

print("\n[3] Selecting four detector categories...")

both = np.flatnonzero(
    (rf_expected == 1) & (if_expected == 1)
)

rf_only = np.flatnonzero(
    (rf_expected == 1) & (if_expected == 0)
)

if_only = np.flatnonzero(
    (rf_expected == 0) & (if_expected == 1)
)

neither = np.flatnonzero(
    (rf_expected == 0) & (if_expected == 0)
)

categories = [
    ("BOTH_FLAGGED", both),
    ("RF_ONLY", rf_only),
    ("IF_ONLY", if_only),
    ("NEITHER_FLAGGED", neither)
]

selected = []

for name, indices in categories:

    if len(indices) > 0:
        selected.append((name, int(indices[0])))

if not selected:
    raise RuntimeError("No representative records found.")

# ============================================================
# 4. SEND RECORDS TO FASTAPI
# ============================================================

print("\n[4] Sending records to NeuroSphere API...")

results = []

for category, index in selected:

    record_id = int(row_ids[index])

    raw_record = aligned.loc[record_id]

    payload = {}

    for feature in features:

        value = raw_record[feature]

        if pd.isna(value):
            payload[feature] = None
        else:
            payload[feature] = float(value)

    print("\n" + "=" * 75)
    print("TEST CATEGORY:", category)
    print("ROW ID:", record_id)
    print("ACTUAL LABEL:", int(labels[index]))

    try:

        response = requests.post(
            API_URL,
            json=payload,
            timeout=60
        )

        print("HTTP STATUS:", response.status_code)

        response.raise_for_status()

        result = response.json()

        rf_api = result["detection"]["random_forest"]
        if_api = result["detection"]["isolation_forest"]

        rf_match = (
            int(rf_api["flagged"]) == int(rf_expected[index])
        )

        if_match = (
            int(if_api["flagged"]) == int(if_expected[index])
        )

        rf_score_difference = abs(
            rf_api["attack_probability"]
            - float(rf_probabilities[index])
        )

        if_score_difference = abs(
            if_api["anomaly_score"]
            - float(if_scores[index])
        )

        print("\nRANDOM FOREST")
        print("API prediction:", int(rf_api["flagged"]))
        print("Offline prediction:", int(rf_expected[index]))
        print("API probability:", rf_api["attack_probability"])
        print("Offline probability:", float(rf_probabilities[index]))
        print("Prediction match:", rf_match)
        print("Score difference:", rf_score_difference)

        print("\nISOLATION FOREST")
        print("API prediction:", int(if_api["flagged"]))
        print("Offline prediction:", int(if_expected[index]))
        print("API anomaly score:", if_api["anomaly_score"])
        print("Offline anomaly score:", float(if_scores[index]))
        print("Prediction match:", if_match)
        print("Score difference:", if_score_difference)

        print("\nAPI AGREEMENT:")
        print(
            result["risk_assessment"]["detector_agreement"]
        )

        results.append({
            "category": category,
            "row_id": record_id,
            "rf_prediction_match": rf_match,
            "if_prediction_match": if_match,
            "rf_score_difference": rf_score_difference,
            "if_score_difference": if_score_difference,
            "http_status": response.status_code
        })

    except requests.RequestException as exc:

        print("API REQUEST FAILED:", exc)

        results.append({
            "category": category,
            "row_id": record_id,
            "error": str(exc)
        })

    except (KeyError, ValueError) as exc:

        print("RESPONSE VALIDATION FAILED:", exc)

        results.append({
            "category": category,
            "row_id": record_id,
            "error": str(exc)
        })

# ============================================================
# 5. FINAL VERIFICATION SUMMARY
# ============================================================

print("\n" + "=" * 75)
print("NEUROSPHERE V2 API VERIFICATION SUMMARY")
print("=" * 75)

successful = [
    item for item in results
    if "error" not in item
]

if successful:

    rf_matches = all(
        item["rf_prediction_match"]
        for item in successful
    )

    if_matches = all(
        item["if_prediction_match"]
        for item in successful
    )

    print("Successful API requests:", len(successful))
    print("Random Forest predictions match:", rf_matches)
    print("Isolation Forest predictions match:", if_matches)

    print(
        "Maximum RF score difference:",
        max(item["rf_score_difference"] for item in successful)
    )

    print(
        "Maximum IF score difference:",
        max(item["if_score_difference"] for item in successful)
    )

    if rf_matches and if_matches:
        print("\nRESULT: API PREDICTIONS MATCH OFFLINE PREDICTIONS.")
    else:
        print("\nRESULT: PREDICTION MISMATCH FOUND.")

else:
    print("No successful API requests.")

# Save verification report
report_path = RESULT_DIR / "api_verification_report.csv"

pd.DataFrame(results).to_csv(
    report_path,
    index=False
)

print("\nReport saved:", report_path)

print("\nNEUROSPHERE V2 API VERIFICATION COMPLETED.")
