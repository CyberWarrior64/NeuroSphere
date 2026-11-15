from __future__ import annotations
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / 'datasets/processed/cic_ids2017_with_day.parquet'
EVAL_DIR = ROOT / 'datasets/processed/hybrid_v2_friday_eval'
ACTIVE_DIR = ROOT / 'datasets/processed/hybrid_v2_training'


def main() -> None:
    features = list(joblib.load(ACTIVE_DIR / 'feature_columns.joblib'))
    eval_features = list(joblib.load(EVAL_DIR / 'feature_columns.joblib'))
    if features != eval_features:
        raise RuntimeError('Friday feature order differs from the active Hybrid V2 model.')
    preprocessor = joblib.load(ACTIVE_DIR / 'preprocessor.joblib')
    if getattr(preprocessor, 'n_features_in_', None) != len(features):
        raise RuntimeError('Active preprocessor input dimension does not match feature schema.')

    test_ids = np.load(EVAL_DIR / 'test_row_id.npy')
    expected_rows = len(np.load(EVAL_DIR / 'y_test.npy', mmap_mode='r'))
    if len(test_ids) != expected_rows or len(np.unique(test_ids)) != len(test_ids):
        raise RuntimeError('Friday row IDs are inconsistent or duplicated.')

    table = pq.read_table(DATA_FILE, columns=features)
    raw = table.take(pa.array(test_ids, type=pa.int64())).to_pandas()
    del table
    for column in features:
        raw[column] = pd.to_numeric(raw[column], errors='coerce')
    raw = raw.replace([np.inf, -np.inf], np.nan)
    transformed = preprocessor.transform(raw).astype(np.float32, copy=False)
    if transformed.shape != (expected_rows, len(features)):
        raise RuntimeError(f'Unexpected transformed Friday shape: {transformed.shape}')

    output = EVAL_DIR / 'X_test.npy'
    partial = EVAL_DIR / 'X_test.npy.part'
    with partial.open('wb') as handle:
        np.save(handle, transformed)
    os.replace(partial, output)
    print(f'Transformed {expected_rows:,} Friday flows with the saved Hybrid V2 preprocessor.')
    print(f'Wrote {output.relative_to(ROOT)} with shape {transformed.shape}.')


if __name__ == '__main__':
    main()
