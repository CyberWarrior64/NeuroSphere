from pathlib import Path
from zoneinfo import ZoneInfo
import json

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "datasets" / "reference_pcaps" / "friday-reference"
generated_path = DATA / "Friday-WorkingHours-attack-windows-reference-global-expiry.csv"
reference_path = DATA / "Friday-traffic-labels-combined.parquet"
windows_path = DATA / "Friday-WorkingHours-attack-windows.slice-report.json"
flags = [
    ("FIN Flag Count", "fin_flag_cnt"),
    ("SYN Flag Count", "syn_flag_cnt"),
    ("RST Flag Count", "rst_flag_cnt"),
    ("PSH Flag Count", "psh_flag_cnt"),
    ("ACK Flag Count", "ack_flag_cnt"),
    ("URG Flag Count", "urg_flag_cnt"),
    ("ECE Flag Count", "ece_flag_cnt"),
]
keys = ["src_ip", "dst_ip", "src_port", "dst_port", "protocol", "timestamp_minute"]
core = [
    ("Flow Duration", "flow_duration"),
    ("Total Fwd Packets", "tot_fwd_pkts"),
    ("Total Backward Packets", "tot_bwd_pkts"),
    ("Total Length of Fwd Packets", "totlen_fwd_pkts"),
    ("Total Length of Bwd Packets", "totlen_bwd_pkts"),
]


def unique_keys(frame: pd.DataFrame) -> pd.DataFrame:
    counts = frame.groupby(keys, dropna=False).size().rename("_key_count")
    unique = counts[counts == 1].reset_index()[keys]
    return frame.merge(unique, on=keys, how="inner", validate="many_to_one")


reference_columns = [
    "Timestamp", "Source IP", "Destination IP", "Source Port", "Destination Port", "Protocol",
    "Label", *(name for name, _ in core), *(name for name, _ in flags),
]
generated_columns = [
    "timestamp", "src_ip", "dst_ip", "src_port", "dst_port", "protocol",
    *(name for _, name in core), *(name for _, name in flags),
]
generated = pd.read_csv(generated_path, usecols=generated_columns)
reference = pd.read_parquet(reference_path, columns=reference_columns)

local_time = pd.to_datetime(generated["timestamp"], errors="raise")
if local_time.dt.tz is None:
    local_time = local_time.dt.tz_localize(ZoneInfo("Asia/Kolkata"))
generated["timestamp_minute"] = local_time.dt.tz_convert("UTC").dt.tz_localize(None).dt.floor("min")
ref_time = pd.to_datetime(reference["Timestamp"], errors="raise", utc=True)
reference["timestamp_minute"] = ref_time.dt.tz_localize(None).dt.floor("min")
windows = json.loads(windows_path.read_text())["windows_utc"]
in_windows = pd.Series(False, index=reference.index)
for window in windows:
    in_windows |= ref_time.between(pd.Timestamp(window["start"]), pd.Timestamp(window["end"]), inclusive="both")
reference = reference.loc[in_windows].copy()
reference = reference.rename(columns={
    "Source IP": "src_ip", "Destination IP": "dst_ip",
    "Source Port": "src_port", "Destination Port": "dst_port",
    "Protocol": "protocol",
})
for frame in (generated, reference):
    for port in ("src_port", "dst_port", "protocol"):
        frame[port] = pd.to_numeric(frame[port], errors="raise").astype("int64")

generated = unique_keys(generated)
reference = unique_keys(reference)
matched = generated.merge(reference, on=keys, how="inner", suffixes=("_generated", "_reference"), validate="one_to_one")
core_match = np.ones(len(matched), dtype=bool)
for reference_name, generated_name in core:
    left = pd.to_numeric(matched[generated_name], errors="coerce").to_numpy(dtype=float, copy=True)
    right = pd.to_numeric(matched[reference_name], errors="coerce").to_numpy(dtype=float, copy=True)
    if reference_name == "Flow Duration":
        left *= 1_000_000.0
    core_match &= np.isclose(left, right, rtol=1e-9, atol=1e-6, equal_nan=True)

print(f"matched={len(matched)}; exact_core={int(core_match.sum())}")
generated_flag_names = [generated_name for _, generated_name in flags]
reference_flag_names = [reference_name for reference_name, _ in flags]
agreement = np.zeros((len(generated_flag_names), len(reference_flag_names)), dtype=float)
for i, generated_name in enumerate(generated_flag_names):
    generated_values = pd.to_numeric(matched[generated_name], errors="coerce").to_numpy(dtype=float, copy=True)
    for j, reference_name in enumerate(reference_flag_names):
        reference_values = pd.to_numeric(matched[reference_name], errors="coerce").to_numpy(dtype=float, copy=True)
        valid = core_match & np.isfinite(generated_values) & np.isfinite(reference_values)
        agreement[i, j] = np.isclose(
            generated_values[valid], reference_values[valid], rtol=1e-9, atol=1e-6
        ).mean() if valid.any() else 0.0
assignment_rows, assignment_columns = linear_sum_assignment(-agreement)
print("\nCross-column exact agreement on exact-core rows (descriptive only):")
print(pd.DataFrame(agreement, index=generated_flag_names, columns=reference_flag_names).round(4).to_string())
print("Best one-to-one descriptive mapping:")
for i, j in zip(assignment_rows, assignment_columns):
    print(f"  {generated_flag_names[i]} -> {reference_flag_names[j]}: {agreement[i, j]:.4f}")

print("\nExact-value agreement only where either field is nonzero (avoids zero-dominated scores):")
nonzero_agreement = np.zeros_like(agreement)
indicator_agreement = np.zeros_like(agreement)
for i, generated_name in enumerate(generated_flag_names):
    left = pd.to_numeric(matched[generated_name], errors="coerce").to_numpy(dtype=float, copy=True)[core_match]
    for j, reference_name in enumerate(reference_flag_names):
        right = pd.to_numeric(matched[reference_name], errors="coerce").to_numpy(dtype=float, copy=True)[core_match]
        either_nonzero = (left != 0) | (right != 0)
        nonzero_agreement[i, j] = np.isclose(
            left[either_nonzero], right[either_nonzero], rtol=1e-9, atol=1e-6
        ).mean() if either_nonzero.any() else float("nan")
        indicator_agreement[i, j] = ((left != 0) == (right != 0)).mean() if len(left) else float("nan")
print("Nonzero-union exact agreement:")
print(pd.DataFrame(nonzero_agreement, index=generated_flag_names, columns=reference_flag_names).round(4).to_string())
print("Nonzero-indicator agreement:")
print(pd.DataFrame(indicator_agreement, index=generated_flag_names, columns=reference_flag_names).round(4).to_string())

for reference_name, generated_name in flags:
    left = pd.to_numeric(matched[generated_name], errors="coerce").to_numpy(dtype=float, copy=True)
    right = pd.to_numeric(matched[reference_name], errors="coerce").to_numpy(dtype=float, copy=True)
    subset_left, subset_right = left[core_match], right[core_match]
    pairs = pd.DataFrame({"generated": subset_left, "reference": subset_right})
    print(f"\n{reference_name}")
    print(f"generated_mean={subset_left.mean():.6f}; reference_mean={subset_right.mean():.6f}")
    print("pair_counts:")
    print(pairs.value_counts().head(12).to_string())
    print("reference_counts:")
    print(pd.Series(subset_right).value_counts().head(12).to_string())
