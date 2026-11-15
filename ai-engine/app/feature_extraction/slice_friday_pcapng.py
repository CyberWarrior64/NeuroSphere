from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / 'datasets/reference_pcaps/friday-reference/Friday-WorkingHours.pcap'
DEFAULT_OUTPUT = ROOT / 'datasets/reference_pcaps/friday-reference/Friday-WorkingHours-attack-windows.pcapng'
WINDOWS_UTC = [
    ('Bot', '2017-07-07T12:28:00+00:00', '2017-07-07T14:12:00+00:00'),
    ('Bot', '2017-07-07T14:18:00+00:00', '2017-07-07T14:22:00+00:00'),
    ('Bot', '2017-07-07T14:28:00+00:00', '2017-07-07T14:32:00+00:00'),
    ('Bot', '2017-07-07T14:38:00+00:00', '2017-07-07T14:42:00+00:00'),
    ('Bot', '2017-07-07T14:48:00+00:00', '2017-07-07T14:52:00+00:00'),
    ('Bot', '2017-07-07T14:58:00+00:00', '2017-07-07T15:02:00+00:00'),
    ('Bot', '2017-07-07T15:08:00+00:00', '2017-07-07T15:12:00+00:00'),
    ('Bot', '2017-07-07T15:18:00+00:00', '2017-07-07T15:22:00+00:00'),
    ('Bot', '2017-07-07T15:28:00+00:00', '2017-07-07T15:32:00+00:00'),
    ('Bot', '2017-07-07T15:38:00+00:00', '2017-07-07T15:42:00+00:00'),
    ('Bot', '2017-07-07T15:48:00+00:00', '2017-07-07T15:52:00+00:00'),
    ('PortScan', '2017-07-07T15:58:00+00:00', '2017-07-07T16:03:00+00:00'),
    ('PortScan', '2017-07-07T16:48:00+00:00', '2017-07-07T17:13:00+00:00'),
    ('PortScan', '2017-07-07T17:48:00+00:00', '2017-07-07T18:31:00+00:00'),
    ('DDoS', '2017-07-07T18:54:00+00:00', '2017-07-07T19:18:00+00:00'),
]

CORE_WINDOWS_UTC = [
    ('Bot', '2017-07-07T13:18:00+00:00', '2017-07-07T14:04:00+00:00'),
    ('PortScan', '2017-07-07T17:48:00+00:00', '2017-07-07T18:12:00+00:00'),
]


def epoch(value: str) -> float:
    return dt.datetime.fromisoformat(value).timestamp()


def parse_options(block: bytes, endian: str) -> dict[int, bytes]:
    options = {}
    offset = 16
    stop = len(block) - 4
    while offset + 4 <= stop:
        code, length = struct.unpack_from(endian + 'HH', block, offset)
        offset += 4
        if code == 0:
            break
        value = block[offset:offset + length]
        options[code] = value
        offset += (length + 3) & ~3
    return options


def main() -> None:
    parser = argparse.ArgumentParser(description='Select Friday attack-time windows from a pcapng capture without decoding packet payloads.')
    parser.add_argument('--input', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--profile', choices=['attack-label-coverage', 'bot-portscan-core'], default='attack-label-coverage')
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix(args.output.suffix + '.part').exists():
        raise SystemExit(f'Refusing to overwrite output or partial file: {args.output}')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    partial = args.output.with_suffix(args.output.suffix + '.part')
    selected_windows = WINDOWS_UTC if args.profile == 'attack-label-coverage' else CORE_WINDOWS_UTC
    ranges = [(name, epoch(start), epoch(end)) for name, start, end in selected_windows]
    interface_resolutions: dict[int, float] = {}
    packets_seen = 0
    packets_written = 0
    by_window = {name: 0 for name, _, _ in ranges}
    block_count = 0
    endian = None

    with args.input.open('rb') as source, partial.open('wb') as target:
        first = source.read(12)
        if len(first) != 12 or first[:4] != bytes.fromhex('0a0d0d0a'):
            raise RuntimeError('Input is not a pcapng section header block.')
        if first[8:12] == bytes.fromhex('4d3c2b1a'):
            endian = '<'
        elif first[8:12] == bytes.fromhex('1a2b3c4d'):
            endian = '>'
        else:
            raise RuntimeError('Unsupported pcapng byte-order magic.')
        first_length = struct.unpack(endian + 'I', first[4:8])[0]
        if first_length < 28 or first_length % 4:
            raise RuntimeError(f'Invalid section header block size: {first_length}')
        first_block = first + source.read(first_length - 12)
        if len(first_block) != first_length or struct.unpack(endian + 'I', first_block[-4:])[0] != first_length:
            raise RuntimeError('Truncated or malformed pcapng section header.')
        target.write(first_block)
        block_count += 1

        while True:
            header = source.read(8)
            if not header:
                break
            if len(header) != 8:
                raise RuntimeError('Truncated pcapng block header.')
            block_type, block_length = struct.unpack(endian + 'II', header)
            if block_length < 12 or block_length % 4:
                raise RuntimeError(f'Invalid pcapng block size {block_length} at offset {source.tell() - 8}')
            rest = source.read(block_length - 8)
            if len(rest) != block_length - 8:
                raise RuntimeError('Truncated pcapng block body.')
            block = header + rest
            if struct.unpack(endian + 'I', block[-4:])[0] != block_length:
                raise RuntimeError('Pcapng block length trailer mismatch.')
            block_count += 1

            if block_type == 1:  # Interface Description Block
                interface_id = len(interface_resolutions)
                options = parse_options(block, endian)
                resolution = 1e-6
                raw = options.get(9)
                if raw:
                    value = raw[0]
                    resolution = (2.0 ** -(value & 0x7F)) if value & 0x80 else (10.0 ** -value)
                interface_resolutions[interface_id] = resolution
                target.write(block)
            elif block_type == 6:  # Enhanced Packet Block
                if len(block) < 32:
                    raise RuntimeError('Malformed Enhanced Packet Block.')
                interface_id, ts_high, ts_low, captured_len, _ = struct.unpack_from(endian + 'IIIII', block, 8)
                resolution = interface_resolutions.get(interface_id, 1e-6)
                packet_time = ((ts_high << 32) | ts_low) * resolution
                packets_seen += 1
                matched_window = None
                for name, start, end in ranges:
                    if start <= packet_time <= end:
                        matched_window = name
                        break
                if matched_window is not None:
                    target.write(block)
                    packets_written += 1
                    by_window[matched_window] += 1
                if packets_seen % 1_000_000 == 0:
                    print(f'Scanned {packets_seen:,} packets; selected {packets_written:,}.', flush=True)
            else:
                # Preserve non-packet metadata blocks; discard packet blocks outside the requested windows.
                target.write(block)

        target.flush()
        os.fsync(target.fileno())

    if packets_written == 0:
        raise RuntimeError('No packet timestamps fell inside the selected windows; partial output retained.')
    os.replace(partial, args.output)
    report = {
        'input': str(args.input.relative_to(ROOT)) if args.input.is_relative_to(ROOT) else str(args.input),
        'output': str(args.output.relative_to(ROOT)) if args.output.is_relative_to(ROOT) else str(args.output),
        'pcapng_byte_order': 'little' if endian == '<' else 'big',
        'packet_blocks_scanned': packets_seen,
        'packet_blocks_selected': packets_written,
        'selected_packet_fraction': packets_written / packets_seen if packets_seen else None,
        'packets_by_window': by_window,
        'profile': args.profile,
        'windows_utc': [{'name': name, 'start': start, 'end': end} for name, start, end in selected_windows],
        'output_bytes': args.output.stat().st_size,
    }
    report_path = args.output.with_suffix('.slice-report.json')
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
