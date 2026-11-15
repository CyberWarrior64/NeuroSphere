
import pyarrow.parquet as pq
import numpy as np
from pathlib import Path
from collections import Counter

FILE = Path("datasets/processed/cic_ids2017_clean.parquet")

if not FILE.exists():
    raise FileNotFoundError(FILE)

parquet = pq.ParquetFile(FILE)

total_rows = parquet.metadata.num_rows
columns = parquet.schema.names

print("=" * 65)
print("NEUROSPHERE - CLEAN DATASET VERIFICATION")
print("=" * 65)

print(f"\nTotal records: {total_rows:,}")
print(f"Total columns: {len(columns)}")
print(f"File size: {FILE.stat().st_size / (1024**2):.2f} MB")

label_counts = Counter()
null_counts = Counter()
infinite_counts = Counter()
invalid_binary = 0
processed = 0

for batch in parquet.iter_batches(batch_size=100_000):

    df = batch.to_pandas()

    processed += len(df)

    label_counts.update(
        df["attack_type"].value_counts().to_dict()
    )

    for col in df.columns:
        null_counts[col] += int(df[col].isna().sum())

    feature_cols = [
        col for col in df.columns
        if col not in {"attack_type", "binary_label"}
    ]

    numeric = df[feature_cols].select_dtypes(
        include="number"
    )

    for col in numeric.columns:
        infinite_counts[col] += int(
            np.isinf(numeric[col].to_numpy()).sum()
        )

    expected_binary = (
        df["attack_type"].str.upper() != "BENIGN"
    ).astype("int8")

    invalid_binary += int(
        (df["binary_label"] != expected_binary).sum()
    )

print("\nRECORD VALIDATION")
print(f"Records scanned: {processed:,}")
print(f"Binary label mismatches: {invalid_binary}")

print("\nLABEL DISTRIBUTION")

for label, count in label_counts.most_common():
    print(f"{label}: {count:,}")

print("\nMISSING VALUES")

for col, count in null_counts.most_common():
    if count > 0:
        print(f"{col}: {count:,}")

print("\nINFINITE VALUES")

for col, count in infinite_counts.most_common():
    if count > 0:
        print(f"{col}: {count:,}")

print("\nDATASET SCHEMA")
print(columns)

print("\nVerification completed.")
