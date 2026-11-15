from __future__ import annotations

import math
from typing import Any, Mapping

# Maps CICFlowMeter Python 0.5.0 field names to the trained model's exact schema.
MODEL_TO_CICFLOWMETER = {
    "Destination Port": "dst_port",
    "Flow Duration": "flow_duration",
    "Total Fwd Packets": "tot_fwd_pkts",
    "Total Backward Packets": "tot_bwd_pkts",
    "Total Length of Fwd Packets": "totlen_fwd_pkts",
    "Total Length of Bwd Packets": "totlen_bwd_pkts",
    "Fwd Packet Length Max": "fwd_pkt_len_max",
    "Fwd Packet Length Min": "fwd_pkt_len_min",
    "Fwd Packet Length Mean": "fwd_pkt_len_mean",
    "Fwd Packet Length Std": "fwd_pkt_len_std",
    "Bwd Packet Length Max": "bwd_pkt_len_max",
    "Bwd Packet Length Min": "bwd_pkt_len_min",
    "Bwd Packet Length Mean": "bwd_pkt_len_mean",
    "Bwd Packet Length Std": "bwd_pkt_len_std",
    "Flow Bytes/s": "flow_byts_s",
    "Flow Packets/s": "flow_pkts_s",
    "Flow IAT Mean": "flow_iat_mean",
    "Flow IAT Std": "flow_iat_std",
    "Flow IAT Max": "flow_iat_max",
    "Flow IAT Min": "flow_iat_min",
    "Fwd IAT Total": "fwd_iat_tot",
    "Fwd IAT Mean": "fwd_iat_mean",
    "Fwd IAT Std": "fwd_iat_std",
    "Fwd IAT Max": "fwd_iat_max",
    "Fwd IAT Min": "fwd_iat_min",
    "Bwd IAT Total": "bwd_iat_tot",
    "Bwd IAT Mean": "bwd_iat_mean",
    "Bwd IAT Std": "bwd_iat_std",
    "Bwd IAT Max": "bwd_iat_max",
    "Bwd IAT Min": "bwd_iat_min",
    "Fwd PSH Flags": "fwd_psh_flags",
    "Fwd Header Length": "fwd_header_len",
    "Bwd Header Length": "bwd_header_len",
    "Fwd Packets/s": "fwd_pkts_s",
    "Bwd Packets/s": "bwd_pkts_s",
    "Min Packet Length": "pkt_len_min",
    "Max Packet Length": "pkt_len_max",
    "Packet Length Mean": "pkt_len_mean",
    "Packet Length Std": "pkt_len_std",
    "Packet Length Variance": "pkt_len_var",
    "FIN Flag Count": "fin_flag_cnt",
    "SYN Flag Count": "syn_flag_cnt",
    "RST Flag Count": "rst_flag_cnt",
    "PSH Flag Count": "psh_flag_cnt",
    "ACK Flag Count": "ack_flag_cnt",
    "URG Flag Count": "urg_flag_cnt",
    "ECE Flag Count": "ece_flag_cnt",
    "Down/Up Ratio": "down_up_ratio",
    "Average Packet Size": "pkt_size_avg",
    "Avg Fwd Segment Size": "fwd_seg_size_avg",
    "Avg Bwd Segment Size": "bwd_seg_size_avg",
    "Subflow Fwd Packets": "subflow_fwd_pkts",
    "Subflow Fwd Bytes": "subflow_fwd_byts",
    "Subflow Bwd Packets": "subflow_bwd_pkts",
    "Subflow Bwd Bytes": "subflow_bwd_byts",
    "Init_Win_bytes_forward": "init_fwd_win_byts",
    "Init_Win_bytes_backward": "init_bwd_win_byts",
    "act_data_pkt_fwd": "fwd_act_data_pkts",
    "min_seg_size_forward": "fwd_seg_size_min",
    "Active Mean": "active_mean",
    "Active Std": "active_std",
    "Active Max": "active_max",
    "Active Min": "active_min",
    "Idle Mean": "idle_mean",
    "Idle Std": "idle_std",
    "Idle Max": "idle_max",
    "Idle Min": "idle_min",
}

TIME_FEATURES = {
    "Flow Duration",
    "Flow IAT Mean", "Flow IAT Std", "Flow IAT Max", "Flow IAT Min",
    "Fwd IAT Total", "Fwd IAT Mean", "Fwd IAT Std", "Fwd IAT Max", "Fwd IAT Min",
    "Bwd IAT Total", "Bwd IAT Mean", "Bwd IAT Std", "Bwd IAT Max", "Bwd IAT Min",
    "Active Mean", "Active Std", "Active Max", "Active Min",
    "Idle Mean", "Idle Std", "Idle Max", "Idle Min",
}

NONNEGATIVE_FEATURES = {
    "Flow Duration", "Fwd Header Length", "Bwd Header Length", "min_seg_size_forward",
}

FEATURE_PARITY_WARNING = (
    "Empirical comparison against a bounded CICIDS2017 Monday sample found 92.17% feature-cell agreement across 5,831 unique direct flow matches; 4,547 flows matched all 67 features. "
    "Feature parity remains unverified. In the 100,000-packet sample, agreement rose to 99.62% of feature cells when restricted to rows with matching core flow fields; exact flow generation remains unresolved."
)

FEATURE_PARITY_AUDIT = {
    "scope": "Source-code review plus empirical comparison with CICIDS2017 training reference features. This is partial evidence, not parity certification.",
    "feature_parity_verified": False,
    "empirical_comparison": {
        "sample_capture": "Monday-WorkingHours.pcap, first 100,000 packets",
        "sample_sha256": "8976cdcf7f34f525c972f94802b2f4e4d0c170fb67b29cd1fb030851094d63d8",
        "training_reference": "Monday-WorkingHours.pcap_ISCX.csv, cross-checked against Monday-WorkingHours.traffic_labels.parquet",
        "unique_direct_flow_matches": 5831,
        "feature_cells_matching": 360069,
        "feature_cells_compared": 390677,
        "feature_cell_agreement": 0.921654,
        "complete_67_feature_vectors": 4547,
        "exact_core_rows": 4899,
        "exact_core_row_fraction": 0.840165,
        "feature_cell_agreement_within_exact_core": 0.996210,
        "complete_vector_rate_within_exact_core": 0.928149,
        "matching_method": "Unique directed source/destination addresses, ports, protocol, and flow-start timestamp rounded to one second. Ambiguous keys and reverse-orientation matches are excluded. Adapter time features are converted from seconds to the training table's microseconds before comparison.",
        "tolerance": {"relative": 1e-9, "absolute": 1e-6},
        "group_agreement": {
            "header_fields": 0.9230,
            "directional_iat": 0.9289,
            "flow_iat": 0.9072,
            "subflow_fields": 0.9142,
            "initial_window_fields": 0.9823,
            "active_idle_fields": 0.9680,
            "payload_totals": 0.9233,
        },
    },
    "candidate_direct_fields": [
        "Destination Port", "Total Fwd Packets", "Total Backward Packets",
        "Fwd PSH Flags", "FIN Flag Count", "SYN Flag Count", "RST Flag Count",
        "PSH Flag Count", "ACK Flag Count", "URG Flag Count", "ECE Flag Count",
        "Init_Win_bytes_forward", "Init_Win_bytes_backward", "act_data_pkt_fwd",
        "Flow Packets/s", "Fwd Packets/s", "Bwd Packets/s",
    ],
    "known_or_unverified_differences": [
        {
            "group": "TCP flag count semantics",
            "features": [
                "FIN Flag Count", "SYN Flag Count", "RST Flag Count", "PSH Flag Count",
                "ACK Flag Count", "URG Flag Count", "ECE Flag Count",
            ],
            "observed": "An independent CICIDS2017 study reports that the original generator counted TCP flags only on a flow's first packet, leaving the original training CSV fields binary. An opt-in first-packet candidate raised Monday sample feature-cell agreement from 92.17% to 92.73% and complete 67-feature rows from 4,547 to 4,562; exact-core row count remained 4,899. On a two-window Friday Bot/PortScan core sample, first-packet counts plus a legacy-order-informed flag mapping reached 97.17% feature-cell agreement and 186,815 exact 67-feature rows across 203,007 unique matches (190,862 exact core). The candidate changes only aggregate flag counts; direction-specific PSH/URG fields remain on existing calculations.",
            "status": "Candidate mode is experimental and not active in the live mapper. The full Friday-window evaluation, including DDoS, is in progress; directional flag behavior and the exact CICFlowMeter build remain unknown.",
        },
        {
            "group": "Header lengths",
            "features": ["Fwd Header Length", "Bwd Header Length", "min_seg_size_forward"],
            "observed": "The best tested header candidate carries the preceding TCP header length into UDP fields; this is an empirical inference. It reached 92.30% agreement (92.39% forward header, 86.14% backward header, 98.37% minimum segment size) on the 100,000-packet comparison.",
            "status": "Empirically improved; exact training-reader semantics remain unidentified.",
        },
        {
            "group": "Inter-arrival times",
            "features": [
                "Flow IAT Mean", "Flow IAT Std", "Flow IAT Max", "Flow IAT Min",
                "Fwd IAT Total", "Fwd IAT Mean", "Fwd IAT Std", "Fwd IAT Max", "Fwd IAT Min",
                "Bwd IAT Total", "Bwd IAT Mean", "Bwd IAT Std", "Bwd IAT Max", "Bwd IAT Min",
            ],
            "observed": "Including the first same-direction interval raised agreement from 75.22% to 84.37% before the subflow/window adjustments. Directional IAT agreement is 92.89% on the 100,000-packet comparison; whole-flow IAT agreement is 90.72%.",
            "status": "Empirically calibrated on this sample; exact release and broader captures remain unverified.",
        },
        {
            "group": "Subflow features",
            "features": ["Subflow Fwd Packets", "Subflow Fwd Bytes", "Subflow Bwd Packets", "Subflow Bwd Bytes"],
            "observed": "The training table stores full per-direction flow totals in these fields for the matched sample. The adapter therefore uses undivided counts and payload totals; current upstream Java BasicFlow divides by sfCount.",
            "status": "Training-table behavior used; exact generator build remains unknown.",
        },
        {
            "group": "Initial window fields",
            "features": ["Init_Win_bytes_forward", "Init_Win_bytes_backward"],
            "observed": "The matched training rows use -1 for UDP windows. The adapter now emits this sentinel; TCP backward window behavior uses the last reverse packet, matching the best observed candidate.",
            "status": "98.23% agreement on the 100,000-packet comparison; remaining TCP differences unresolved.",
        },
        {
            "group": "Flow boundaries and timing",
            "features": ["Flow Duration", "Flow Packets/s", "Flow Bytes/s", "Active Mean", "Idle Mean"],
            "observed": "Core duration, packet counts, and directional payload totals matched on 4,899 of 5,831 direct flow matches. Within those, 4,547 (92.81%) also matched all 67 fields, and cell agreement was 99.62%. This points to flow segmentation and closure as major contributors to the remaining mismatch, but that explanation has not been proven.",
            "status": "Partially compared; exact generator release and full-capture parity unverified.",
        },
        {
            "group": "Independent prediction quality",
            "features": [],
            "observed": "The Monday capture is benign training-source traffic, not an independent attack holdout. Single-flow calibration and generalization are not measured.",
            "status": "Unverified; research use only.",
        },
    ],
    "reviewed_sources": [
        "https://github.com/ahlashkari/CICFlowMeter/blob/master/src/main/java/cic/cs/unb/ca/jnetpcap/BasicFlow.java",
        "https://github.com/ahlashkari/CICFlowMeter/blob/master/src/main/java/cic/cs/unb/ca/jnetpcap/PacketReader.java",
        "https://github.com/ahlashkari/CICFlowMeter/issues/60",
        "https://intrusion-detection.distrinet-research.be/WTMC2021/extended_doc.html#tcp-flag-count",
    ],
}


def map_cicflowmeter_record(record: Mapping[str, Any]) -> tuple[dict[str, float | None], list[str]]:
    """Map one CICFlowMeter Python output dict into the trained 67-feature schema.

    The package reports its packet times in seconds; CICIDS2017 model time
    features use microseconds. Rates are already per second and are unchanged.
    """
    missing = sorted(set(MODEL_TO_CICFLOWMETER.values()) - set(record))
    if missing:
        raise ValueError(f"CICFlowMeter record is missing fields: {missing}")

    mapped: dict[str, float | None] = {}
    negative_as_missing: list[str] = []
    for model_name, source_name in MODEL_TO_CICFLOWMETER.items():
        raw = record[source_name]
        if raw is None:
            mapped[model_name] = None
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"CICFlowMeter field '{source_name}' is not numeric.") from exc
        if not math.isfinite(value):
            mapped[model_name] = None
            continue
        if model_name in NONNEGATIVE_FEATURES and value < 0:
            mapped[model_name] = None
            negative_as_missing.append(model_name)
            continue
        if model_name in TIME_FEATURES:
            value *= 1_000_000.0
        mapped[model_name] = value

    return mapped, negative_as_missing
