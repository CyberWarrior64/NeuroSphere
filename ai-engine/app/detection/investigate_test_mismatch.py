
from pathlib import Path
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]

RF_DIR = BASE_DIR / "datasets" / "processed" / "day_based_training"
IF_DIR = BASE_DIR / "datasets" / "processed" / "anomaly_training"

rf_source = np.load(
    RF_DIR / "source_file_test.npy",
    allow_pickle=True
).astype(str)

if_source = np.load(
    IF_DIR / "source_file_test.npy",
    allow_pickle=True
).astype(str)

rf_attack = np.load(
    RF_DIR / "attack_type_test.npy",
    allow_pickle=True
).astype(str)

if_attack = np.load(
    IF_DIR / "attack_type_test.npy",
    allow_pickle=True
).astype(str)

rf_y = np.load(RF_DIR / "y_test.npy")
if_y = np.load(IF_DIR / "y_test.npy")

print("=" * 70)
print("NEUROSPHERE - TEST DATA MISMATCH INVESTIGATION")
print("=" * 70)

# Compare record counts by source file and attack type
rf_df = pd.DataFrame({
    "source": rf_source,
    "attack": rf_attack,
    "label": rf_y
})

if_df = pd.DataFrame({
    "source": if_source,
    "attack": if_attack,
    "label": if_y
})

print("\n1. SOURCE FILE COUNTS")
print("-" * 70)

print("Random Forest:")
print(rf_df["source"].value_counts().sort_index())

print("\nIsolation Forest:")
print(if_df["source"].value_counts().sort_index())

print("\n2. ATTACK FAMILY COUNTS")
print("-" * 70)

print("Random Forest:")
print(rf_df["attack"].value_counts())

print("\nIsolation Forest:")
print(if_df["attack"].value_counts())

print("\n3. MULTISET DIFFERENCE")
print("-" * 70)

rf_counts = rf_df.value_counts(
    ["source", "attack", "label"]
)

if_counts = if_df.value_counts(
    ["source", "attack", "label"]
)

comparison = pd.concat(
    [
        rf_counts.rename("RF_count"),
        if_counts.rename("IF_count")
    ],
    axis=1
).fillna(0).astype(int)

difference = comparison[
    comparison["RF_count"] != comparison["IF_count"]
]

print("Groups with different counts:")
print(difference.to_string())

print("\n4. TOTAL RECORD DIFFERENCE")
print("-" * 70)

print("RF records:", len(rf_df))
print("IF records:", len(if_df))
print("Difference:", len(if_df) - len(rf_df))

print("\nInvestigation completed.")
