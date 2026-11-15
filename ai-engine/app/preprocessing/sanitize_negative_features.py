from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

BASE_DIR = Path(__file__).resolve().parents[2]
SOURCE_FILE = BASE_DIR / "datasets/processed/cic_ids2017_clean.parquet"
OUTPUT_FILE = BASE_DIR / "datasets/processed/cic_ids2017_validated.parquet"
TEMP_FILE = OUTPUT_FILE.with_suffix(".parquet.partial")
INVALID_IF_NEGATIVE = [
    "Flow Duration",
    "Fwd Header Length",
    "Bwd Header Length",
    "min_seg_size_forward",
]
BATCH_SIZE = 100_000

if OUTPUT_FILE.exists() or TEMP_FILE.exists():
    raise FileExistsError(f"Refusing to overwrite {OUTPUT_FILE} or {TEMP_FILE}")

parquet = pq.ParquetFile(SOURCE_FILE)
missing = set(INVALID_IF_NEGATIVE) - set(parquet.schema_arrow.names)
if missing:
    raise ValueError(f"Required columns missing from source: {sorted(missing)}")

writer = None
rows = 0
invalid_counts = {column: 0 for column in INVALID_IF_NEGATIVE}
try:
    for batch in parquet.iter_batches(batch_size=BATCH_SIZE):
        frame = batch.to_pandas()
        for column in INVALID_IF_NEGATIVE:
            invalid = frame[column] < 0
            invalid_counts[column] += int(invalid.sum())
            frame.loc[invalid, column] = np.nan
        table = pa.Table.from_pandas(frame, preserve_index=False)
        if writer is None:
            writer = pq.ParquetWriter(TEMP_FILE, table.schema, compression="snappy")
        writer.write_table(table)
        rows += len(frame)
finally:
    if writer is not None:
        writer.close()

TEMP_FILE.replace(OUTPUT_FILE)
print(f"Rows copied: {rows:,}")
print("Negative values replaced with null:")
for column, count in invalid_counts.items():
    print(f"  {column}: {count:,}")
print(f"Output: {OUTPUT_FILE}")
