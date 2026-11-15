
import pandas as pd
from pathlib import Path
from collections import Counter

DATASET_DIR = Path("datasets/CIC-IDS2017")
CHUNK_SIZE = 100_000

total_rows = 0
total_labels = Counter()

print("=" * 65)
print("       NEUROSPHERE - CIC-IDS2017 DATASET INSPECTION")
print("=" * 65)

csv_files = sorted(DATASET_DIR.glob("*.csv"))

if not csv_files:
    raise FileNotFoundError("No CSV files found in dataset directory.")

print(f"\nCSV files found: {len(csv_files)}")

for file in csv_files:

    print("\n" + "-" * 65)
    print(f"FILE: {file.name}")

    file_rows = 0
    file_labels = Counter()

    try:
        # Read column names only
        header = pd.read_csv(
            file,
            nrows=0,
            encoding="utf-8-sig"
        )

        columns = [str(col).strip() for col in header.columns]

        print(f"Number of features: {len(columns)}")

        label_column = next(
            (col for col in columns if col.lower() == "label"),
            None
        )

        if label_column is None:
            print("ERROR: Label column not found.")
            continue

        print(f"Label column: {label_column}")

        # Process traffic in manageable chunks
        for chunk in pd.read_csv(
            file,
            chunksize=CHUNK_SIZE,
            encoding="utf-8-sig",
            encoding_errors="replace"
        ):

            chunk.columns = [
                str(col).strip() for col in chunk.columns
            ]

            labels = (
                chunk[label_column]
                .astype("string")
                .str.strip()
                .fillna("MISSING")
            )

            file_labels.update(labels.value_counts().to_dict())
            file_rows += len(chunk)

        total_rows += file_rows
        total_labels.update(file_labels)

        print(f"Total records: {file_rows:,}")
        print("Label distribution:")

        for label, count in file_labels.most_common():
            print(f"  {label}: {count:,}")

    except Exception as error:
        print(f"ERROR processing file: {error}")

print("\n" + "=" * 65)
print("                  COMPLETE DATASET SUMMARY")
print("=" * 65)

print(f"Total records processed: {total_rows:,}")
print("\nOverall label distribution:")

for label, count in total_labels.most_common():
    print(f"  {label}: {count:,}")

print("\nDataset inspection completed.")
