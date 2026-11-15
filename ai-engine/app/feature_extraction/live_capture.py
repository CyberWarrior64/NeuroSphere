from collections import defaultdict
from scapy.all import sniff, IP, TCP, UDP, ICMP

INTERFACE = "enp0s31f6"
CAPTURE_SECONDS = 15

flows = defaultdict(lambda: {
    "packets": 0,
    "bytes": 0,
    "first_seen": None,
    "last_seen": None
})

protocol_counts = defaultdict(int)
total_packets = 0


def process_packet(packet):
    global total_packets

    if not packet.haslayer(IP):
        return

    ip = packet[IP]

    if packet.haslayer(TCP):
        protocol = "TCP"
        src_port = packet[TCP].sport
        dst_port = packet[TCP].dport
    elif packet.haslayer(UDP):
        protocol = "UDP"
        src_port = packet[UDP].sport
        dst_port = packet[UDP].dport
    elif packet.haslayer(ICMP):
        protocol = "ICMP"
        src_port = 0
        dst_port = 0
    else:
        return

    timestamp = float(packet.time)
    packet_size = len(packet)

    flow_key = (
        ip.src, src_port,
        ip.dst, dst_port,
        protocol
    )

    flow = flows[flow_key]
    flow["packets"] += 1
    flow["bytes"] += packet_size

    if flow["first_seen"] is None:
        flow["first_seen"] = timestamp

    flow["last_seen"] = timestamp

    protocol_counts[protocol] += 1
    total_packets += 1


if __name__ == "__main__":
    print("=" * 55)
    print("       NEUROSPHERE - LIVE NETWORK MONITOR")
    print("=" * 55)
    print("Interface:", INTERFACE)
    print("Duration:", CAPTURE_SECONDS, "seconds")
    print("Mode: Passive metadata capture")
    print("Packet payloads are not stored.")
    print("\nCapturing traffic...\n")

    try:
        sniff(
            iface=INTERFACE,
            filter="ip and (tcp or udp or icmp)",
            timeout=CAPTURE_SECONDS,
            store=False,
            prn=process_packet
        )
    except Exception as error:
        print("Capture error:", error)
        raise SystemExit(1)

    print("\n========== CAPTURE SUMMARY ==========")
    print("Total packets:", total_packets)
    print("Unique directional flows:", len(flows))

    for protocol, count in protocol_counts.items():
        print(f"{protocol}: {count} packets")

    print("\n========== TOP NETWORK FLOWS ==========")

    sorted_flows = sorted(
        flows.items(),
        key=lambda item: item[1]["packets"],
        reverse=True
    )

    for key, stats in sorted_flows[:10]:
        src, sport, dst, dport, protocol = key
        duration = stats["last_seen"] - stats["first_seen"]

        print({
            "source": f"{src}:{sport}",
            "destination": f"{dst}:{dport}",
            "protocol": protocol,
            "packets": stats["packets"],
            "bytes": stats["bytes"],
            "duration_seconds": round(duration, 6)
        })

    print("\nNeuroSphere capture test completed.")
