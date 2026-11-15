
from pathlib import Path
import gc
import joblib
import numpy as np
import pandas as pd

from sklearn.impute import SimpleImputer

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_FILE = (
    BASE_DIR / "datasets" / "processed"
    / "cic_ids2017_with_day.parquet"
)

OUTPUT_DIR = (
    BASE_DIR / "datasets" / "processed"
    / "anomaly_training"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TRAIN_DAYS = ["Monday", "Tuesday", "Wednesday"]
VALIDATION_DAY = "Thursday"
TEST_DAY = "Friday"

MAX_TRAIN_RECORDS = 200_000

print("=" * 70)
print("NEUROSPHERE - ISOLATION FOREST DATA PREPARATION")
print("=" * 70)

# --------------------------------------------------
# 1. Load dataset
# --------------------------------------------------

print("\nLoading CIC-IDS2017 dataset...")

df = pd.read_parquet(DATA_FILE)
df["_row_id"] = np.arange(len(df), dtype=np.int64)

metadata = {
    "capture_day",
    "source_file",
    "attack_type",
    "binary_label",
    "_row_id"
}

feature_columns = [
    col for col in df.columns
    if col not in metadata
]

# --------------------------------------------------
# 2. Select normal training traffic
# --------------------------------------------------

print("\nSelecting normal training traffic...")

train_df = df[
    df["capture_day"].isin(TRAIN_DAYS)
    & (df["binary_label"] == 0)
]

# Thursday BENIGN traffic for threshold calibration
validation_df = df[
    (df["capture_day"] == VALIDATION_DAY)
    & (df["binary_label"] == 0)
]

# All Friday traffic for final evaluation
test_df = df[
    df["capture_day"] == TEST_DAY
]
test_row_ids = test_df["_row_id"].to_numpy(dtype=np.int64)

X_train = train_df[feature_columns].copy().reset_index(drop=True)

X_val = validation_df[feature_columns].copy().reset_index(drop=True)

X_test = test_df[feature_columns].copy().reset_index(drop=True)

y_test = test_df["binary_label"].to_numpy(dtype=np.int8)

attack_types = test_df["attack_type"].astype(str).to_numpy()

source_files = test_df["source_file"].astype(str).to_numpy()

print("Training normal records:", f"{len(X_train):,}")
print("Thursday validation normal records:", f"{len(X_val):,}")
print("Friday testing records:", f"{len(X_test):,}")

del df, train_df, validation_df, test_df
gc.collect()

# --------------------------------------------------
# 3. Clean invalid numeric values
# --------------------------------------------------

print("\nCleaning numeric features...")

X_train = X_train.replace([np.inf, -np.inf], np.nan)
X_val = X_val.replace([np.inf, -np.inf], np.nan)
X_test = X_test.replace([np.inf, -np.inf], np.nan)

# Remove constant features based on training data only
constant_features = [
    col for col in feature_columns
    if X_train[col].nunique(dropna=False) <= 1
]

X_train = X_train.drop(columns=constant_features)
X_val = X_val.drop(columns=constant_features)
X_test = X_test.drop(columns=constant_features)

feature_columns = [
    col for col in feature_columns
    if col not in constant_features
]

print("Constant features removed:", len(constant_features))
print("Features retained:", len(feature_columns))

# --------------------------------------------------
# 4. Generate feature fingerprints
# --------------------------------------------------

print("\nGenerating feature fingerprints...")

train_hash = pd.util.hash_pandas_object(
    X_train, index=False
).to_numpy(dtype=np.uint64)

val_hash = pd.util.hash_pandas_object(
    X_val, index=False
).to_numpy(dtype=np.uint64)

test_hash = pd.util.hash_pandas_object(
    X_test, index=False
).to_numpy(dtype=np.uint64)

# --------------------------------------------------
# 5. Keep validation and test independent
# --------------------------------------------------

print("\nRemoving validation patterns found in Friday test data...")

test_unique_hashes = np.unique(test_hash)

val_overlap = np.isin(val_hash, test_unique_hashes)

validation_overlap_removed = int(val_overlap.sum())

keep_val = ~val_overlap

X_val = X_val.loc[keep_val].reset_index(drop=True)
val_hash = val_hash[keep_val]

# --------------------------------------------------
# 6. Remove training overlap with validation/test
# --------------------------------------------------

print("\nRemoving cross-split duplicates...")

heldout_hashes = np.unique(
    np.concatenate([val_hash, test_unique_hashes])
)

train_overlap = np.isin(train_hash, heldout_hashes)

cross_split_removed = int(train_overlap.sum())

keep_train = ~train_overlap

X_train = X_train.loc[keep_train].reset_index(drop=True)
train_hash = train_hash[keep_train]

# Remove repeated training feature patterns
before = len(X_train)

unique_mask = ~pd.Series(train_hash).duplicated().to_numpy()

X_train = X_train.loc[unique_mask].reset_index(drop=True)

training_duplicates_removed = before - len(X_train)

print("Validation/test overlap removed:", validation_overlap_removed)
print("Training cross-split duplicates removed:", cross_split_removed)
print("Repeated training records removed:", training_duplicates_removed)

# --------------------------------------------------
# 7. Select normal training sample
# --------------------------------------------------

print("\nSelecting training sample...")

sample_size = min(MAX_TRAIN_RECORDS, len(X_train))

if sample_size < 1000:
    raise ValueError("Insufficient normal training records.")

if sample_size < len(X_train):
    X_train = X_train.sample(
        n=sample_size,
        random_state=42
    ).reset_index(drop=True)

print("Final normal training records:", f"{len(X_train):,}")
print("Final validation records:", f"{len(X_val):,}")
print("Final Friday test records:", f"{len(X_test):,}")

# --------------------------------------------------
# 8. Fit imputer on training data only
# --------------------------------------------------

print("\nFitting median imputer on normal training data...")

imputer = SimpleImputer(strategy="median")

X_train_processed = imputer.fit_transform(X_train)
X_val_processed = imputer.transform(X_val)
X_test_processed = imputer.transform(X_test)

# --------------------------------------------------
# 9. Save prepared data
# --------------------------------------------------

print("\nSaving anomaly detection data...")

np.save(
    OUTPUT_DIR / "X_train.npy",
    X_train_processed.astype(np.float32)
)

np.save(
    OUTPUT_DIR / "X_validation.npy",
    X_val_processed.astype(np.float32)
)

np.save(
    OUTPUT_DIR / "X_test.npy",
    X_test_processed.astype(np.float32)
)

np.save(
    OUTPUT_DIR / "y_test.npy",
    y_test
)

np.save(
    OUTPUT_DIR / "attack_type_test.npy",
    attack_types
)

np.save(
    OUTPUT_DIR / "source_file_test.npy",
    source_files
)

np.save(
    OUTPUT_DIR / "test_row_id.npy",
    test_row_ids
)

joblib.dump(
    imputer,
    OUTPUT_DIR / "imputer.joblib"
)

joblib.dump(
    feature_columns,
    OUTPUT_DIR / "feature_columns.joblib"
)

# --------------------------------------------------
# 10. Final report
# --------------------------------------------------

print("\n" + "=" * 70)
print("ISOLATION FOREST DATA PREPARATION RESULTS")
print("=" * 70)

print("Training days:", ", ".join(TRAIN_DAYS))
print("Validation day:", VALIDATION_DAY)
print("Testing day:", TEST_DAY)

print("\nTraining normal records:", len(X_train))
print("Validation normal records:", len(X_val))
print("Friday testing records:", len(X_test))

print("\nFriday class distribution:")
print(pd.Series(y_test).value_counts().sort_index().to_dict())

print("\nFriday attack-family distribution:")
print(pd.Series(attack_types).value_counts().to_string())

print("\nOutput directory:", OUTPUT_DIR)

print("\nISOLATION FOREST DATA PREPARATION COMPLETED!")
