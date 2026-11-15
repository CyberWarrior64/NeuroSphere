from __future__ import annotations
import argparse
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score

from app.feature_extraction.cicflowmeter_mapper import MODEL_TO_CICFLOWMETER, TIME_FEATURES

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / 'datasets/reference_pcaps/friday-reference'
GENERATED = DATA_DIR / 'Friday-WorkingHours-novel-attack-core-reference.csv'
INPUT_PCAP = DATA_DIR / 'Friday-WorkingHours-novel-attack-core.pcapng'
REFERENCE = DATA_DIR / 'Friday-traffic-labels-combined.parquet'
OUTPUT = DATA_DIR / 'Friday-novel-attack-core-minute-key-evaluation.json'
MODEL_DIR = ROOT / 'saved_models'
HYBRID_DIR = ROOT / 'datasets/processed/hybrid_v2_training'
ANOMALY_DIR = ROOT / 'datasets/processed/anomaly_training'
WINDOWS = [
    ('2017-07-07T13:18:00Z', '2017-07-07T14:04:00Z'),
    ('2017-07-07T17:48:00Z', '2017-07-07T18:12:00Z'),
]
CORE_FEATURES = [
    'Flow Duration', 'Total Fwd Packets', 'Total Backward Packets',
    'Total Length of Fwd Packets', 'Total Length of Bwd Packets',
]
FLAG_FEATURES = [
    'FIN Flag Count', 'SYN Flag Count', 'RST Flag Count', 'PSH Flag Count',
    'ACK Flag Count', 'URG Flag Count', 'ECE Flag Count',
]
EMPIRICAL_FLAG_MAPPING_CANDIDATE = {
    'SYN Flag Count': 'psh_flag_cnt',
    'PSH Flag Count': 'syn_flag_cnt',
    'RST Flag Count': 'ece_flag_cnt',
}
FIRST_PACKET_LEGACY_ORDER_CANDIDATE = {
    'FIN Flag Count': 'rst_flag_cnt',
    'SYN Flag Count': 'psh_flag_cnt',
    'RST Flag Count': 'ece_flag_cnt',
    'PSH Flag Count': 'syn_flag_cnt',
    'URG Flag Count': 'fin_flag_cnt',
}


def unique_keys(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    counts = frame.groupby(keys, dropna=False).size().rename('_key_count')
    unique = counts[counts == 1].reset_index()[keys]
    return frame.merge(unique, on=keys, how='inner', validate='many_to_one')


def metrics(y_true: np.ndarray, score: np.ndarray, threshold: float) -> dict:
    pred = (score >= threshold).astype(np.int8)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    return {
        'accuracy': float(accuracy_score(y_true, pred)),
        'precision': float(precision_score(y_true, pred, zero_division=0)),
        'recall': float(recall_score(y_true, pred, zero_division=0)),
        'f1': float(f1_score(y_true, pred, zero_division=0)),
        'false_positive_rate': float(fp / (fp + tn)) if (fp + tn) else None,
        'true_negatives': int(tn), 'false_positives': int(fp),
        'false_negatives': int(fn), 'true_positives': int(tp),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Evaluate the Friday raw-PCAP adapter against minute-resolution reference labels.')
    parser.add_argument('--output', type=Path, default=OUTPUT, help='New JSON path; existing reports are never overwritten.')
    parser.add_argument('--generated', type=Path, default=GENERATED, help='Generated reference-adapter CSV.')
    parser.add_argument('--input-pcap', type=Path, default=INPUT_PCAP, help='PCAP/PCAPNG used to generate the CSV.')
    parser.add_argument('--windows-report', type=Path, help='Optional slicer report whose windows define the reference subset.')
    parser.add_argument(
        '--flag-count-mode', choices=('all_packets', 'first_packet'), default='all_packets',
        help='Flag-count behavior used to create the supplied CSV; reporting only.',
    )
    parser.add_argument(
        '--empirical-flag-mapping-candidate', action='store_true',
        help='Evaluate an empirical SYN/PSH swap and ECE-to-RST candidate mapping without changing the live mapper.',
    )
    parser.add_argument(
        '--first-packet-legacy-order-candidate', action='store_true',
        help='Evaluate first-packet SYN/PSH/RST plus FIN/URG legacy-order mappings; evaluation-only.',
    )
    args = parser.parse_args()
    output_path = args.output
    if output_path.exists():
        raise SystemExit(f'Refusing to overwrite evaluation report: {output_path}')
    selected_windows = WINDOWS
    if args.windows_report is not None:
        window_report = json.loads(args.windows_report.read_text())
        selected_windows = [(item['start'], item['end']) for item in window_report['windows_utc']]
    generated = pd.read_csv(args.generated)
    reference = pd.read_parquet(REFERENCE)
    model_features = list(joblib.load(HYBRID_DIR / 'feature_columns.joblib'))
    if args.empirical_flag_mapping_candidate and args.first_packet_legacy_order_candidate:
        raise SystemExit('Choose one flag-mapping candidate at a time.')
    model_to_cicflowmeter = dict(MODEL_TO_CICFLOWMETER)
    if args.empirical_flag_mapping_candidate:
        model_to_cicflowmeter.update(EMPIRICAL_FLAG_MAPPING_CANDIDATE)
    if args.first_packet_legacy_order_candidate:
        model_to_cicflowmeter.update(FIRST_PACKET_LEGACY_ORDER_CANDIDATE)
    if len(model_features) != 67 or any(name not in model_to_cicflowmeter for name in model_features):
        raise RuntimeError('Packet adapter mapping does not cover the active 67-feature model schema.')

    local_time = pd.to_datetime(generated['timestamp'], errors='raise')
    if local_time.dt.tz is None:
        local_time = local_time.dt.tz_localize(ZoneInfo('Asia/Kolkata'))
    generated['timestamp_minute'] = local_time.dt.tz_convert('UTC').dt.tz_localize(None).dt.floor('min')
    reference_timestamp = pd.to_datetime(reference['Timestamp'], errors='raise', utc=True)
    reference['timestamp_minute'] = reference_timestamp.dt.tz_localize(None).dt.floor('min')
    reference_timestamp_resolution = {
        'rows_checked': int(len(reference_timestamp)),
        'rows_aligned_to_minute': int((reference_timestamp.dt.second.eq(0) & reference_timestamp.dt.microsecond.eq(0)).sum()),
        'resolution_used': 'minute',
    }
    generated = generated.rename(columns={'src_ip': 'src_ip', 'dst_ip': 'dst_ip', 'src_port': 'src_port', 'dst_port': 'dst_port', 'protocol': 'protocol'})
    reference = reference.rename(columns={'Source IP': 'src_ip', 'Destination IP': 'dst_ip', 'Source Port': 'src_port', 'Destination Port': 'dst_port', 'Protocol': 'protocol'})
    for frame in (generated, reference):
        frame['src_port'] = pd.to_numeric(frame['src_port'], errors='raise').astype('int64')
        frame['dst_port'] = pd.to_numeric(frame['dst_port'], errors='raise').astype('int64')
        frame['protocol'] = pd.to_numeric(frame['protocol'], errors='raise').astype('int64')

    keys = ['src_ip', 'dst_ip', 'src_port', 'dst_port', 'protocol', 'timestamp_minute']
    def generated_column_name(column: str) -> str:
        if column in keys:
            return column
        return column + '_generated' if column in reference.columns else column

    generated_unique = unique_keys(generated, keys)
    reference_unique = unique_keys(reference, keys)
    matched = generated_unique.merge(reference_unique, on=keys, how='inner', suffixes=('_generated', '_reference'), validate='one_to_one')
    if matched.empty:
        raise RuntimeError('No unique direct flows matched. Check timezone and capture-window alignment before interpreting the result.')

    feature_matches = {}
    for feature in model_features:
        gen_col = model_to_cicflowmeter[feature]
        gen_name = generated_column_name(gen_col)
        ref_name = 'dst_port' if feature == 'Destination Port' else feature
        actual = pd.to_numeric(matched[gen_name], errors='coerce')
        expected = pd.to_numeric(matched[ref_name], errors='coerce')
        if feature in TIME_FEATURES:
            actual = actual * 1_000_000.0
        feature_matches[feature] = np.isclose(actual.to_numpy(), expected.to_numpy(), rtol=1e-9, atol=1e-6, equal_nan=True)
    feature_matrix = np.column_stack(list(feature_matches.values()))
    core_matrix = np.column_stack([feature_matches[name] for name in CORE_FEATURES])
    exact_core = core_matrix.all(axis=1)
    exact_full = feature_matrix.all(axis=1)
    flag_agreement_by_core_match = {
        feature: {
            'overall_agreement': float(feature_matches[feature].mean()),
            'agreement_when_core_fields_match': (
                float(feature_matches[feature][exact_core].mean()) if exact_core.any() else None
            ),
            'agreement_when_any_core_field_differs': (
                float(feature_matches[feature][~exact_core].mean()) if (~exact_core).any() else None
            ),
        }
        for feature in FLAG_FEATURES
    }
    flag_value_differences = {}
    for feature in FLAG_FEATURES:
        generated_values = pd.to_numeric(
            matched[generated_column_name(model_to_cicflowmeter[feature])], errors='coerce'
        ).to_numpy(dtype=float)
        reference_values = pd.to_numeric(matched[feature], errors='coerce').to_numpy(dtype=float)
        valid_core = exact_core & np.isfinite(generated_values) & np.isfinite(reference_values)
        deltas = generated_values[valid_core] - reference_values[valid_core]
        delta_counts = pd.Series(deltas.astype(np.int64)).value_counts().head(9)
        flag_value_differences[feature] = {
            'rows_compared_with_exact_core': int(valid_core.sum()),
            'mean_generated': float(generated_values[valid_core].mean()) if valid_core.any() else None,
            'mean_reference': float(reference_values[valid_core].mean()) if valid_core.any() else None,
            'mean_absolute_difference': float(np.abs(deltas).mean()) if len(deltas) else None,
            'generated_zero_fraction': float(np.isclose(generated_values[valid_core], 0).mean()) if valid_core.any() else None,
            'reference_zero_fraction': float(np.isclose(reference_values[valid_core], 0).mean()) if valid_core.any() else None,
            'most_common_signed_differences_generated_minus_reference': {
                str(int(delta)): int(count) for delta, count in delta_counts.items()
            },
        }

    labels = matched['Label'].astype(str).str.strip().to_numpy()
    y_true = (labels != 'BENIGN').astype(np.int8)
    raw = pd.DataFrame({
        feature: pd.to_numeric(matched[generated_column_name(model_to_cicflowmeter[feature])], errors='coerce')
        for feature in model_features
    }, columns=model_features).replace([np.inf, -np.inf], np.nan)
    rf = joblib.load(MODEL_DIR / 'random_forest_cicids2017_hybrid_v2.joblib')
    rf_preprocessor = joblib.load(HYBRID_DIR / 'preprocessor.joblib')
    if_model = joblib.load(MODEL_DIR / 'isolation_forest_cicids2017_v2.joblib')
    if_imputer = joblib.load(ANOMALY_DIR / 'imputer.joblib')
    rf_threshold = float(json.loads((ROOT / 'datasets/processed/hybrid_v2_results/rf_v2_selected_threshold.json').read_text())['selected_threshold'])
    if_threshold = float(joblib.load(MODEL_DIR / 'isolation_forest_calibration.joblib')['threshold'])
    x_rf = rf_preprocessor.transform(raw)
    rf_scores = rf.predict_proba(x_rf)[:, 1]
    rf_predictions = rf_scores >= rf_threshold
    x_if = if_imputer.transform(raw)
    if_scores = -if_model.score_samples(x_if)
    if_predictions = if_scores >= if_threshold

    detector_results = {
        'random_forest': {'threshold': rf_threshold, **metrics(y_true, rf_scores, rf_threshold)},
        'isolation_forest': {'threshold': if_threshold, **metrics(y_true, if_scores, if_threshold)},
        'offline_or': metrics(y_true, (rf_predictions | if_predictions).astype(float), 0.5),
        'offline_and': metrics(y_true, (rf_predictions & if_predictions).astype(float), 0.5),
    }
    family_results = []
    for family in sorted(set(labels)):
        mask = labels == family
        count = int(mask.sum())
        family_results.append({
            'attack_type': family,
            'matched_rows': count,
            'random_forest_detected': int(rf_predictions[mask].sum()),
            'random_forest_recall': float(rf_predictions[mask].mean()),
            'isolation_forest_detected': int(if_predictions[mask].sum()),
            'isolation_forest_recall': float(if_predictions[mask].mean()),
            'offline_or_detected': int((rf_predictions[mask] | if_predictions[mask]).sum()),
        })

    ref_time = pd.to_datetime(reference['Timestamp'], errors='raise', utc=True)
    in_windows = pd.Series(False, index=reference.index)
    for start, end in selected_windows:
        in_windows |= ref_time.between(pd.Timestamp(start), pd.Timestamp(end), inclusive='both')
    reference_window = reference.loc[in_windows]
    attack_rows_window = reference_window[reference_window['Label'].astype(str).str.strip() != 'BENIGN']
    matched_family_counts = pd.Series(labels).value_counts().to_dict()
    scoped_family_counts = attack_rows_window['Label'].astype(str).str.strip().value_counts().to_dict()
    family_coverage = {
        family: {
            'reference_attack_rows_in_selected_windows': int(count),
            'directly_matched_rows': int(matched_family_counts.get(family, 0)),
            'direct_match_rate': float(matched_family_counts.get(family, 0) / count) if count else None,
        }
        for family, count in scoped_family_counts.items()
    }
    report = {
        'evaluation': 'Friday raw-PCAP attack-window adapter validation',
        'status': 'experimental; sampled raw capture windows, not full-day replay',
        'input_pcap': str(args.input_pcap),
        'windows_source_report': str(args.windows_report) if args.windows_report is not None else None,
        'packet_adapter': 'CICFlowMeterReferenceSession source-level Java semantics port',
        'packet_flag_count_mode': args.flag_count_mode,
        'feature_mapping_variant': (
            'first-packet legacy-order-informed FIN/SYN/RST/PSH/URG candidate; evaluation-only'
            if args.first_packet_legacy_order_candidate else (
                'empirical SYN/PSH swap and ECE-to-RST candidate; evaluation-only'
                if args.empirical_flag_mapping_candidate else 'current production feature mapping'
            )
        ),
        'candidate_flag_mapping': (
            FIRST_PACKET_LEGACY_ORDER_CANDIDATE if args.first_packet_legacy_order_candidate else (
                EMPIRICAL_FLAG_MAPPING_CANDIDATE if args.empirical_flag_mapping_candidate else None
            )
        ),
        'matching_method': 'unique direct IPs, ports, protocol, and UTC minute; reference timestamps have minute resolution',
        'reference_timestamp_resolution': reference_timestamp_resolution,
        'timezone_conversion': 'generated local timestamps Asia/Kolkata converted to UTC; reference timestamps already UTC',
        'selected_windows_utc': selected_windows,
        'generated_flows': int(len(generated)),
        'generated_unique_direct_keys': int(len(generated_unique)),
        'reference_rows_in_selected_windows': int(len(reference_window)),
        'reference_unique_direct_keys_in_selected_windows': int(len(unique_keys(reference_window, keys))),
        'unique_direct_matches': int(len(matched)),
        'matched_label_counts': {str(k): int(v) for k, v in pd.Series(labels).value_counts().items()},
        'attack_family_match_coverage_in_selected_windows': family_coverage,
        'feature_parity': {
            'feature_cells_agree': int(feature_matrix.sum()),
            'feature_cells_compared': int(feature_matrix.size),
            'feature_cell_agreement': float(feature_matrix.mean()),
            'exact_core_rows': int(exact_core.sum()),
            'exact_core_fraction': float(exact_core.mean()),
            'complete_67_feature_rows': int(exact_full.sum()),
            'per_feature_agreement': {name: float(values.mean()) for name, values in feature_matches.items()},
            'flag_agreement_by_core_match': {
                'core_match_definition': CORE_FEATURES,
                'exact_core_rows': int(exact_core.sum()),
                'rows_with_core_mismatch': int((~exact_core).sum()),
                'per_flag': flag_agreement_by_core_match,
            },
            'flag_value_differences_when_core_fields_match': flag_value_differences,
            'feature_parity_verified': False,
        },
        'hybrid_v2_models_on_direct_matches': {
            'feature_count': len(model_features),
            'thresholds_previously_selected_without_friday_data': True,
            'detectors': detector_results,
            'by_attack_family': family_results,
        },
        'limitations': [
            'This evaluates only the selected Friday windows listed in the report, not full-day traffic.',
            'Only unique, directly oriented five-tuple plus UTC-minute matches are scored; reverse, ambiguous, and unmatched flows are excluded.',
            'The flow boundaries are produced by the experimental packet adapter and may not match the training generator.',
            'The exact CICFlowMeter version and CSV export path used by the training dataset are unidentified; experimental flag-count modes do not establish parity.',
            'This is the same CICIDS2017 benchmark, not an external capture.',
            'Research only; do not automate blocking or alert escalation.',
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({
        'generated_flows': report['generated_flows'],
        'direct_matches': report['unique_direct_matches'],
        'feature_cell_agreement': report['feature_parity']['feature_cell_agreement'],
        'exact_67_rows': report['feature_parity']['complete_67_feature_rows'],
        'family_match_coverage': family_coverage,
        'detectors': detector_results,
        'report': str(output_path),
    }, indent=2), flush=True)


if __name__ == '__main__':
    main()
