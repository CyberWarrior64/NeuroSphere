
from __future__ import annotations

import math
import statistics
from typing import Any

from cicflowmeter.features.context import PacketDirection
from scapy.layers.inet import TCP, UDP

REFERENCE_ADAPTER_ID = "cicflowmeter-python-0.5.0-training-csv-calibrated"
ACTIVITY_TIMEOUT_US = 5_000_000


def _transport(packet: Any) -> tuple[int, int, set[str], int]:
    """Return payload bytes, calibrated header bytes, flags, and TCP window."""
    if TCP in packet:
        layer = packet[TCP]
        payload_bytes = len(layer.payload)
        header_bytes = int(layer.dataofs or 5) * 4
        return payload_bytes, header_bytes, set(str(layer.flags)), int(layer.window or 0)
    if UDP in packet:
        layer = packet[UDP]
        payload_bytes = len(layer.payload)
        # The training-table match is best explained by its UDP packet reader
        # retaining the most recent TCP header length across packets.
        header_bytes = int(getattr(packet, "_neurosphere_previous_tcp_header_bytes", 20))
        return payload_bytes, header_bytes, set(), -1
    return 0, 0, set(), 0


def _stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"total": 0.0, "mean": 0.0, "std": 0.0, "variance": 0.0, "min": 0.0, "max": 0.0}
    return {
        "total": float(sum(values)),
        "mean": float(statistics.mean(values)),
        "std": float(statistics.stdev(values)) if len(values) > 1 else 0.0,
        "variance": float(statistics.variance(values)) if len(values) > 1 else 0.0,
        "min": float(min(values)),
        "max": float(max(values)),
    }


def training_csv_feature_overrides(
    flow: Any, *, flag_count_mode: str = "all_packets"
) -> dict[str, int | float | str]:
    """Recalculate selected fields using raw packets and training-table evidence.

    Source review informed the packet features, then a bounded comparison calibrated
    differences against CICIDS2017 training rows. The exact generator build is unknown;
    the measured agreement is partial and must not be treated as parity certification.
    """
    packet_items = list(flow.packets)
    if not packet_items:
        return {"_feature_extractor": REFERENCE_ADAPTER_ID}

    payloads: list[int] = []
    headers: list[int] = []
    flags_by_packet: list[set[str]] = []
    windows: list[int] = []
    directions: list[Any] = []
    timestamps_us: list[int] = []

    for packet, direction in packet_items:
        payload_bytes, header_bytes, flag_chars, tcp_window = _transport(packet)
        payloads.append(payload_bytes)
        headers.append(header_bytes)
        flags_by_packet.append(flag_chars)
        windows.append(tcp_window)
        directions.append(direction)
        timestamps_us.append(int(round(float(packet.time) * 1_000_000)))

    forward = [i for i, direction in enumerate(directions) if direction == PacketDirection.FORWARD]
    backward = [i for i, direction in enumerate(directions) if direction == PacketDirection.REVERSE]
    fwd_payloads = [payloads[i] for i in forward]
    bwd_payloads = [payloads[i] for i in backward]
    fwd_headers = [headers[i] for i in forward]
    bwd_headers = [headers[i] for i in backward]
    duration_us = max(0, timestamps_us[-1] - timestamps_us[0])
    duration_s = duration_us / 1_000_000.0

    flow_iats = [
        float(timestamps_us[i] - timestamps_us[i - 1])
        for i in range(1, len(timestamps_us))
    ]

    # The CICIDS2017 training CSV comparison shows that the first same-direction
    # gap is included, even though current upstream Java BasicFlow omits it.
    fwd_iats: list[float] = []
    bwd_iats: list[float] = []
    last_seen: dict[Any, int] = {}
    seen: dict[Any, int] = {PacketDirection.FORWARD: 0, PacketDirection.REVERSE: 0}
    for timestamp, direction in zip(timestamps_us, directions):
        if seen.get(direction, 0) > 0 and direction in last_seen:
            interval = float(timestamp - last_seen[direction])
            (fwd_iats if direction == PacketDirection.FORWARD else bwd_iats).append(interval)
        last_seen[direction] = timestamp
        seen[direction] = seen.get(direction, 0) + 1

    flow_stats = _stats(flow_iats)
    fwd_iat_stats = _stats(fwd_iats)
    bwd_iat_stats = _stats(bwd_iats)
    fwd_stats = _stats([float(x) for x in fwd_payloads])
    bwd_stats = _stats([float(x) for x in bwd_payloads])

    # The reviewed Java firstPacket() adds the initial payload to flowLengthStats
    # before and inside the direction branch, so the first value is counted twice.
    flow_lengths = [float(x) for x in payloads]
    if flow_lengths:
        flow_lengths.insert(0, flow_lengths[0])
    packet_stats = _stats(flow_lengths)
    packet_count = len(packet_items)
    fwd_count = len(forward)
    bwd_count = len(backward)
    total_payload = sum(payloads)
    # The labeled training CSV stores full per-flow packet/byte totals here;
    # this differs from current upstream Java, which divides by sfCount.

    flag_names = ("F", "S", "R", "P", "A", "U", "E", "C")
    if flag_count_mode == "all_packets":
        flag_counts = {
            flag: sum(1 for packet_flags in flags_by_packet if flag in packet_flags)
            for flag in flag_names
        }
    elif flag_count_mode == "first_packet":
        first_packet_flags = flags_by_packet[0]
        flag_counts = {flag: int(flag in first_packet_flags) for flag in flag_names}
    else:
        raise ValueError(f"Unsupported flag_count_mode: {flag_count_mode}")
    fwd_psh = sum(1 for i in forward if "P" in flags_by_packet[i])
    bwd_psh = sum(1 for i in backward if "P" in flags_by_packet[i])

    # The reference implementation initializes the forward window on the first
    # packet and updates the backward value on each reverse packet.
    init_fwd_window = windows[forward[0]] if forward else -1
    init_bwd_window = windows[backward[-1]] if backward else -1

    # Its active/idle updater runs before each subsequent packet with a 5 s
    # activity timeout. Finalization behavior can depend on how a flow closes.
    active_us: list[float] = []
    idle_us: list[float] = []
    start_active = timestamps_us[0]
    end_active = timestamps_us[0]
    for current in timestamps_us[1:]:
        if current - end_active > ACTIVITY_TIMEOUT_US:
            if end_active - start_active > 0:
                active_us.append(float(end_active - start_active))
            idle_us.append(float(current - end_active))
            start_active = current
            end_active = current
        else:
            end_active = current
    active_stats = _stats(active_us)
    idle_stats = _stats(idle_us)

    def seconds(value: float) -> float:
        return value / 1_000_000.0

    return {
        "flow_duration": seconds(float(duration_us)),
        "tot_fwd_pkts": fwd_count,
        "tot_bwd_pkts": bwd_count,
        "totlen_fwd_pkts": sum(fwd_payloads),
        "totlen_bwd_pkts": sum(bwd_payloads),
        "fwd_pkt_len_max": fwd_stats["max"],
        "fwd_pkt_len_min": fwd_stats["min"],
        "fwd_pkt_len_mean": fwd_stats["mean"],
        "fwd_pkt_len_std": fwd_stats["std"],
        "bwd_pkt_len_max": bwd_stats["max"],
        "bwd_pkt_len_min": bwd_stats["min"],
        "bwd_pkt_len_mean": bwd_stats["mean"],
        "bwd_pkt_len_std": bwd_stats["std"],
        "flow_byts_s": total_payload / duration_s if duration_s > 0 else 0.0,
        "flow_pkts_s": packet_count / duration_s if duration_s > 0 else 0.0,
        "flow_iat_mean": seconds(flow_stats["mean"]),
        "flow_iat_std": seconds(flow_stats["std"]),
        "flow_iat_max": seconds(flow_stats["max"]),
        "flow_iat_min": seconds(flow_stats["min"]),
        "fwd_iat_tot": seconds(fwd_iat_stats["total"]),
        "fwd_iat_mean": seconds(fwd_iat_stats["mean"]),
        "fwd_iat_std": seconds(fwd_iat_stats["std"]),
        "fwd_iat_max": seconds(fwd_iat_stats["max"]),
        "fwd_iat_min": seconds(fwd_iat_stats["min"]),
        "bwd_iat_tot": seconds(bwd_iat_stats["total"]),
        "bwd_iat_mean": seconds(bwd_iat_stats["mean"]),
        "bwd_iat_std": seconds(bwd_iat_stats["std"]),
        "bwd_iat_max": seconds(bwd_iat_stats["max"]),
        "bwd_iat_min": seconds(bwd_iat_stats["min"]),
        "fwd_psh_flags": fwd_psh,
        "fwd_header_len": sum(fwd_headers),
        "bwd_header_len": sum(bwd_headers),
        "fwd_pkts_s": fwd_count / duration_s if duration_s > 0 else 0.0,
        "bwd_pkts_s": bwd_count / duration_s if duration_s > 0 else 0.0,
        "pkt_len_min": packet_stats["min"],
        "pkt_len_max": packet_stats["max"],
        "pkt_len_mean": packet_stats["mean"],
        "pkt_len_std": packet_stats["std"],
        "pkt_len_var": packet_stats["variance"],
        "fin_flag_cnt": flag_counts["F"],
        "syn_flag_cnt": flag_counts["S"],
        "rst_flag_cnt": flag_counts["R"],
        "psh_flag_cnt": flag_counts["P"],
        "ack_flag_cnt": flag_counts["A"],
        "urg_flag_cnt": flag_counts["U"],
        "ece_flag_cnt": flag_counts["E"],
        "down_up_ratio": (bwd_count // fwd_count) if fwd_count else 0,
        "pkt_size_avg": packet_stats["total"] / packet_count if packet_count else 0.0,
        "fwd_seg_size_avg": fwd_stats["mean"],
        "bwd_seg_size_avg": bwd_stats["mean"],
        "subflow_fwd_pkts": fwd_count,
        "subflow_fwd_byts": sum(fwd_payloads),
        "subflow_bwd_pkts": bwd_count,
        "subflow_bwd_byts": sum(bwd_payloads),
        "init_fwd_win_byts": init_fwd_window,
        "init_bwd_win_byts": init_bwd_window,
        "fwd_act_data_pkts": sum(
            1 for i in forward if i != 0 and payloads[i] >= 1
        ),
        "fwd_seg_size_min": min(fwd_headers) if fwd_headers else 0,
        "active_mean": seconds(active_stats["mean"]),
        "active_std": seconds(active_stats["std"]),
        "active_max": seconds(active_stats["max"]),
        "active_min": seconds(active_stats["min"]),
        "idle_mean": seconds(idle_stats["mean"]),
        "idle_std": seconds(idle_stats["std"]),
        "idle_max": seconds(idle_stats["max"]),
        "idle_min": seconds(idle_stats["min"]),
        "fwd_urg_flags": sum(1 for i in forward if "U" in flags_by_packet[i]),
        "bwd_urg_flags": sum(1 for i in backward if "U" in flags_by_packet[i]),
        "bwd_psh_flags": bwd_psh,
        "_feature_extractor": REFERENCE_ADAPTER_ID,
    }


def install_training_csv_reference_adapter(*, flag_count_mode: str = "all_packets") -> None:
    """Patch flow output and packet context before starting a capture.

    first_packet is an offline research candidate for the historical
    CICFlowMeter behavior reported for the original CICIDS2017 CSVs.
    """
    if flag_count_mode not in {"all_packets", "first_packet"}:
        raise ValueError(f"Unsupported flag_count_mode: {flag_count_mode}")
    from cicflowmeter.flow import Flow
    from cicflowmeter.flow_session import FlowSession
    from app.feature_extraction.cicflowmeter_java_session import CICFlowMeterReferenceSession

    if not getattr(Flow, "_neurosphere_reference_adapter_installed", False):
        original_get_data = Flow.get_data

        def get_data_with_reference_features(self: Any, include_fields: Any = None) -> dict[str, Any]:
            record = original_get_data(self, include_fields=None)
            record.update(training_csv_feature_overrides(self, flag_count_mode=flag_count_mode))
            if include_fields is not None:
                allowed = set(include_fields)
                return {key: value for key, value in record.items()
                        if key in allowed or key == "_feature_extractor"}
            return record

        Flow.get_data = get_data_with_reference_features
        Flow._neurosphere_reference_adapter_installed = True

    for session_class in (FlowSession, CICFlowMeterReferenceSession):
        if session_class.__dict__.get("_neurosphere_header_context_installed", False):
            continue
        original_process = session_class.process

        def process_with_header_context(self: Any, packet: Any, _original=original_process):
            context = getattr(self, "_neurosphere_header_context", None)
            if context is None:
                context = {"last_tcp_header_bytes": 20}
                self._neurosphere_header_context = context
            packet._neurosphere_previous_tcp_header_bytes = context["last_tcp_header_bytes"]
            if TCP in packet:
                context["last_tcp_header_bytes"] = int(packet[TCP].dataofs or 5) * 4
            return _original(self, packet)

        session_class.process = process_with_header_context
        session_class._neurosphere_header_context_installed = True
