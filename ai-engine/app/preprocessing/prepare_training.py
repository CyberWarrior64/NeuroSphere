
import pandas as pd
import numpy as np

from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
import joblib

DATASET = Path("datasets/processed/cic_ids2017_clean.parquet")
OUTPUT_DIR = Path("datasets/processed/training")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42
SAMPLE_SIZE = 300_000

print("=" * 65)
print("NEUROSPHERE - TRAINING DATA PREPARATION")
print("=" * 65)

print("\nLoading cleaned dataset...")

df = pd.read_parquet(DATASET)

print(f"Original records: {len(df):,}")

# Keep only the features and labels for binary classification
X = df.drop(
    columns=["attack_type", "binary_label"]
)

y = df["binary_label"].astype("int8")

# Remove duplicate-style feature
if "Fwd Header Length.1" in X.columns:
    X = X.drop(columns=["Fwd Header Length.1"])

# Replace extreme values that cannot be represented as finite floats
X = X.replace([np.inf, -np.inf], np.nan)

# Remove features that have no variation
constant_features = [
    col for col in X.columns
    if X[col].nunique(dropna=True) <= 1
]

X = X.drop(columns=constant_features)

print(f"Features selected: {X.shape[1]}")
print(f"Constant features removed: {len(constant_features)}")

# Take stratified sample for first experiment
if len(df) > SAMPLE_SIZE:

    X, _, y, _ = train_test_split(
        X,
        y,
        train_size=SAMPLE_SIZE,
        stratify=y,
        random_state=RANDOM_STATE
    )

print(f"Experiment records: {len(X):,}")

# Split into training and test sets
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    stratify=y,
    random_state=RANDOM_STATE
)

print(f"Training records: {len(X_train):,}")
print(f"Testing records: {len(X_test):,}")

print("\nTraining class distribution:")
print(y_train.value_counts().to_dict())

print("\nTesting class distribution:")
print(y_test.value_counts().to_dict())

# Preprocessing is fitted only on training data
preprocessor = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler())
])

X_train_processed = preprocessor.fit_transform(X_train)
X_test_processed = preprocessor.transform(X_test)

# Save prepared datasets
np.save(
    OUTPUT_DIR / "X_train.npy",
    X_train_processed
)

np.save(
    OUTPUT_DIR / "X_test.npy",
    X_test_processed
)

np.save(
    OUTPUT_DIR / "y_train.npy",
    y_train.to_numpy()
)

np.save(
    OUTPUT_DIR / "y_test.npy",
    y_test.to_numpy()
)

joblib.dump(
    preprocessor,
    OUTPUT_DIR / "preprocessor.joblib"
)

joblib.dump(
    list(X.columns),
    OUTPUT_DIR / "feature_columns.joblib"
)

print("\nTraining data preparation completed!")
print(f"Output directory: {OUTPUT_DIR}")
