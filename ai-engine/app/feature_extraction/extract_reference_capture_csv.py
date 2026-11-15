from __future__ import annotations
import argparse
import csv
import os
import time
from pathlib import Path
from threading import Thread, Event

from scapy.sendrecv import AsyncSniffer

from app.feature_extraction.cicflowmeter_java_session import CICFlowMeterReferenceSession
from app.feature_extraction.cicflowmeter_packet_compat import install_training_csv_reference_adapter

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / 'datasets/reference_pcaps/friday-reference/Friday-WorkingHours.pcap'
DEFAULT_OUTPUT = ROOT / 'datasets/reference_pcaps/friday-reference/Friday-WorkingHours-reference-java-port.csv'


class BufferedCSVWriter:
    def __init__(self, path: Path, flush_rows: int = 5000):
        self.file = path.open('w', newline='')
        self.writer = csv.writer(self.file)
        self.flush_rows = max(1, flush_rows)
        self.rows = 0
        self._header_written = False

    def write(self, data: dict) -> None:
        if not self._header_written:
            self.writer.writerow(data.keys())
            self._header_written = True
        self.writer.writerow(data.values())
        self.rows += 1
        if self.rows % self.flush_rows == 0:
            self.file.flush()

    def close(self) -> None:
        if not self.file.closed:
            self.file.flush()
            self.file.close()

    def __del__(self):
        self.close()


class ProgressSession(CICFlowMeterReferenceSession):
    def process(self, packet):
        result = super().process(packet)
        count = self.packets_count
        if count and count % 100_000 == 0:
            writer = getattr(self, 'output_writer', None)
            rows = getattr(writer, 'rows', 0)
            print(f'Processed {count:,} IP TCP/UDP packets; emitted {rows:,} flows.', flush=True)
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description='Extract Friday PCAP flows with the experimental Java-reference port.')
    parser.add_argument('--input', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--flush-rows', type=int, default=5000)
    parser.add_argument(
        '--flag-count-mode', choices=('all_packets', 'first_packet'), default='all_packets',
        help='Experimental first-packet mode reproduces the historical CICIDS2017 flag-count bug.',
    )
    parser.add_argument('--bpf-filter', default='ip and (tcp or udp)', help='libpcap filter applied before Scapy decoding')
    args = parser.parse_args()
    if not args.input.is_file():
        raise SystemExit(f'Input capture not found: {args.input}')
    if args.output.exists() or args.output.with_suffix(args.output.suffix + '.part').exists():
        raise SystemExit(f'Refusing to overwrite output or partial file: {args.output}')

    output_part = args.output.with_suffix(args.output.suffix + '.part')
    output_part.parent.mkdir(parents=True, exist_ok=True)
    install_training_csv_reference_adapter(flag_count_mode=args.flag_count_mode)
    session = ProgressSession(output_mode='csv', output=str(output_part), fields=None, verbose=False)
    session.output_writer.file.close()
    writer = BufferedCSVWriter(output_part, args.flush_rows)
    session.output_writer = writer
    sniffer = AsyncSniffer(
        offline=str(args.input),
        filter=args.bpf_filter,
        prn=session.process,
        store=False,
    )
    started = time.monotonic()
    print(f'Processing {args.input} to {output_part} with BPF {args.bpf_filter!r}; no per-flow API requests will be sent.', flush=True)
    try:
        sniffer.start()
        sniffer.join()
    finally:
        session.flush_flows()
        writer.close()
    os.replace(output_part, args.output)
    elapsed = time.monotonic() - started
    print(f'Finished: {session.packets_count:,} IP TCP/UDP packets, {writer.rows:,} flows, {elapsed:.1f} seconds.', flush=True)
    print(f'CSV: {args.output} ({args.output.stat().st_size:,} bytes)', flush=True)


if __name__ == '__main__':
    main()
