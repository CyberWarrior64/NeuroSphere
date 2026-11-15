from __future__ import annotations
import hashlib
import json
import os
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "datasets/source_day_flows"
MANIFEST = SOURCE_DIR / "source_day_flows_manifest.json"
OUTPUT = ROOT / "datasets/processed/cic_ids2017_with_day.parquet"
REPORT = ROOT / "datasets/processed/cic_ids2017_with_day_manifest.json"
FEATURE_PATH = ROOT / "saved_models/validated_randomsplit/feature_columns.joblib"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if OUTPUT.exists() or OUTPUT.with_suffix(OUTPUT.suffix + ".part").exists() or REPORT.exists():
        raise SystemExit("Refusing to overwrite an existing output, partial file, or manifest.")
    manifest = json.loads(MANIFEST.read_text())
    features = list(joblib.load(FEATURE_PATH))
    if len(features) != 67 or len(set(features)) != 67:
        raise SystemExit(f"Expected 67 unique model features; found {len(features)}.")

    schema = pa.schema(
        [*[pa.field(name, pa.float64()) for name in features],
         pa.field("attack_type", pa.string()),
         pa.field("binary_label", pa.int8()),
         pa.field("capture_day", pa.string()),
         pa.field("source_file", pa.string())]
    )
    output_part = OUTPUT.with_suffix(OUTPUT.suffix + ".part")
    total_rows = 0
    day_counts: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    source_rows = {}
    writer = None
    expected_rows = 0

    try:
        for entry in manifest["files"]:
            source = SOURCE_DIR / entry["filename"]
            if not source.is_file():
                raise SystemExit(f"Missing source file: {source}")
            actual_hash = sha256_file(source)
            if actual_hash.lower() != entry["sha256"].lower():
                raise SystemExit(f"SHA-256 mismatch for {source.name}: {actual_hash}")
            parquet = pq.ParquetFile(source)
            available = set(parquet.schema.names)
            missing = [name for name in features if name not in available]
            if missing or "Label" not in available:
                raise SystemExit(f"{source.name} missing required columns: {missing or ['Label']}")

            file_rows = 0
            expected_rows += parquet.metadata.num_rows
            columns = features + ["Label"]
            for batch in parquet.iter_batches(batch_size=50000, columns=columns):
                frame = batch.to_pandas()
                arrays = {}
                for name in features:
                    values = pd.to_numeric(frame[name], errors="coerce").replace([np.inf, -np.inf], np.nan).to_numpy(dtype=np.float64)
                    arrays[name] = pa.array(values, type=pa.float64())
                labels = frame["Label"].astype("string").str.strip().fillna("UNKNOWN")
                label_values = labels.astype(str).tolist()
                arrays["attack_type"] = pa.array(label_values, type=pa.string())
                arrays["binary_label"] = pa.array([int(label.upper() != "BENIGN") for label in label_values], type=pa.int8())
                arrays["capture_day"] = pa.array([entry["capture_day"]] * len(frame), type=pa.string())
                arrays["source_file"] = pa.array([source.name] * len(frame), type=pa.string())
                table = pa.Table.from_pydict(arrays, schema=schema)
                if writer is None:
                    writer = pq.ParquetWriter(output_part, schema, compression="snappy")
                writer.write_table(table, row_group_size=50000)
                n = len(frame)
                file_rows += n
                total_rows += n
                day_counts[entry["capture_day"]] += n
                label_counts.update(label_values)
            if file_rows != parquet.metadata.num_rows:
                raise RuntimeError(f"Row count mismatch for {source.name}: read {file_rows}, expected {parquet.metadata.num_rows}")
            source_rows[source.name] = file_rows
            print(f"Tagged {source.name}: {file_rows:,} flows", flush=True)

        if writer is None:
            raise RuntimeError("No source files were processed.")
        writer.close()
        writer = None
        if total_rows != expected_rows:
            raise RuntimeError(f"Total row count mismatch: read {total_rows}, expected {expected_rows}")
        os.replace(output_part, OUTPUT)
        result = {
            "source_repository": manifest.get("source_repository"),
            "revision": manifest.get("revision"),
            "source_status": manifest.get("mirror_status"),
            "rows": total_rows,
            "model_feature_count": len(features),
            "capture_day_counts": dict(day_counts),
            "label_counts": dict(sorted(label_counts.items())),
            "source_file_rows": source_rows,
            "output": str(OUTPUT.relative_to(ROOT)),
            "parquet_rows": pq.ParquetFile(OUTPUT).metadata.num_rows,
        }
        original = ROOT / "datasets/processed/cic_ids2017_validated.parquet"
        if original.exists():
            result["existing_validated_rows"] = pq.ParquetFile(original).metadata.num_rows
            result["row_count_matches_existing_validated"] = result["existing_validated_rows"] == total_rows
        REPORT.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2), flush=True)
    except BaseException:
        if writer is not None:
            writer.close()
        raise


if __name__ == "__main__":
    main()
