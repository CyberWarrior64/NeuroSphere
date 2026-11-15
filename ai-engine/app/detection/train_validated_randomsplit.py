from __future__ import annotations

from pathlib import Path
import json
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_FILE = BASE_DIR / "datasets/processed/cic_ids2017_validated.parquet"
FEATURE_FILE = BASE_DIR / "datasets/processed/hybrid_v2_training/feature_columns.joblib"
MODEL_DIR = BASE_DIR / "saved_models/validated_randomsplit"
RESULT_DIR = BASE_DIR / "datasets/processed/validated_randomsplit_results"
SAMPLE_SIZE = 300_000
RANDOM_STATE = 42
TARGET_IF_VALIDATION_FPR = 0.01

if MODEL_DIR.exists() or RESULT_DIR.exists():
    raise FileExistsError("Validated random-split outputs already exist; refusing to overwrite.")

features = list(joblib.load(FEATURE_FILE))
df = pd.read_parquet(DATA_FILE, columns=features + ["binary_label"])
missing = set(features + ["binary_label"]) - set(df.columns)
if missing:
    raise ValueError(f"Missing required dataset columns: {sorted(missing)}")

X = df[features].replace([np.inf, -np.inf], np.nan)
y = df["binary_label"].astype(np.int8)
if y.nunique() != 2:
    raise ValueError("Expected both benign and attack labels.")

# Draw the same-size stratified experiment sample used by the earlier baseline.
X, _, y, _ = train_test_split(
    X, y, train_size=min(SAMPLE_SIZE, len(df)), stratify=y, random_state=RANDOM_STATE
)
X = X.reset_index(drop=True)
y = y.reset_index(drop=True)

# Keep identical feature vectors out of both sides of evaluation; drop patterns
# that have conflicting binary labels before de-duplicating.
fingerprints = pd.util.hash_pandas_object(X, index=False).to_numpy(dtype=np.uint64)
audit = pd.DataFrame({"fingerprint": fingerprints, "label": y.to_numpy()})
conflict_hashes = audit.groupby("fingerprint")["label"].nunique()
conflict_hashes = conflict_hashes[conflict_hashes > 1].index.to_numpy(dtype=np.uint64)
valid = ~np.isin(fingerprints, conflict_hashes)
X = X.loc[valid].reset_index(drop=True)
y = y.loc[valid].reset_index(drop=True)
fingerprints = fingerprints[valid]
unique = ~pd.Series(fingerprints).duplicated().to_numpy()
X = X.loc[unique].reset_index(drop=True)
y = y.loc[unique].reset_index(drop=True)

# Random stratified 60/20/20 split. This is not a capture-day holdout.
X_train, X_holdout, y_train, y_holdout = train_test_split(
    X, y, test_size=0.40, stratify=y, random_state=RANDOM_STATE
)
X_validation, X_test, y_validation, y_test = train_test_split(
    X_holdout, y_holdout, test_size=0.50, stratify=y_holdout, random_state=RANDOM_STATE
)

print(f"Sample after conflict/dedup filtering: {len(X):,}")
print(f"Split sizes train/validation/test: {len(X_train):,}/{len(X_validation):,}/{len(X_test):,}")
print(f"Feature count: {len(features)}")
print(f"Training classes: {y_train.value_counts().sort_index().to_dict()}")

# Random Forest: impute and scale using training data only.
rf_preprocessor = Pipeline([
    ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
    ("scaler", StandardScaler()),
])
X_train_rf = rf_preprocessor.fit_transform(X_train)
X_validation_rf = rf_preprocessor.transform(X_validation)
X_test_rf = rf_preprocessor.transform(X_test)
rf_model = RandomForestClassifier(
    n_estimators=100,
    max_depth=25,
    min_samples_leaf=2,
    class_weight="balanced",
    n_jobs=-1,
    random_state=RANDOM_STATE,
    verbose=1,
)
start = time.time()
rf_model.fit(X_train_rf, y_train)
rf_seconds = time.time() - start
rf_probabilities = rf_model.predict_proba(X_test_rf)[:, 1]
rf_predictions = (rf_probabilities >= 0.50).astype(np.int8)
rf_tn, rf_fp, rf_fn, rf_tp = confusion_matrix(y_test, rf_predictions, labels=[0, 1]).ravel()
rf_metrics = {
    "threshold": 0.50,
    "accuracy": float(accuracy_score(y_test, rf_predictions)),
    "precision": float(precision_score(y_test, rf_predictions, zero_division=0)),
    "recall": float(recall_score(y_test, rf_predictions, zero_division=0)),
    "f1": float(f1_score(y_test, rf_predictions, zero_division=0)),
    "roc_auc": float(roc_auc_score(y_test, rf_probabilities)),
    "pr_auc": float(average_precision_score(y_test, rf_probabilities)),
    "false_positive_rate": float(rf_fp / (rf_fp + rf_tn)) if rf_fp + rf_tn else 0.0,
    "confusion_matrix_tn_fp_fn_tp": [int(rf_tn), int(rf_fp), int(rf_fn), int(rf_tp)],
    "training_seconds": rf_seconds,
    "classification_report": classification_report(y_test, rf_predictions, labels=[0, 1], target_names=["BENIGN", "ATTACK"], output_dict=True, zero_division=0),
}

# Isolation Forest: fit only on benign training traffic, calibrate on benign validation.
train_normal = X_train.loc[y_train.to_numpy() == 0]
validation_normal = X_validation.loc[y_validation.to_numpy() == 0]
if_imputer = SimpleImputer(strategy="median", keep_empty_features=True)
X_train_if = if_imputer.fit_transform(train_normal)
X_validation_normal_if = if_imputer.transform(validation_normal)
X_test_if = if_imputer.transform(X_test)
if_model = IsolationForest(
    n_estimators=300,
    max_samples=4096,
    contamination="auto",
    max_features=1.0,
    bootstrap=False,
    n_jobs=-1,
    random_state=RANDOM_STATE,
    verbose=1,
)
start = time.time()
if_model.fit(X_train_if)
if_seconds = time.time() - start
validation_normal_scores = -if_model.score_samples(X_validation_normal_if)
if_threshold = float(np.quantile(validation_normal_scores, 1 - TARGET_IF_VALIDATION_FPR))
if_test_scores = -if_model.score_samples(X_test_if)
if_predictions = (if_test_scores >= if_threshold).astype(np.int8)
if_tn, if_fp, if_fn, if_tp = confusion_matrix(y_test, if_predictions, labels=[0, 1]).ravel()
if_metrics = {
    "target_validation_fpr": TARGET_IF_VALIDATION_FPR,
    "actual_validation_fpr": float((validation_normal_scores >= if_threshold).mean()),
    "threshold": if_threshold,
    "accuracy": float(accuracy_score(y_test, if_predictions)),
    "precision": float(precision_score(y_test, if_predictions, zero_division=0)),
    "recall": float(recall_score(y_test, if_predictions, zero_division=0)),
    "f1": float(f1_score(y_test, if_predictions, zero_division=0)),
    "roc_auc": float(roc_auc_score(y_test, if_test_scores)),
    "false_positive_rate": float(if_fp / (if_fp + if_tn)) if if_fp + if_tn else 0.0,
    "confusion_matrix_tn_fp_fn_tp": [int(if_tn), int(if_fp), int(if_fn), int(if_tp)],
    "training_seconds": if_seconds,
    "classification_report": classification_report(y_test, if_predictions, labels=[0, 1], target_names=["BENIGN", "ATTACK"], output_dict=True, zero_division=0),
}

MODEL_DIR.mkdir(parents=True)
RESULT_DIR.mkdir(parents=True)
joblib.dump(rf_model, MODEL_DIR / "random_forest.joblib", compress=3)
joblib.dump(rf_preprocessor, MODEL_DIR / "random_forest_preprocessor.joblib", compress=3)
joblib.dump(if_model, MODEL_DIR / "isolation_forest.joblib", compress=3)
joblib.dump(if_imputer, MODEL_DIR / "isolation_forest_imputer.joblib", compress=3)
joblib.dump(features, MODEL_DIR / "feature_columns.joblib", compress=3)
report = {
    "dataset": str(DATA_FILE.relative_to(BASE_DIR)),
    "evaluation_design": "300k stratified random sample; conflict patterns removed; exact feature duplicates removed; random 60/20/20 split; not capture-day-disjoint",
    "random_state": RANDOM_STATE,
    "rows_after_filtering": int(len(X)),
    "features": features,
    "class_counts_after_filtering": {str(k): int(v) for k, v in y.value_counts().sort_index().items()},
    "split_rows": {"train": int(len(X_train)), "validation": int(len(X_validation)), "test": int(len(X_test))},
    "rf": rf_metrics,
    "isolation_forest": if_metrics,
}
with (RESULT_DIR / "evaluation.json").open("w") as handle:
    json.dump(report, handle, indent=2)
print("\nRF TEST METRICS:")
for key in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc", "false_positive_rate"]:
    print(f"  {key}: {rf_metrics[key]:.6f}")
print("\nISOLATION FOREST TEST METRICS:")
for key in ["accuracy", "precision", "recall", "f1", "roc_auc", "false_positive_rate", "actual_validation_fpr"]:
    print(f"  {key}: {if_metrics[key]:.6f}")
print(f"\nModels: {MODEL_DIR}")
print(f"Evaluation: {RESULT_DIR / 'evaluation.json'}")
