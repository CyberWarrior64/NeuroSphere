"""Offline flow session using the reviewed CICFlowMeter Java boundary rules.

This is a source-level port for controlled PCAP evaluation. It does not prove
that the exact CICFlowMeter release used to produce CICIDS2017 is identical.
"""
from __future__ import annotations

from typing import Any
import heapq

from cicflowmeter.features.context import PacketDirection, get_packet_flow_key
from cicflowmeter.flow import Flow
from cicflowmeter.flow_session import FlowSession
from scapy.layers.inet import TCP, UDP


JAVA_FLOW_TIMEOUT_SECONDS = 120.0


class CICFlowMeterReferenceSession(FlowSession):
    """Collect offline flows with an absolute 120-second lifetime.

    Java FlowGenerator checks flow age before adding a new packet. FIN state is
    cached per flow so repeated checks do not rescan the full packet history.
    """

    def __init__(self, *args: Any, flow_timeout_seconds: float = JAVA_FLOW_TIMEOUT_SECONDS, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.flow_timeout_seconds = float(flow_timeout_seconds)
        self._fin_seen_by_flow: dict[tuple, set[PacketDirection]] = {}
        self._expiry_heap: list[tuple[float, int, tuple]] = []
        self._expiry_by_flow: dict[tuple, tuple[float, int]] = {}
        self._expiry_sequence = 0
        self._latest_packet_timestamp: float | None = None

    @staticmethod
    def _packet_has_fin(packet: Any) -> bool:
        return TCP in packet and "F" in str(packet[TCP].flags)

    def _write_and_remove(self, key: tuple, flow: Flow) -> None:
        if len(flow.packets) > 1:
            self.output_writer.write(flow.get_data(self.fields))
        self.flows.pop(key, None)
        self._fin_seen_by_flow.pop(key, None)
        self._expiry_by_flow.pop(key, None)

    def _register_expiry(self, key: tuple, flow: Flow) -> None:
        expires_at = float(flow.start_timestamp) + self.flow_timeout_seconds
        self._expiry_sequence += 1
        token = (expires_at, self._expiry_sequence)
        self._expiry_by_flow[key] = token
        heapq.heappush(self._expiry_heap, (expires_at, self._expiry_sequence, key))

    def _expire_old_flows(self, timestamp: float) -> None:
        while self._expiry_heap and self._expiry_heap[0][0] < timestamp:
            expires_at, sequence, key = heapq.heappop(self._expiry_heap)
            if self._expiry_by_flow.get(key) != (expires_at, sequence):
                continue
            flow = self.flows.get(key)
            if flow is not None:
                self._write_and_remove(key, flow)

    def process(self, packet: Any):
        if TCP not in packet and UDP not in packet:
            return None

        self.packets_count += 1
        packet_timestamp = float(packet.time)
        if self._latest_packet_timestamp is None or packet_timestamp > self._latest_packet_timestamp:
            self._latest_packet_timestamp = packet_timestamp
        self._expire_old_flows(self._latest_packet_timestamp)
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
            self._fin_seen_by_flow[flow_key] = (
                {direction} if self._packet_has_fin(packet) else set()
            )
            self._register_expiry(flow_key, self.flows[flow_key])
            return None

        elapsed = float(packet.time) - float(flow.start_timestamp)
        if elapsed > self.flow_timeout_seconds:
            self._write_and_remove(flow_key, flow)
            self.flows[flow_key] = Flow(packet, direction)
            self._fin_seen_by_flow[flow_key] = (
                {direction} if self._packet_has_fin(packet) else set()
            )
            self._register_expiry(flow_key, self.flows[flow_key])
            return None

        fin_seen = self._fin_seen_by_flow.setdefault(flow_key, set())
        if TCP in packet:
            flags = set(str(packet[TCP].flags))
            if "F" in flags:
                if direction in fin_seen:
                    return None
                flow.add_packet(packet, direction)
                fin_seen.add(direction)
                if (
                    PacketDirection.FORWARD in fin_seen
                    and PacketDirection.REVERSE in fin_seen
                ):
                    self._write_and_remove(flow_key, flow)
                return None
            if "R" in flags:
                flow.add_packet(packet, direction)
                self._write_and_remove(flow_key, flow)
                return None
            if direction in fin_seen:
                return None

        flow.add_packet(packet, direction)
        return None

    def flush_flows(self) -> None:
        items = list(self.flows.items())
        self.flows.clear()
        self._fin_seen_by_flow.clear()
        self._expiry_heap.clear()
        self._expiry_by_flow.clear()
        for _, flow in items:
            if len(flow.packets) > 1:
                self.output_writer.write(flow.get_data(self.fields))
        try:
            del self.output_writer
        except Exception:
            pass

