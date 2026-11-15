from pathlib import Path
import gc
import joblib
import numpy as np
import pandas as pd

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_FILE = (
    BASE_DIR / "datasets" / "processed"
    / "cic_ids2017_with_day.parquet"
)

OUTPUT_DIR = (
    BASE_DIR / "datasets" / "processed"
    / "hybrid_v2_friday_eval"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TRAIN_DAYS = ["Monday", "Tuesday", "Wednesday"]
VALIDATION_DAY = "Thursday"
TEST_DAY = "Friday"

MAX_TRAIN_RECORDS = 300_000
RANDOM_STATE = 42


def save_array(name, values):
    np.save(OUTPUT_DIR / name, values)


def class_distribution(labels):
    values, counts = np.unique(labels, return_counts=True)
    return dict(zip(values.tolist(), counts.tolist()))


print("=" * 75)
print("NEUROSPHERE - HYBRID V2 THREE-WAY DATA PREPARATION")
print("=" * 75)

# --------------------------------------------------
# 1. Load dataset
# --------------------------------------------------

print("\nLoading dataset...")

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
# 2. Separate the three capture-day partitions
# --------------------------------------------------

print("\nSeparating capture days...")

train_df = df[df["capture_day"].isin(TRAIN_DAYS)].copy()
validation_df = df[df["capture_day"] == VALIDATION_DAY].copy()
test_df = df[df["capture_day"] == TEST_DAY].copy()

if train_df.empty or validation_df.empty or test_df.empty:
    raise ValueError("One or more capture-day partitions are empty.")

print("Monday-Wednesday training:", f"{len(train_df):,}")
print("Thursday validation:", f"{len(validation_df):,}")
print("Friday final testing:", f"{len(test_df):,}")

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

X_train = train_df[feature_columns].copy()
X_validation = validation_df[feature_columns].copy()
X_test = test_df[feature_columns].copy()

y_train = train_df["binary_label"].astype("int8").reset_index(drop=True)
y_validation = validation_df["binary_label"].astype("int8").reset_index(drop=True)
y_test = test_df["binary_label"].astype("int8").reset_index(drop=True)

train_ids = train_df["_row_id"].to_numpy(dtype=np.int64)
validation_ids = validation_df["_row_id"].to_numpy(dtype=np.int64)
test_ids = test_df["_row_id"].to_numpy(dtype=np.int64)

validation_attack_types = (
    validation_df["attack_type"].astype(str).reset_index(drop=True)
)
test_attack_types = (
    test_df["attack_type"].astype(str).reset_index(drop=True)
)

validation_source_files = (
    validation_df["source_file"].astype(str).reset_index(drop=True)
)
test_source_files = (
    test_df["source_file"].astype(str).reset_index(drop=True)
)

del df, train_df, validation_df, test_df
gc.collect()

for frame in (X_train, X_validation, X_test):
    frame.reset_index(drop=True, inplace=True)
    frame.replace([np.inf, -np.inf], np.nan, inplace=True)

# --------------------------------------------------
# 4. Remove constant features using training only
# --------------------------------------------------

print("\nChecking constant features using training data...")

constant_features = [
    col for col in feature_columns
    if X_train[col].nunique(dropna=False) <= 1
]

if constant_features:
    X_train.drop(columns=constant_features, inplace=True)
    X_validation.drop(columns=constant_features, inplace=True)
    X_test.drop(columns=constant_features, inplace=True)

feature_columns = [
    col for col in feature_columns
    if col not in constant_features
]

print("Constant features removed:", len(constant_features))
print("Features retained:", len(feature_columns))

# --------------------------------------------------
# 5. Generate feature fingerprints
# --------------------------------------------------

print("\nGenerating feature fingerprints...")

train_hash = pd.util.hash_pandas_object(
    X_train, index=False
).to_numpy(dtype=np.uint64)

validation_hash = pd.util.hash_pandas_object(
    X_validation, index=False
).to_numpy(dtype=np.uint64)

test_hash = pd.util.hash_pandas_object(
    X_test, index=False
).to_numpy(dtype=np.uint64)

# --------------------------------------------------
# 6. Remove feature patterns with conflicting labels
#    across ALL three partitions
# --------------------------------------------------

print("\nChecking conflicting labels across all partitions...")

all_hashes = np.concatenate([
    train_hash,
    validation_hash,
    test_hash
])

all_labels = np.concatenate([
    y_train.to_numpy(),
    y_validation.to_numpy(),
    y_test.to_numpy()
])

audit = pd.DataFrame({
    "fingerprint": all_hashes,
    "label": all_labels
})

conflict_counts = audit.groupby("fingerprint")["label"].nunique()

conflict_hashes = conflict_counts[
    conflict_counts > 1
].index.to_numpy(dtype=np.uint64)

print("Conflicting feature patterns:", len(conflict_hashes))

del all_hashes, all_labels, audit, conflict_counts
gc.collect()

def remove_conflicts(X, y, ids, hashes, *metadata):
    valid = ~np.isin(hashes, conflict_hashes)

    X = X.loc[valid].reset_index(drop=True)
    y = y.loc[valid].reset_index(drop=True)
    ids = ids[valid]
    hashes = hashes[valid]

    filtered_metadata = []

    for item in metadata:
        filtered_metadata.append(
            item.loc[valid].reset_index(drop=True)
        )

    removed = int((~valid).sum())

    return (
        X, y, ids, hashes,
        filtered_metadata, removed
    )


(
    X_train, y_train, train_ids, train_hash,
    _, train_conflicts_removed
) = remove_conflicts(
    X_train, y_train, train_ids, train_hash
)

(
    X_validation, y_validation,
    validation_ids, validation_hash,
    validation_metadata, validation_conflicts_removed
) = remove_conflicts(
    X_validation,
    y_validation,
    validation_ids,
    validation_hash,
    validation_attack_types,
    validation_source_files
)

validation_attack_types, validation_source_files = validation_metadata

(
    X_test, y_test, test_ids, test_hash,
    test_metadata, test_conflicts_removed
) = remove_conflicts(
    X_test,
    y_test,
    test_ids,
    test_hash,
    test_attack_types,
    test_source_files
)

test_attack_types, test_source_files = test_metadata

print("Training conflicts removed:", train_conflicts_removed)
print("Validation conflicts removed:", validation_conflicts_removed)
print("Testing conflicts removed:", test_conflicts_removed)

# --------------------------------------------------
# 7. Remove cross-partition duplicates
#    Priority: Friday > Thursday > Monday-Wednesday
# --------------------------------------------------

print("\nRemoving cross-partition duplicate patterns...")

# Remove Thursday patterns that also occur on Friday.
test_hashes = np.unique(test_hash)

validation_keep = ~np.isin(validation_hash, test_hashes)

validation_overlap_removed = int((~validation_keep).sum())

X_validation = X_validation.loc[validation_keep].reset_index(drop=True)
y_validation = y_validation.loc[validation_keep].reset_index(drop=True)
validation_ids = validation_ids[validation_keep]
validation_hash = validation_hash[validation_keep]

validation_attack_types = (
    validation_attack_types.loc[validation_keep].reset_index(drop=True)
)
validation_source_files = (
    validation_source_files.loc[validation_keep].reset_index(drop=True)
)

# Remove training patterns appearing in either later partition.
later_hashes = np.unique(
    np.concatenate([validation_hash, test_hash])
)

train_keep = ~np.isin(train_hash, later_hashes)

train_overlap_removed = int((~train_keep).sum())

X_train = X_train.loc[train_keep].reset_index(drop=True)
y_train = y_train.loc[train_keep].reset_index(drop=True)
train_ids = train_ids[train_keep]
train_hash = train_hash[train_keep]

print("Thursday overlap with Friday removed:", validation_overlap_removed)
print("Training overlap with later partitions removed:", train_overlap_removed)

# --------------------------------------------------
# 8. Remove repeated training patterns
# --------------------------------------------------

print("\nRemoving repeated training patterns...")

unique_mask = ~pd.Series(train_hash).duplicated().to_numpy()

training_duplicates_removed = int((~unique_mask).sum())

X_train = X_train.loc[unique_mask].reset_index(drop=True)
y_train = y_train.loc[unique_mask].reset_index(drop=True)
train_ids = train_ids[unique_mask]

print("Repeated training records removed:", training_duplicates_removed)

if y_train.nunique() != 2:
    raise ValueError("Training data must contain both classes.")

if y_validation.nunique() != 2:
    raise ValueError("Thursday validation must contain both classes.")

if y_test.nunique() != 2:
    raise ValueError("Friday testing must contain both classes.")

# --------------------------------------------------
# 9. Select training sample
# --------------------------------------------------

print("\nSelecting training sample...")

sample_size = min(MAX_TRAIN_RECORDS, len(X_train))

if sample_size < 2:
    raise ValueError("Not enough training records.")

if sample_size < len(X_train):
    selected_indices, _ = train_test_split(
        np.arange(len(X_train)),
        train_size=sample_size,
        stratify=y_train,
        random_state=RANDOM_STATE
    )
else:
    selected_indices = np.arange(len(X_train))

X_train = X_train.iloc[selected_indices].reset_index(drop=True)
y_train = y_train.iloc[selected_indices].reset_index(drop=True)
train_ids = train_ids[selected_indices]

# --------------------------------------------------
# 10. Fit preprocessing on training only
# --------------------------------------------------

print("\nFitting preprocessing on training data only...")

preprocessor = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler())
])

X_train_processed = preprocessor.fit_transform(X_train)
X_validation_processed = preprocessor.transform(X_validation)
X_test_processed = preprocessor.transform(X_test)

# --------------------------------------------------
# 11. Save datasets
# --------------------------------------------------

print("\nSaving V2 datasets...")

save_array("X_train.npy", X_train_processed.astype(np.float32))
save_array("X_validation.npy", X_validation_processed.astype(np.float32))
save_array("X_test.npy", X_test_processed.astype(np.float32))

save_array("y_train.npy", y_train.to_numpy(dtype=np.int8))
save_array("y_validation.npy", y_validation.to_numpy(dtype=np.int8))
save_array("y_test.npy", y_test.to_numpy(dtype=np.int8))

save_array("train_row_id.npy", train_ids)
save_array("validation_row_id.npy", validation_ids)
save_array("test_row_id.npy", test_ids)

save_array(
    "attack_type_validation.npy",
    validation_attack_types.to_numpy(dtype=str)
)
save_array(
    "attack_type_test.npy",
    test_attack_types.to_numpy(dtype=str)
)

save_array(
    "source_file_validation.npy",
    validation_source_files.to_numpy(dtype=str)
)
save_array(
    "source_file_test.npy",
    test_source_files.to_numpy(dtype=str)
)

joblib.dump(preprocessor, OUTPUT_DIR / "preprocessor.joblib")
joblib.dump(feature_columns, OUTPUT_DIR / "feature_columns.joblib")

# --------------------------------------------------
# 12. Final report
# --------------------------------------------------

print("\n" + "=" * 75)
print("HYBRID V2 DATA PREPARATION RESULTS")
print("=" * 75)

print("\nTraining records:", f"{len(X_train):,}")
print("Thursday validation records:", f"{len(X_validation):,}")
print("Friday testing records:", f"{len(X_test):,}")
print("Features:", len(feature_columns))

print("\nTraining classes:", class_distribution(y_train.to_numpy()))
print("Validation classes:", class_distribution(y_validation.to_numpy()))
print("Testing classes:", class_distribution(y_test.to_numpy()))

print("\nThursday attack-family distribution:")
print(validation_attack_types.value_counts().to_string())

print("\nFriday attack-family distribution:")
print(test_attack_types.value_counts().to_string())

print("\nAll three partitions have separate row IDs.")
print("Output directory:", OUTPUT_DIR)

print("\nHYBRID V2 DATA PREPARATION COMPLETED!")
