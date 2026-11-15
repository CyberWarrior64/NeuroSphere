from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from scapy.layers.inet import TCP, UDP
from scapy.sendrecv import AsyncSniffer

from app.feature_extraction.cicflowmeter_packet_compat import install_training_csv_reference_adapter
from app.feature_extraction.cicflowmeter_java_session import CICFlowMeterReferenceSession
from cicflowmeter.features.context import PacketDirection, get_packet_flow_key
from cicflowmeter.flow import Flow


class CurrentUpstreamFINSession(CICFlowMeterReferenceSession):
    """Candidate port of current upstream FlowGenerator FIN/RST handling."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._candidate_fin_counts: dict[tuple, list[int]] = {}

    def process(self, packet: Any):
        context = getattr(self, "_neurosphere_header_context", None)
        if context is None:
            context = {"last_tcp_header_bytes": 20}
            self._neurosphere_header_context = context
        packet._neurosphere_previous_tcp_header_bytes = context["last_tcp_header_bytes"]
        if TCP in packet:
            context["last_tcp_header_bytes"] = int(packet[TCP].dataofs or 5) * 4

        if TCP not in packet and UDP not in packet:
            return None

        self.packets_count += 1
        direction = PacketDirection.FORWARD
        packet_flow_key = get_packet_flow_key(packet, direction)
        flow_key = (packet_flow_key, 0)
        flow = self.flows.get(flow_key)

        if flow is None:
            direction = PacketDirection.REVERSE
            packet_flow_key = get_packet_flow_key(packet, direction)
            flow_key = (packet_flow_key, 0)
            flow = self.flows.get(flow_key)

        if flow is None:
            direction = PacketDirection.FORWARD
            packet_flow_key = get_packet_flow_key(packet, direction)
            flow_key = (packet_flow_key, 0)
            self.flows[flow_key] = Flow(packet, direction)
            self._candidate_fin_counts[flow_key] = [0, 0]
            return None

        elapsed = float(packet.time) - float(flow.start_timestamp)
        if elapsed > self.flow_timeout_seconds:
            self._write_and_remove(flow_key, flow)
            self._candidate_fin_counts.pop(flow_key, None)
            self.flows[flow_key] = Flow(packet, direction)
            self._candidate_fin_counts[flow_key] = [0, 0]
            return None

        fin_counts = self._candidate_fin_counts.setdefault(flow_key, [0, 0])
        if TCP in packet:
            flags = set(str(packet[TCP].flags))
            if "F" in flags:
                index = 0 if direction == PacketDirection.FORWARD else 1
                fin_counts[index] += 1
                if fin_counts[index] != 1:
                    return None
                flow.add_packet(packet, direction)
                # Current upstream checks the backward count twice.
                if direction == PacketDirection.REVERSE and 2 * fin_counts[1] == 2:
                    self._write_and_remove(flow_key, flow)
                    self._candidate_fin_counts.pop(flow_key, None)
                return None
            if "R" in flags:
                flow.add_packet(packet, direction)
                self._write_and_remove(flow_key, flow)
                self._candidate_fin_counts.pop(flow_key, None)
                return None

        if direction == PacketDirection.FORWARD and fin_counts[0] == 0:
            flow.add_packet(packet, direction)
        elif fin_counts[1] == 0:
            flow.add_packet(packet, direction)
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay a PCAP with either the calibrated session or current upstream FIN handling."
    )
    parser.add_argument("--pcap", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--boundary", choices=("current", "upstream"), default="upstream")
    args = parser.parse_args()

    install_training_csv_reference_adapter()
    session_class = (
        CurrentUpstreamFINSession
        if args.boundary == "upstream"
        else CICFlowMeterReferenceSession
    )
    session = session_class(
        output_mode="csv",
        output=str(args.output_csv),
        fields=None,
        verbose=False,
    )
    sniffer = AsyncSniffer(
        offline=str(args.pcap),
        filter="ip and (tcp or udp)",
        prn=session.process,
        store=False,
    )
    sniffer.start()
    sniffer.join()
    session.flush_flows()
    print(f"Wrote {args.boundary} boundary flows to {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

