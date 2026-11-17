"""Create a tiny synthetic Ethernet/IPv4/TCP capture for offline parser checks."""

from __future__ import annotations

import socket
import struct
from pathlib import Path


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "capture-smoke-test.pcap"
CLIENT_IP = "198.51.100.10"  # RFC 5737 documentation range; never a real host.
SERVER_IP = "203.0.113.20"   # RFC 5737 documentation range; never a real host.
CLIENT_MAC = bytes.fromhex("020000000010")
SERVER_MAC = bytes.fromhex("020000000020")
CLIENT_PORT = 51514
SERVER_PORT = 8080


def internet_checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\0"
    words = struct.unpack(f"!{len(data) // 2}H", data)
    total = sum(words)
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


def tcp_frame(
    *,
    source_ip: str,
    destination_ip: str,
    source_mac: bytes,
    destination_mac: bytes,
    source_port: int,
    destination_port: int,
    sequence: int,
    acknowledgement: int,
    flags: int,
    payload: bytes = b"",
    identification: int,
) -> bytes:
    source = socket.inet_aton(source_ip)
    destination = socket.inet_aton(destination_ip)
    offset_and_flags = (5 << 12) | flags
    tcp_without_checksum = struct.pack(
        "!HHIIHHHH",
        source_port,
        destination_port,
        sequence,
        acknowledgement,
        offset_and_flags,
        64240,
        0,
        0,
    ) + payload
    pseudo_header = source + destination + struct.pack("!BBH", 0, 6, len(tcp_without_checksum))
    tcp_checksum = internet_checksum(pseudo_header + tcp_without_checksum)
    tcp_segment = struct.pack(
        "!HHIIHHHH",
        source_port,
        destination_port,
        sequence,
        acknowledgement,
        offset_and_flags,
        64240,
        tcp_checksum,
        0,
    ) + payload

    total_length = 20 + len(tcp_segment)
    ip_without_checksum = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0,
        total_length,
        identification,
        0x4000,
        64,
        6,
        0,
        source,
        destination,
    )
    ip_checksum = internet_checksum(ip_without_checksum)
    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0,
        total_length,
        identification,
        0x4000,
        64,
        6,
        ip_checksum,
        source,
        destination,
    )
    ethernet = destination_mac + source_mac + struct.pack("!H", 0x0800)
    return ethernet + ip_header + tcp_segment


def main() -> None:
    request = (
        b"GET /health HTTP/1.1\r\n"
        b"Host: smoke-test.invalid\r\n"
        b"Connection: close\r\n\r\n"
    )
    response = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Length: 2\r\n"
        b"Connection: close\r\n\r\nOK"
    )
    client_next = 1001 + len(request)
    server_next = 5001 + len(response)
    packets = [
        (0, tcp_frame(source_ip=CLIENT_IP, destination_ip=SERVER_IP, source_mac=CLIENT_MAC, destination_mac=SERVER_MAC, source_port=CLIENT_PORT, destination_port=SERVER_PORT, sequence=1000, acknowledgement=0, flags=0x02, identification=1)),
        (100_000, tcp_frame(source_ip=SERVER_IP, destination_ip=CLIENT_IP, source_mac=SERVER_MAC, destination_mac=CLIENT_MAC, source_port=SERVER_PORT, destination_port=CLIENT_PORT, sequence=5000, acknowledgement=1001, flags=0x12, identification=2)),
        (200_000, tcp_frame(source_ip=CLIENT_IP, destination_ip=SERVER_IP, source_mac=CLIENT_MAC, destination_mac=SERVER_MAC, source_port=CLIENT_PORT, destination_port=SERVER_PORT, sequence=1001, acknowledgement=5001, flags=0x10, identification=3)),
        (300_000, tcp_frame(source_ip=CLIENT_IP, destination_ip=SERVER_IP, source_mac=CLIENT_MAC, destination_mac=SERVER_MAC, source_port=CLIENT_PORT, destination_port=SERVER_PORT, sequence=1001, acknowledgement=5001, flags=0x18, payload=request, identification=4)),
        (400_000, tcp_frame(source_ip=SERVER_IP, destination_ip=CLIENT_IP, source_mac=SERVER_MAC, destination_mac=CLIENT_MAC, source_port=SERVER_PORT, destination_port=CLIENT_PORT, sequence=5001, acknowledgement=client_next, flags=0x10, identification=5)),
        (500_000, tcp_frame(source_ip=SERVER_IP, destination_ip=CLIENT_IP, source_mac=SERVER_MAC, destination_mac=CLIENT_MAC, source_port=SERVER_PORT, destination_port=CLIENT_PORT, sequence=5001, acknowledgement=client_next, flags=0x18, payload=response, identification=6)),
        (600_000, tcp_frame(source_ip=CLIENT_IP, destination_ip=SERVER_IP, source_mac=CLIENT_MAC, destination_mac=SERVER_MAC, source_port=CLIENT_PORT, destination_port=SERVER_PORT, sequence=client_next, acknowledgement=server_next, flags=0x10, identification=7)),
        (700_000, tcp_frame(source_ip=CLIENT_IP, destination_ip=SERVER_IP, source_mac=CLIENT_MAC, destination_mac=SERVER_MAC, source_port=CLIENT_PORT, destination_port=SERVER_PORT, sequence=client_next, acknowledgement=server_next, flags=0x11, identification=8)),
        (800_000, tcp_frame(source_ip=SERVER_IP, destination_ip=CLIENT_IP, source_mac=SERVER_MAC, destination_mac=CLIENT_MAC, source_port=SERVER_PORT, destination_port=CLIENT_PORT, sequence=server_next, acknowledgement=client_next + 1, flags=0x11, identification=9)),
        (900_000, tcp_frame(source_ip=CLIENT_IP, destination_ip=SERVER_IP, source_mac=CLIENT_MAC, destination_mac=SERVER_MAC, source_port=CLIENT_PORT, destination_port=SERVER_PORT, sequence=client_next + 1, acknowledgement=server_next + 1, flags=0x10, identification=10)),
    ]

    with OUTPUT.open("wb") as capture:
        # Classic PCAP, little-endian, microsecond timestamps, Ethernet link type.
        capture.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        base_seconds = 1_700_000_000
        for microseconds, packet in packets:
            capture.write(struct.pack("<IIII", base_seconds, microseconds, len(packet), len(packet)))
            capture.write(packet)

    print(f"Wrote {len(packets)} synthetic TCP packets to {OUTPUT} ({OUTPUT.stat().st_size} bytes).")


if __name__ == "__main__":
    main()
