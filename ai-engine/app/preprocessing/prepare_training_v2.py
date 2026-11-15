
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_FILE = BASE_DIR / "datasets" / "processed" / "cic_ids2017_clean.parquet"
OUTPUT_DIR = BASE_DIR / "datasets" / "processed" / "training"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 65)
print("NEUROSPHERE - LEAKAGE-REDUCED DATA PREPARATION")
print("=" * 65)

print("\nLoading cleaned CIC-IDS2017 dataset...")
df = pd.read_parquet(DATA_FILE)

y = df["binary_label"].astype("int8")
X = df.drop(columns=["attack_type", "binary_label"])

X = X.replace([np.inf, -np.inf], np.nan)

# Remove constant features
constant_features = [
    col for col in X.columns
    if X[col].nunique(dropna=False) <= 1
]

X = X.drop(columns=constant_features)

print("Original records:", len(df))
print("Features retained:", X.shape[1])
print("Constant features removed:", len(constant_features))

# Select a stratified experiment sample
print("\nSelecting 300,000 stratified records...")

X_sample, _, y_sample, _ = train_test_split(
    X,
    y,
    train_size=300_000,
    stratify=y,
    random_state=42
)

X_sample = X_sample.reset_index(drop=True)
y_sample = y_sample.reset_index(drop=True)

# Generate fingerprints for identical feature patterns
print("\nChecking duplicate feature patterns...")

fingerprints = pd.util.hash_pandas_object(
    X_sample,
    index=False
)

audit = pd.DataFrame({
    "fingerprint": fingerprints.to_numpy(),
    "label": y_sample.to_numpy()
})

# Identify feature patterns assigned conflicting labels
label_counts = audit.groupby("fingerprint")["label"].nunique()
conflict_fingerprints = label_counts[label_counts > 1].index

conflict_rows = audit["fingerprint"].isin(
    conflict_fingerprints
).sum()

print("Conflicting feature patterns:", len(conflict_fingerprints))
print("Records with conflicting labels:", conflict_rows)

# Exclude all ambiguous feature patterns
valid_mask = ~audit["fingerprint"].isin(
    conflict_fingerprints
)

clean_data = X_sample.loc[valid_mask].copy()
clean_data["binary_label"] = y_sample.loc[valid_mask].to_numpy()
clean_data["_fingerprint"] = fingerprints.loc[valid_mask].to_numpy()

# Keep only one record for each identical feature pattern
before_deduplication = len(clean_data)

clean_data = clean_data.drop_duplicates(
    subset="_fingerprint",
    keep="first"
).reset_index(drop=True)

duplicates_removed = before_deduplication - len(clean_data)

print("Duplicate records removed:", duplicates_removed)
print("Unique records remaining:", len(clean_data))

# Separate features and labels
feature_columns = [
    col for col in clean_data.columns
    if col not in ["binary_label", "_fingerprint"]
]

X_unique = clean_data[feature_columns]
y_unique = clean_data["binary_label"]

# Fresh stratified 80/20 split
print("\nCreating fresh 80/20 train/test split...")

X_train, X_test, y_train, y_test = train_test_split(
    X_unique,
    y_unique,
    test_size=0.20,
    stratify=y_unique,
    random_state=42
)

# Fit preprocessing on training data only
print("\nFitting preprocessing pipeline...")

preprocessor = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler())
])

X_train_processed = preprocessor.fit_transform(X_train)
X_test_processed = preprocessor.transform(X_test)

# Save arrays as float32 to reduce storage and memory usage
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

joblib.dump(preprocessor, OUTPUT_DIR / "preprocessor.joblib")
joblib.dump(feature_columns, OUTPUT_DIR / "feature_columns.joblib")

print("\n" + "=" * 65)
print("NEW DATA PREPARATION RESULTS")
print("=" * 65)

print("Final unique records:", len(clean_data))
print("Training records:", len(X_train))
print("Testing records:", len(X_test))
print("Features:", len(feature_columns))

print("\nTraining class distribution:")
print(y_train.value_counts().sort_index().to_dict())

print("\nTesting class distribution:")
print(y_test.value_counts().sort_index().to_dict())

print("\nSaved updated training files to:", OUTPUT_DIR)
print("\nLeakage-reduced preparation completed!")
