from __future__ import annotations

import argparse
import json
import sys
import threading
from decimal import Decimal

import requests

def _json_compatible(value):
    """Convert Decimal values from offline PCAP timestamps before HTTP JSON encoding."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(key): _json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_compatible(item) for item in value]
    return value


from app.feature_extraction.cicflowmeter_packet_compat import (
    install_training_csv_reference_adapter,
)
from app.feature_extraction.cicflowmeter_java_session import CICFlowMeterReferenceSession
from cicflowmeter.sniffer import create_sniffer
from scapy.sendrecv import AsyncSniffer


class PredictionWriter:
    """Post completed flow records and print compact model results."""

    def __init__(self, url: str, capture_mode: str) -> None:
        self.url = url
        self.capture_mode = capture_mode
        self._print_lock = threading.Lock()

    def write(self, data: dict) -> None:
        try:
            payload = _json_compatible(data)
            payload["_capture_mode"] = self.capture_mode
            response = requests.post(self.url, json=payload, timeout=5)
            response.raise_for_status()
            result = response.json()
            summary = {
                "input_source": result.get("input_source"),
                "capture_mode": result.get("capture_mode"),
                "packet_level_reference_features": result.get(
                    "packet_level_reference_features"
                ),
                "detection": result.get("detection"),
                "input_warnings": result.get("input_warnings"),
                "caution": result.get("caution"),
            }
            line = json.dumps(summary, ensure_ascii=False)
            with self._print_lock:
                print(line, flush=True)
        except Exception as exc:
            with self._print_lock:
                print(f"Prediction request failed: {exc}", file=sys.stderr, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Experimental live or offline capture with training-table-calibrated packet feature overrides."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("-i", "--interface", help="network interface to capture")
    input_group.add_argument("-f", "--file", help="offline PCAP/PCAPNG capture to process")
    parser.add_argument("-u", "--url", required=True, help="flow prediction endpoint URL")
    args = parser.parse_args()

    install_training_csv_reference_adapter()
    if args.file:
        session = CICFlowMeterReferenceSession(
            output_mode="url",
            output=args.url,
            fields=None,
            verbose=False,
        )
        sniffer = AsyncSniffer(
            offline=args.file,
            filter="ip and (tcp or udp)",
            prn=session.process,
            store=False,
        )
    else:
        sniffer, session = create_sniffer(
            input_file=None,
            input_interface=args.interface,
            output_mode="url",
            output=args.url,
            fields=None,
            verbose=False,
        )
    session.output_writer = PredictionWriter(args.url, "pcap" if args.file else "live")
    if args.file:
        print(f"Processing {args.file}; completed flows will be posted to {args.url}.")
    else:
        print(f"Capturing on {args.interface}; completed flows will be posted to {args.url}.")
    print("Each completed flow will print its experimental prediction. Press Ctrl+C to stop.")
    try:
        sniffer.start()
        sniffer.join()
    except KeyboardInterrupt:
        print("Stopping capture...", file=sys.stderr)
        try:
            sniffer.stop()
        except Exception:
            pass
    finally:
        stop_event = getattr(session, "_gc_stop", None)
        gc_thread = getattr(session, "_gc_thread", None)
        if stop_event is not None:
            stop_event.set()
        if gc_thread is not None:
            gc_thread.join(timeout=2.0)
        session.flush_flows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
