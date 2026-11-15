
from pathlib import Path
import numpy as np

BASE_DIR = Path(__file__).resolve().parents[2]

RF_DIR = BASE_DIR / "datasets/processed/day_based_training"
IF_DIR = BASE_DIR / "datasets/processed/anomaly_training"

# Load record IDs
rf_ids = np.load(RF_DIR / "test_row_id.npy")
if_ids = np.load(IF_DIR / "test_row_id.npy")

# Load metadata
rf_y = np.load(RF_DIR / "y_test.npy")
if_y = np.load(IF_DIR / "y_test.npy")

rf_attack = np.load(
    RF_DIR / "attack_type_test.npy", allow_pickle=True
).astype(str)

if_attack = np.load(
    IF_DIR / "attack_type_test.npy", allow_pickle=True
).astype(str)

rf_source = np.load(
    RF_DIR / "source_file_test.npy", allow_pickle=True
).astype(str)

if_source = np.load(
    IF_DIR / "source_file_test.npy", allow_pickle=True
).astype(str)

# Match by original row ID
common_ids, rf_idx, if_idx = np.intersect1d(
    rf_ids,
    if_ids,
    return_indices=True
)

# Compare metadata in matched order
labels_match = np.array_equal(rf_y[rf_idx], if_y[if_idx])

attacks_match = np.array_equal(
    rf_attack[rf_idx], if_attack[if_idx]
)

sources_match = np.array_equal(
    rf_source[rf_idx], if_source[if_idx]
)

print("=" * 65)
print("NEUROSPHERE - COMMON TEST RECORD VERIFICATION")
print("=" * 65)

print("Common records:", len(common_ids))
print("Labels match:", labels_match)
print("Attack types match:", attacks_match)
print("Source files match:", sources_match)

print("\nAttack-family distribution:")
unique, counts = np.unique(rf_attack[rf_idx], return_counts=True)

for family, count in zip(unique, counts):
    print(f"{family:15s}: {count:,}")

print("\n" + "=" * 65)

if labels_match and attacks_match and sources_match:
    print("SUCCESS: COMMON TEST RECORDS VERIFIED")
    print("Safe to proceed with aligned model evaluation.")
else:
    print("ERROR: METADATA MISMATCH")
    print("Do not combine predictions.")

print("=" * 65)
