from __future__ import annotations

import argparse
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from app.feature_extraction.cicflowmeter_mapper import MODEL_TO_CICFLOWMETER, TIME_FEATURES


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_GENERATED = BASE_DIR / "datasets/reference_pcaps/Monday-first-100000-reference-header-calibrated.csv"
DEFAULT_REFERENCE = BASE_DIR / "datasets/reference_pcaps/Monday-WorkingHours.traffic_labels.parquet"
DEFAULT_OUTPUT = BASE_DIR / "datasets/reference_pcaps/Monday-first-100000-feature-parity.json"
KEYS = ["src_ip", "dst_ip", "src_port", "dst_port", "protocol", "timestamp_second"]
GROUPS = {
    "header_fields": ["Fwd Header Length", "Bwd Header Length", "min_seg_size_forward"],
    "directional_iat": [
        "Fwd IAT Total", "Fwd IAT Mean", "Fwd IAT Std", "Fwd IAT Max", "Fwd IAT Min",
        "Bwd IAT Total", "Bwd IAT Mean", "Bwd IAT Std", "Bwd IAT Max", "Bwd IAT Min",
    ],
    "flow_iat": ["Flow IAT Mean", "Flow IAT Std", "Flow IAT Max", "Flow IAT Min"],
    "subflow_fields": ["Subflow Fwd Packets", "Subflow Fwd Bytes", "Subflow Bwd Packets", "Subflow Bwd Bytes"],
    "initial_window_fields": ["Init_Win_bytes_forward", "Init_Win_bytes_backward"],
    "active_idle_fields": ["Active Mean", "Active Std", "Active Max", "Active Min", "Idle Mean", "Idle Std", "Idle Max", "Idle Min"],
    "payload_totals": ["Total Length of Fwd Packets", "Total Length of Bwd Packets"],
}
CORE_FEATURES = [
    "Flow Duration", "Total Fwd Packets", "Total Backward Packets",
    "Total Length of Fwd Packets", "Total Length of Bwd Packets",
]


def _unique_keys(frame: pd.DataFrame) -> pd.DataFrame:
    counts = frame.groupby(KEYS, dropna=False).size().rename("_key_count")
    unique = counts[counts == 1].reset_index()[KEYS]
    return frame.merge(unique, on=KEYS, how="inner", validate="many_to_one")


def compare(generated_path: Path, reference_path: Path, capture_timezone: str) -> dict:
    generated = pd.read_csv(generated_path)
    reference = pd.read_parquet(reference_path)

    local_time = pd.to_datetime(generated["timestamp"], errors="raise")
    if local_time.dt.tz is None:
        local_time = local_time.dt.tz_localize(ZoneInfo(capture_timezone))
    generated["timestamp_second"] = (
        local_time.dt.tz_convert("UTC").dt.tz_localize(None).dt.floor("s")
    )
    reference["timestamp_second"] = (
        pd.to_datetime(reference["Timestamp"], errors="raise", utc=True)
        .dt.tz_localize(None)
        .dt.floor("s")
    )

    generated = generated.rename(columns={
        "src_ip": "src_ip", "dst_ip": "dst_ip", "src_port": "src_port",
        "dst_port": "dst_port", "protocol": "protocol",
    })
    reference = reference.rename(columns={
        "Source IP": "src_ip", "Destination IP": "dst_ip",
        "Source Port": "src_port", "Destination Port": "dst_port",
        "Protocol": "protocol",
    })
    for frame in (generated, reference):
        frame["src_port"] = pd.to_numeric(frame["src_port"], errors="raise").astype("int64")
        frame["dst_port"] = pd.to_numeric(frame["dst_port"], errors="raise").astype("int64")
        frame["protocol"] = pd.to_numeric(frame["protocol"], errors="raise").astype("int64")

    generated_unique = _unique_keys(generated)
    reference_unique = _unique_keys(reference)
    matched = generated_unique.merge(
        reference_unique, on=KEYS, how="inner", suffixes=("_generated", "_reference"),
        validate="one_to_one",
    )
    if matched.empty:
        raise ValueError("No unique directly oriented flows matched the reference table.")

    feature_matches: dict[str, np.ndarray] = {}
    for feature, generated_column in MODEL_TO_CICFLOWMETER.items():
        actual = pd.to_numeric(matched[generated_column], errors="coerce")
        reference_column = "dst_port" if feature == "Destination Port" else feature
        expected = pd.to_numeric(matched[reference_column], errors="coerce")
        if feature in TIME_FEATURES:
            actual = actual * 1_000_000.0
        feature_matches[feature] = np.isclose(
            actual.to_numpy(), expected.to_numpy(), rtol=1e-9, atol=1e-6, equal_nan=True
        )

    matrix = np.column_stack(list(feature_matches.values()))
    core_matrix = np.column_stack([feature_matches[name] for name in CORE_FEATURES])
    exact_core_mask = core_matrix.all(axis=1)
    full_vector_mask = matrix.all(axis=1)
    feature_cell_matches = int(matrix.sum())
    feature_cell_count = int(matrix.size)
    exact_core_rows = int(exact_core_mask.sum())
    full_vectors_with_exact_core = int((full_vector_mask & exact_core_mask).sum())
    exact_core_comparison = {
        "rows": exact_core_rows,
        "row_fraction": exact_core_rows / len(matched),
        "complete_67_feature_rows": full_vectors_with_exact_core,
        "complete_vector_rate_within_core_exact": (
            full_vectors_with_exact_core / exact_core_rows if exact_core_rows else None
        ),
        "feature_cell_agreement": (
            float(matrix[exact_core_mask].mean()) if exact_core_rows else None
        ),
        "per_feature_agreement": {
            name: float(values[exact_core_mask].mean()) if exact_core_rows else None
            for name, values in feature_matches.items()
        },
    }
    group_agreement = {
        group: float(np.column_stack([feature_matches[name] for name in names]).mean())
        for group, names in GROUPS.items()
    }
    per_feature = {
        name: float(values.mean()) for name, values in feature_matches.items()
    }

    return {
        "sample": {
            "generated_csv": str(generated_path.relative_to(BASE_DIR)) if generated_path.is_relative_to(BASE_DIR) else str(generated_path),
            "capture_timezone": capture_timezone,
            "rows": int(len(generated)),
        },
        "reference": {
            "training_labels_parquet": str(reference_path.relative_to(BASE_DIR)) if reference_path.is_relative_to(BASE_DIR) else str(reference_path),
            "rows": int(len(reference)),
        },
        "matching": {
            "method": "unique directed addresses, ports, protocol, and start timestamp rounded to one second",
            "unique_direct_matches": int(len(matched)),
            "ambiguous_keys_excluded": True,
            "reverse_orientation_matches_excluded": True,
        },
        "comparison": {
            "relative_tolerance": 1e-9,
            "absolute_tolerance": 1e-6,
            "time_unit_conversion": "generated seconds converted to training-table microseconds",
            "feature_cells_matching": feature_cell_matches,
            "feature_cells_compared": feature_cell_count,
            "feature_cell_agreement": feature_cell_matches / feature_cell_count,
            "complete_67_feature_vectors": int(full_vector_mask.sum()),
            "exact_core_rows": exact_core_rows,
            "exact_core_comparison": exact_core_comparison,
            "group_agreement": group_agreement,
            "per_feature_agreement": per_feature,
        },
        "feature_parity_verified": False,
        "limitations": [
            "This comparison uses model training-source traffic and does not measure independent-capture generalization.",
            "Only unique direct flow keys are compared; ambiguous and reverse-orientation flows are excluded.",
            "The exact CICFlowMeter release and full flow-boundary parity are not established.",
            "This comparison does not measure attack detection quality or independent-capture generalization.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare packet-derived flow features with the CICIDS2017 training reference.")
    parser.add_argument("--generated-csv", type=Path, default=DEFAULT_GENERATED)
    parser.add_argument("--reference-parquet", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--capture-timezone", default="Asia/Kolkata")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = compare(args.generated_csv, args.reference_parquet, args.capture_timezone)
    output = args.output if args.output.is_absolute() else BASE_DIR / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    summary = report["comparison"]
    print(json.dumps({
        "unique_direct_matches": report["matching"]["unique_direct_matches"],
        "feature_cell_agreement": summary["feature_cell_agreement"],
        "complete_67_feature_vectors": summary["complete_67_feature_vectors"],
        "exact_core_rows": summary["exact_core_rows"],
        "complete_vector_rate_within_core_exact": summary["exact_core_comparison"]["complete_vector_rate_within_core_exact"],
        "report": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
