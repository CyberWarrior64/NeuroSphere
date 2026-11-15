from __future__ import annotations
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / 'datasets/reference_pcaps/friday-reference'
OUTPUT = SOURCE_DIR / 'Friday-traffic-labels-combined.parquet'
FILES = [
    'Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv.parquet',
    'Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv.parquet',
    'Friday-WorkingHours-Morning.pcap_ISCX.csv.parquet',
]


def main() -> None:
    if OUTPUT.exists() or OUTPUT.with_suffix(OUTPUT.suffix + '.part').exists():
        raise SystemExit(f'Refusing to overwrite existing output: {OUTPUT}')
    manifest = json.loads((SOURCE_DIR / 'friday_reference_manifest.json').read_text())
    hashes = {entry['filename']: entry['sha256'] for entry in manifest['files']}
    tables = []
    total_rows = 0
    for filename in FILES:
        path = SOURCE_DIR / filename
        if not path.exists() or path.name not in hashes:
            raise RuntimeError(f'Missing or unlisted reference labels file: {path}')
        table = pq.read_table(path)
        rows = table.num_rows
        table = table.append_column('source_file', pa.array([filename] * rows, type=pa.string()))
        tables.append(table)
        total_rows += rows
        print(f'Loaded {filename}: {rows:,} rows', flush=True)
    combined = pa.concat_tables(tables)
    part = OUTPUT.with_suffix(OUTPUT.suffix + '.part')
    pq.write_table(combined, part, compression='snappy', row_group_size=50000)
    if pq.ParquetFile(part).metadata.num_rows != total_rows:
        raise RuntimeError('Combined label table row count mismatch.')
    part.replace(OUTPUT)
    print(f'Wrote {OUTPUT.relative_to(ROOT)}: {total_rows:,} rows, {len(combined.schema.names)} columns', flush=True)


if __name__ == '__main__':
    main()
