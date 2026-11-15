
from pathlib import Path
import gc
import joblib
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_FILE = (
    BASE_DIR
    / "datasets"
    / "processed"
    / "cic_ids2017_with_day.parquet"
)

OUTPUT_DIR = (
    BASE_DIR
    / "datasets"
    / "processed"
    / "day_based_training"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TRAIN_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday"]
TEST_DAY = "Friday"
MAX_TRAIN_RECORDS = 300_000

print("=" * 70)
print("NEUROSPHERE - CAPTURE-DAY EVALUATION PREPARATION")
print("=" * 70)

# --------------------------------------------------
# 1. Load dataset
# --------------------------------------------------

print("\nLoading metadata-preserving dataset...")

df = pd.read_parquet(DATA_FILE)
df["_row_id"] = np.arange(len(df), dtype=np.int64)

print("Total records:", f"{len(df):,}")

required_columns = {
    "capture_day",
    "source_file",
    "attack_type",
    "binary_label"
}

missing = required_columns - set(df.columns)

if missing:
    raise ValueError(f"Missing required columns: {missing}")

# --------------------------------------------------
# 2. Separate training and testing days
# --------------------------------------------------

print("\nSeparating capture days...")

train_df = df[df["capture_day"].isin(TRAIN_DAYS)].copy()
test_df = df[df["capture_day"] == TEST_DAY].copy()
test_row_id = test_df["_row_id"].to_numpy(dtype=np.int64)

if train_df.empty or test_df.empty:
    raise ValueError("Training or testing day data is empty.")

print("Training-day records:", f"{len(train_df):,}")
print("Friday testing records:", f"{len(test_df):,}")

# --------------------------------------------------
# 3. Select model features
# --------------------------------------------------

excluded = {
    "capture_day",
    "source_file",
    "attack_type",
    "binary_label",
    "_row_id"
}

feature_columns = [
    col for col in df.columns
    if col not in excluded
]

X_train_all = train_df[feature_columns].copy()
X_test = test_df[feature_columns].copy()

y_train_all = train_df["binary_label"].astype("int8").reset_index(drop=True)
y_test = test_df["binary_label"].astype("int8").reset_index(drop=True)

attack_type_test = (
    test_df["attack_type"].astype(str).reset_index(drop=True)
)

source_file_test = (
    test_df["source_file"].astype(str).reset_index(drop=True)
)

# Release original dataframes
del df, train_df, test_df
gc.collect()

X_train_all = X_train_all.reset_index(drop=True)
X_test = X_test.reset_index(drop=True)

X_train_all = X_train_all.replace([np.inf, -np.inf], np.nan)
X_test = X_test.replace([np.inf, -np.inf], np.nan)

# Remove constant training features
constant_features = [
    col for col in feature_columns
    if X_train_all[col].nunique(dropna=False) <= 1
]

X_train_all = X_train_all.drop(columns=constant_features)
X_test = X_test.drop(columns=constant_features)

feature_columns = [
    col for col in feature_columns
    if col not in constant_features
]

print("\nFeatures retained:", len(feature_columns))
print("Constant features removed:", len(constant_features))

# --------------------------------------------------
# 4. Generate exact feature fingerprints
# --------------------------------------------------

print("\nGenerating Friday feature fingerprints...")

test_hash = pd.util.hash_pandas_object(
    X_test,
    index=False
).to_numpy(dtype=np.uint64)

print("Generating training feature fingerprints...")

train_hash = pd.util.hash_pandas_object(
    X_train_all,
    index=False
).to_numpy(dtype=np.uint64)

# --------------------------------------------------
# 5. Remove ambiguous binary labels in each split
# --------------------------------------------------

print("\nChecking ambiguous feature patterns...")

test_audit = pd.DataFrame({
    "fingerprint": test_hash,
    "label": y_test.to_numpy()
})

test_conflicts = (
    test_audit.groupby("fingerprint")["label"].nunique()
)

test_conflict_hashes = set(
    test_conflicts[test_conflicts > 1].index
)

test_valid = ~np.isin(
    test_hash,
    list(test_conflict_hashes)
)

test_ambiguous_removed = int((~test_valid).sum())

X_test = X_test.loc[test_valid].reset_index(drop=True)
y_test = y_test.loc[test_valid].reset_index(drop=True)
test_row_id = test_row_id[test_valid]

attack_type_test = attack_type_test.loc[test_valid].reset_index(drop=True)
source_file_test = source_file_test.loc[test_valid].reset_index(drop=True)

test_hash = test_hash[test_valid]

train_audit = pd.DataFrame({
    "fingerprint": train_hash,
    "label": y_train_all.to_numpy()
})

train_conflicts = (
    train_audit.groupby("fingerprint")["label"].nunique()
)

train_conflict_hashes = set(
    train_conflicts[train_conflicts > 1].index
)

train_valid = ~np.isin(
    train_hash,
    list(train_conflict_hashes)
)

train_ambiguous_removed = int((~train_valid).sum())

X_train_all = X_train_all.loc[train_valid].reset_index(drop=True)
y_train_all = y_train_all.loc[train_valid].reset_index(drop=True)

train_hash = train_hash[train_valid]

# --------------------------------------------------
# 6. Remove training patterns found in Friday
# --------------------------------------------------

print("\nChecking cross-day duplicate overlap...")

friday_hashes = np.unique(test_hash)

overlap_mask = np.isin(train_hash, friday_hashes)

cross_day_duplicates = int(overlap_mask.sum())

keep_train = ~overlap_mask

X_train_all = X_train_all.loc[keep_train].reset_index(drop=True)
y_train_all = y_train_all.loc[keep_train].reset_index(drop=True)
train_hash = train_hash[keep_train]

print("Training ambiguous records removed:", train_ambiguous_removed)
print("Friday ambiguous records removed:", test_ambiguous_removed)
print("Cross-day training duplicates removed:", cross_day_duplicates)

# --------------------------------------------------
# 7. Remove repeated training feature patterns
# --------------------------------------------------

print("\nRemoving repeated training feature patterns...")

before_dedup = len(X_train_all)

unique_mask = ~pd.Series(train_hash).duplicated().to_numpy()

X_train_all = X_train_all.loc[unique_mask].reset_index(drop=True)
y_train_all = y_train_all.loc[unique_mask].reset_index(drop=True)

training_duplicates_removed = before_dedup - len(X_train_all)

print("Repeated training records removed:", training_duplicates_removed)

# --------------------------------------------------
# 8. Select stratified training sample
# --------------------------------------------------

print("\nSelecting training sample...")

if y_train_all.nunique() != 2:
    raise ValueError("Training data must contain both binary classes.")

sample_size = min(MAX_TRAIN_RECORDS, len(X_train_all))

if sample_size < 2:
    raise ValueError("Not enough training records.")

if sample_size == len(X_train_all):
    X_train = X_train_all.copy()
    y_train = y_train_all.copy()
else:
    X_train, _, y_train, _ = train_test_split(
        X_train_all,
        y_train_all,
        train_size=sample_size,
        stratify=y_train_all,
        random_state=42
    )

X_train = X_train.reset_index(drop=True)
y_train = y_train.reset_index(drop=True)

# --------------------------------------------------
# 9. Fit preprocessing on training data only
# --------------------------------------------------

print("\nFitting preprocessing on training data only...")

preprocessor = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler())
])

X_train_processed = preprocessor.fit_transform(X_train)
X_test_processed = preprocessor.transform(X_test)

# --------------------------------------------------
# 10. Save experiment files
# --------------------------------------------------

print("\nSaving day-based experiment files...")

np.save(
    OUTPUT_DIR / "X_train.npy",
    X_train_processed.astype(np.float32)
)

np.save(
    OUTPUT_DIR / "X_test.npy",
    X_test_processed.astype(np.float32)
)

np.save(
    OUTPUT_DIR / "y_train.npy",
    y_train.to_numpy(dtype=np.int8)
)

np.save(
    OUTPUT_DIR / "y_test.npy",
    y_test.to_numpy(dtype=np.int8)
)

np.save(
    OUTPUT_DIR / "attack_type_test.npy",
    attack_type_test.to_numpy(dtype=str)
)

np.save(
    OUTPUT_DIR / "source_file_test.npy",
    source_file_test.to_numpy(dtype=str)
)

np.save(
    OUTPUT_DIR / "test_row_id.npy",
    test_row_id
)

joblib.dump(
    preprocessor,
    OUTPUT_DIR / "preprocessor.joblib"
)

joblib.dump(
    feature_columns,
    OUTPUT_DIR / "feature_columns.joblib"
)

# --------------------------------------------------
# 11. Final report
# --------------------------------------------------

print("\n" + "=" * 70)
print("DAY-BASED DATA PREPARATION RESULTS")
print("=" * 70)

print("Training days:", ", ".join(TRAIN_DAYS))
print("Testing day:", TEST_DAY)

print("\nTraining records:", f"{len(X_train):,}")
print("Friday testing records:", f"{len(X_test):,}")
print("Features:", len(feature_columns))

print("\nTraining class distribution:")
print(y_train.value_counts().sort_index().to_dict())

print("\nFriday testing class distribution:")
print(y_test.value_counts().sort_index().to_dict())

print("\nFriday attack-family distribution:")
print(attack_type_test.value_counts().to_string())

print("\nCross-day duplicate records removed:", cross_day_duplicates)

print("\nOutput directory:", OUTPUT_DIR)

print("\nDAY-BASED PREPARATION COMPLETED!")
