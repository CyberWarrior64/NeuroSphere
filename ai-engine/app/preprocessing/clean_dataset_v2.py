
import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

SOURCE_DIR = BASE_DIR / "datasets" / "CIC-IDS2017"
OUTPUT_DIR = BASE_DIR / "datasets" / "processed"

# New output file: original cleaned dataset remains untouched
OUTPUT_FILE = OUTPUT_DIR / "cic_ids2017_with_day.parquet"

CHUNK_SIZE = 100_000

EXCLUDED_COLUMNS = {
    "Flow ID",
    "Source IP",
    "Destination IP",
    "Timestamp",
    "Label",
    "Fwd Header Length.1"
}

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

csv_files = sorted(SOURCE_DIR.glob("*.csv"))

if not csv_files:
    raise FileNotFoundError("No CIC-IDS2017 CSV files found.")

writer = None
total_rows = 0
label_counts = {}

print("=" * 65)
print("NEUROSPHERE - CIC-IDS2017 CLEANING V2")
print("=" * 65)

try:
    for file in csv_files:

        # Extract capture day from original filename
        capture_day = file.name.split("-")[0].capitalize()

        print(f"\nProcessing: {file.name}")
        print(f"Capture day: {capture_day}")

        for chunk in pd.read_csv(
            file,
            chunksize=CHUNK_SIZE,
            encoding="utf-8-sig",
            encoding_errors="replace"
        ):

            chunk.columns = [
                str(col).strip() for col in chunk.columns
            ]

            if "Label" not in chunk.columns:
                raise ValueError(
                    f"Label column missing in {file.name}"
                )

            # Preserve original attack category
            chunk["attack_type"] = (
                chunk["Label"]
                .astype("string")
                .str.strip()
            )

            # Binary classification target
            chunk["binary_label"] = (
                chunk["attack_type"]
                .str.upper()
                .ne("BENIGN")
                .astype("int8")
            )

            # Select numeric features only
            feature_columns = [
                col for col in chunk.columns
                if col not in EXCLUDED_COLUMNS
                and col not in {"attack_type", "binary_label"}
            ]

            features = chunk[feature_columns].apply(
                pd.to_numeric,
                errors="coerce"
            )

            features = features.replace(
                [np.inf, -np.inf],
                np.nan
            )

            # Build cleaned dataset
            cleaned = features.copy()

            cleaned["attack_type"] = (
                chunk["attack_type"]
            )

            cleaned["binary_label"] = (
                chunk["binary_label"]
            )

            # Preserve original capture metadata
            cleaned["capture_day"] = capture_day
            cleaned["source_file"] = file.name

            cleaned = cleaned.dropna(
                subset=["attack_type"]
            )

            cleaned["attack_type"] = (
                cleaned["attack_type"].astype(str)
            )

            # Write Parquet incrementally
            table = pa.Table.from_pandas(
                cleaned,
                preserve_index=False
            )

            if writer is None:
                writer = pq.ParquetWriter(
                    OUTPUT_FILE,
                    table.schema,
                    compression="snappy"
                )

            writer.write_table(table)

            total_rows += len(cleaned)

            for label, count in (
                cleaned["attack_type"].value_counts().items()
            ):
                label_counts[label] = (
                    label_counts.get(label, 0) + int(count)
                )

        print(f"Completed: {file.name}")

finally:
    if writer is not None:
        writer.close()

print("\n" + "=" * 65)
print("DATA CLEANING V2 COMPLETED")
print("=" * 65)

print(f"Total records: {total_rows:,}")
print(f"Output file: {OUTPUT_FILE}")

print("\nBinary class distribution:")

benign = label_counts.get("BENIGN", 0)
attack = total_rows - benign

print(f"BENIGN: {benign:,}")
print(f"ATTACK: {attack:,}")

print("\nCapture-day metadata preserved.")
print("Original source filenames preserved.")

print("\nCleaning V2 completed successfully.")
