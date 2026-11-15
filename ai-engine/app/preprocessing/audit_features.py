
import pandas as pd
import numpy as np
from pathlib import Path

DATASET_DIR = Path("datasets/CIC-IDS2017")
CHUNK_SIZE = 100_000

# These are identifiers or metadata, not direct ML features.
EXCLUDED_COLUMNS = {
    "Flow ID",
    "Source IP",
    "Destination IP",
    "Timestamp",
    "Label"
}

total_rows = 0
invalid_counts = None
infinite_counts = None
feature_columns = None

print("=" * 70)
print("       NEUROSPHERE - CIC-IDS2017 FEATURE QUALITY AUDIT")
print("=" * 70)

for file in sorted(DATASET_DIR.glob("*.csv")):

    print(f"\nInspecting: {file.name}")

    for chunk in pd.read_csv(
        file,
        chunksize=CHUNK_SIZE,
        encoding="utf-8-sig",
        encoding_errors="replace"
    ):

        chunk.columns = [
            str(col).strip() for col in chunk.columns
        ]

        if feature_columns is None:
            feature_columns = [
                col for col in chunk.columns
                if col not in EXCLUDED_COLUMNS
            ]

            invalid_counts = pd.Series(
                0, index=feature_columns, dtype="int64"
            )

            infinite_counts = pd.Series(
                0, index=feature_columns, dtype="int64"
            )

        numeric = chunk[feature_columns].apply(
            pd.to_numeric, errors="coerce"
        )

        invalid_counts += numeric.isna().sum()

        infinite_counts += np.isinf(numeric).sum()

        total_rows += len(chunk)

print("\n" + "=" * 70)
print("                    AUDIT SUMMARY")
print("=" * 70)

print(f"Total records inspected: {total_rows:,}")
print(f"Total ML candidate features: {len(feature_columns)}")

print("\nTOP 25 FEATURES WITH INVALID / MISSING VALUES:")

summary = pd.DataFrame({
    "Invalid_or_Missing": invalid_counts,
    "Infinite": infinite_counts
})

summary["Invalid_Percent"] = (
    summary["Invalid_or_Missing"] / total_rows * 100
).round(3)

print(
    summary.sort_values(
        "Invalid_or_Missing",
        ascending=False
    ).head(25).to_string()
)

print("\nFEATURES WITH NO INVALID VALUES:")

clean_features = summary[
    (summary["Invalid_or_Missing"] == 0) &
    (summary["Infinite"] == 0)
]

print(f"Count: {len(clean_features)}")
print(clean_features.index.tolist())

print("\nFeature quality audit completed.")
