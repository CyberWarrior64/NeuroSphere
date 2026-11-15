
from pathlib import Path
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "datasets" / "processed" / "training"

print("=" * 65)
print("NEUROSPHERE - TRAIN/TEST DUPLICATE AUDIT")
print("=" * 65)

X_train = np.load(DATA_DIR / "X_train.npy")
X_test = np.load(DATA_DIR / "X_test.npy")
y_train = np.load(DATA_DIR / "y_train.npy")
y_test = np.load(DATA_DIR / "y_test.npy")

print("\nGenerating feature fingerprints...")

train_hash = pd.util.hash_pandas_object(
    pd.DataFrame(X_train), index=False
).to_numpy()

test_hash = pd.util.hash_pandas_object(
    pd.DataFrame(X_test), index=False
).to_numpy()

print("Checking overlap...")

train_unique = pd.DataFrame({
    "hash": train_hash,
    "label": y_train
}).drop_duplicates("hash")

test_records = pd.DataFrame({
    "hash": test_hash,
    "label": y_test
})

comparison = test_records.merge(
    train_unique,
    on="hash",
    how="inner",
    suffixes=("_test", "_train")
)

overlap = len(comparison)
conflicts = (
    comparison["label_test"] != comparison["label_train"]
).sum()

print("\n" + "=" * 65)
print("DUPLICATE AUDIT RESULTS")
print("=" * 65)

print("Training records:", len(X_train))
print("Testing records:", len(X_test))
print("Test records matching training features:", overlap)
print("Matching records with conflicting labels:", conflicts)

if overlap == 0:
    print("\nNo exact train/test feature overlap detected.")
else:
    print("\nWARNING: Matching feature records were found.")

if conflicts > 0:
    print("WARNING: Some matching features have different labels.")

print("\nAudit completed.")
