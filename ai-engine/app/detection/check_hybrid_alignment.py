
from pathlib import Path
import numpy as np
import joblib

BASE_DIR = Path(__file__).resolve().parents[2]

RF_DIR = BASE_DIR / "datasets" / "processed" / "day_based_training"
IF_DIR = BASE_DIR / "datasets" / "processed" / "anomaly_training"

print("=" * 70)
print("NEUROSPHERE - HYBRID DATASET ALIGNMENT CHECK")
print("=" * 70)

# Load test arrays
rf_X = np.load(RF_DIR / "X_test.npy", mmap_mode="r")
rf_y = np.load(RF_DIR / "y_test.npy")
rf_attack = np.load(
    RF_DIR / "attack_type_test.npy",
    allow_pickle=True
)
rf_source = np.load(
    RF_DIR / "source_file_test.npy",
    allow_pickle=True
)

if_X = np.load(IF_DIR / "X_test.npy", mmap_mode="r")
if_y = np.load(IF_DIR / "y_test.npy")
if_attack = np.load(
    IF_DIR / "attack_type_test.npy",
    allow_pickle=True
)
if_source = np.load(
    IF_DIR / "source_file_test.npy",
    allow_pickle=True
)

print("\n1. ARRAY SHAPES")
print("-" * 70)

print("Random Forest X:", rf_X.shape)
print("Isolation Forest X:", if_X.shape)

print("Random Forest y:", rf_y.shape)
print("Isolation Forest y:", if_y.shape)

print("Random Forest attack types:", rf_attack.shape)
print("Isolation Forest attack types:", if_attack.shape)

print("Random Forest source files:", rf_source.shape)
print("Isolation Forest source files:", if_source.shape)

print("\n2. FEATURE INFORMATION")
print("-" * 70)

rf_features = joblib.load(RF_DIR / "feature_columns.joblib")
if_features = joblib.load(IF_DIR / "feature_columns.joblib")

print("Random Forest feature count:", len(rf_features))
print("Isolation Forest feature count:", len(if_features))

print("\n3. ROW COUNT CHECK")
print("-" * 70)

same_rows = (
    len(rf_y) == len(if_y)
    == len(rf_attack) == len(if_attack)
    == len(rf_source) == len(if_source)
)

print("All row counts equal:", same_rows)

if not same_rows:
    print("\nSTOP: Row counts differ. Direct combination is unsafe.")
    raise SystemExit(1)

print("\n4. LABEL ALIGNMENT")
print("-" * 70)

labels_equal = np.array_equal(rf_y, if_y)
print("Binary labels identical:", labels_equal)

print("\n5. ATTACK TYPE ALIGNMENT")
print("-" * 70)

attack_equal = np.array_equal(rf_attack, if_attack)
print("Attack types identical:", attack_equal)

print("\n6. SOURCE FILE ALIGNMENT")
print("-" * 70)

source_equal = np.array_equal(rf_source, if_source)
print("Source file order identical:", source_equal)

print("\n7. FIRST FIVE RECORDS")
print("-" * 70)

for i in range(min(5, len(rf_y))):
    print(
        f"Row {i}: "
        f"RF label={rf_y[i]}, "
        f"IF label={if_y[i]}, "
        f"RF attack={rf_attack[i]}, "
        f"IF attack={if_attack[i]}, "
        f"RF source={rf_source[i]}, "
        f"IF source={if_source[i]}"
    )

print("\n" + "=" * 70)

if same_rows and labels_equal and attack_equal and source_equal:
    print("RESULT: METADATA ALIGNMENT PASSED")
    print("The test arrays have matching metadata and ordering.")
    print("Further feature-level verification is still recommended.")
else:
    print("RESULT: ALIGNMENT NOT CONFIRMED")
    print("Do not combine predictions by row position yet.")

print("=" * 70)
