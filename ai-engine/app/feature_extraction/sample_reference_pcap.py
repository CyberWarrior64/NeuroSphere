from __future__ import annotations

import argparse
import json
import mmap
import struct
from pathlib import Path


PCAP_MAGIC_ENDIAN = {
    b"\xd4\xc3\xb2\xa1": "<",
    b"\xa1\xb2\xc3\xd4": ">",
    b"\x4d\x3c\xb2\xa1": "<",
    b"\xa1\xb2\x3c\x4d": ">",
}
PCAPNG_MAGIC = b"\x0a\x0d\x0d\x0a"
PCAPNG_BOM_ENDIAN = {
    b"\x4d\x3c\x2b\x1a": "<",
    b"\x1a\x2b\x3c\x4d": ">",
}
PCAPNG_SHB = 0x0A0D0D0A
PCAPNG_IDB = 0x00000001
PCAPNG_PACKET_BLOCKS = {0x00000002, 0x00000006}


def _scan_classic(mapped: mmap.mmap, endian: str) -> tuple[int, list[bytes]]:
    offset = 24
    packets = 0
    while offset + 16 <= len(mapped):
        _, _, included, _ = struct.unpack_from(endian + "IIII", mapped, offset)
        next_offset = offset + 16 + included
        if included > 16 * 1024 * 1024 or next_offset > len(mapped):
            raise ValueError(f"Invalid PCAP record at packet {packets}, byte offset {offset}")
        packets += 1
        offset = next_offset
    if offset != len(mapped):
        raise ValueError(f"Trailing {len(mapped) - offset} bytes after {packets} packets")
    return packets, [mapped[:24]]


def _scan_pcapng(mapped: mmap.mmap) -> tuple[int, list[bytes]]:
    offset = 0
    packets = 0
    endian: str | None = None
    metadata: list[bytes] = []
    while offset + 12 <= len(mapped):
        block_bytes = mapped[offset:offset + 4]
        if block_bytes == PCAPNG_MAGIC:
            if offset + 12 > len(mapped):
                raise ValueError("Truncated PCAPNG section header")
            bom = mapped[offset + 8:offset + 12]
            endian = PCAPNG_BOM_ENDIAN.get(bom)
            if endian is None:
                raise ValueError(f"Unsupported PCAPNG byte-order marker: {bom.hex()}")
            block_type = PCAPNG_SHB
        else:
            if endian is None:
                raise ValueError("PCAPNG file does not start with a section header")
            block_type = struct.unpack(endian + "I", block_bytes)[0]
        block_length = struct.unpack_from(endian + "I", mapped, offset + 4)[0]
        if block_length < 12 or block_length % 4 or offset + block_length > len(mapped):
            raise ValueError(f"Invalid PCAPNG block at byte offset {offset}")
        if block_type in (PCAPNG_SHB, PCAPNG_IDB):
            metadata.append(mapped[offset:offset + block_length])
        elif block_type in PCAPNG_PACKET_BLOCKS:
            packets += 1
        offset += block_length
    if offset != len(mapped):
        raise ValueError(f"Trailing {len(mapped) - offset} bytes after {packets} packets")
    return packets, metadata


def _make_outputs(source: Path, output_dir: Path, metadata: list[bytes], starts: list[int], size: int):
    outputs = []
    for index, start in enumerate(starts):
        path = output_dir / f"{source.stem}-window-{index:02d}.pcapng"
        output = path.open("wb")
        for block in metadata:
            output.write(block)
        outputs.append((path, start, start + size, output))
    return outputs


def _write_classic_windows(mapped: mmap.mmap, endian: str, outputs) -> None:
    offset = 24
    packet_index = 0
    target_index = 0
    while offset + 16 <= len(mapped):
        _, _, included, _ = struct.unpack_from(endian + "IIII", mapped, offset)
        block_size = 16 + included
        while target_index < len(outputs) and packet_index >= outputs[target_index][2]:
            outputs[target_index][3].close()
            target_index += 1
        if target_index < len(outputs):
            _, start, end, output = outputs[target_index]
            if start <= packet_index < end:
                output.write(mapped[offset:offset + block_size])
        packet_index += 1
        offset += block_size
    for index in range(target_index, len(outputs)):
        outputs[index][3].close()


def _write_pcapng_windows(mapped: mmap.mmap, outputs) -> None:
    offset = 0
    packet_index = 0
    target_index = 0
    endian: str | None = None
    while offset + 12 <= len(mapped):
        block_bytes = mapped[offset:offset + 4]
        if block_bytes == PCAPNG_MAGIC:
            endian = PCAPNG_BOM_ENDIAN[mapped[offset + 8:offset + 12]]
            block_type = PCAPNG_SHB
        else:
            if endian is None:
                raise ValueError("PCAPNG file does not start with a section header")
            block_type = struct.unpack(endian + "I", block_bytes)[0]
        block_length = struct.unpack_from(endian + "I", mapped, offset + 4)[0]
        if block_type in PCAPNG_PACKET_BLOCKS:
            while target_index < len(outputs) and packet_index >= outputs[target_index][2]:
                outputs[target_index][3].close()
                target_index += 1
            if target_index < len(outputs):
                _, start, end, output = outputs[target_index]
                if start <= packet_index < end:
                    output.write(mapped[offset:offset + block_length])
            packet_index += 1
        offset += block_length
    for index in range(target_index, len(outputs)):
        outputs[index][3].close()


def extract_windows(source: Path, output_dir: Path, window_size: int, window_count: int) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as source_file:
        mapped = mmap.mmap(source_file.fileno(), 0, access=mmap.ACCESS_READ)
        prefix = mapped[:4]
        if prefix == PCAPNG_MAGIC:
            total_packets, metadata = _scan_pcapng(mapped)
            file_format = "pcapng"
        elif prefix in PCAP_MAGIC_ENDIAN:
            endian = PCAP_MAGIC_ENDIAN[prefix]
            total_packets, metadata = _scan_classic(mapped, endian)
            file_format = "pcap"
        else:
            mapped.close()
            raise ValueError("Input is not a supported classic PCAP or PCAPNG file")

        if total_packets < window_size:
            mapped.close()
            raise ValueError(f"Capture has {total_packets} packets, fewer than requested window size")
        last_start = total_packets - window_size
        starts = [
            round(last_start * i / (window_count - 1)) if window_count > 1 else 0
            for i in range(window_count)
        ]
        outputs = _make_outputs(source, output_dir, metadata, starts, window_size)
        if file_format == "pcapng":
            _write_pcapng_windows(mapped, outputs)
        else:
            _write_classic_windows(mapped, PCAP_MAGIC_ENDIAN[prefix], outputs)
        mapped.close()

    windows = [
        {
            "file": str(path),
            "first_packet_index": start,
            "last_packet_index_exclusive": end,
            "packets": min(window_size, max(0, total_packets - start)),
        }
        for path, start, end, _ in outputs
    ]
    return {
        "source": str(source),
        "source_format": file_format,
        "source_packets": total_packets,
        "window_size": window_size,
        "windows": windows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract evenly spaced packet windows from a classic PCAP or PCAPNG.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--window-size", type=int, default=100_000)
    parser.add_argument("--window-count", type=int, default=8)
    args = parser.parse_args()
    report = extract_windows(args.input, args.output_dir, args.window_size, args.window_count)
    manifest = args.output_dir / f"{args.input.stem}-window-manifest.json"
    manifest.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print(f"Manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

