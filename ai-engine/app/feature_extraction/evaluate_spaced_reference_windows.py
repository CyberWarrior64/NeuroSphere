from __future__ import annotations

import argparse
import json
from pathlib import Path

from scapy.sendrecv import AsyncSniffer

from app.feature_extraction.cicflowmeter_packet_compat import install_training_csv_reference_adapter
from app.feature_extraction.cicflowmeter_java_session import CICFlowMeterReferenceSession
from app.feature_extraction.compare_training_reference import GROUPS, compare
from app.feature_extraction.evaluate_java_fin_candidate import CurrentUpstreamFINSession


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_REFERENCE = BASE_DIR / "datasets/reference_pcaps/Monday-WorkingHours.traffic_labels.parquet"


def _run(pcap: Path, output_csv: Path, boundary: str) -> None:
    session_class = CurrentUpstreamFINSession if boundary == "upstream" else CICFlowMeterReferenceSession
    session = session_class(
        output_mode="csv",
        output=str(output_csv),
        fields=None,
        verbose=False,
    )
    sniffer = AsyncSniffer(
        offline=str(pcap),
        filter="ip and (tcp or udp)",
        prn=session.process,
        store=False,
    )
    print(f"Starting {boundary} replay: {pcap}", flush=True)
    sniffer.start()
    sniffer.join()
    session.flush_flows()
    print(f"Finished {boundary} replay: {output_csv}", flush=True)


def _aggregate(reports: list[dict]) -> dict:
    comparisons = [report["comparison"] for report in reports]
    matching = [report["matching"]["unique_direct_matches"] for report in reports]
    total_rows = sum(matching)
    total_cells = sum(item["feature_cells_compared"] for item in comparisons)
    matched_cells = sum(item["feature_cells_matching"] for item in comparisons)
    exact_core_rows = sum(item["exact_core_rows"] for item in comparisons)
    full_vectors = sum(item["complete_67_feature_vectors"] for item in comparisons)

    per_feature = {}
    for feature in comparisons[0]["per_feature_agreement"]:
        matched = sum(
            round(item["per_feature_agreement"][feature] * rows)
            for item, rows in zip(comparisons, matching)
        )
        per_feature[feature] = matched / total_rows if total_rows else None

    group_agreement = {}
    for group, features in GROUPS.items():
        matched = 0
        cells = 0
        for item, rows in zip(comparisons, matching):
            n_cells = len(features) * rows
            matched += round(item["group_agreement"][group] * n_cells)
            cells += n_cells
        group_agreement[group] = matched / cells if cells else None

    core_exact_cells = sum(
        round(item["exact_core_comparison"]["feature_cell_agreement"] * item["exact_core_rows"] * 67)
        if item["exact_core_rows"] else 0
        for item in comparisons
    )
    return {
        "windows": len(reports),
        "generated_rows": sum(report["sample"]["rows"] for report in reports),
        "unique_direct_matches": total_rows,
        "feature_cells_matching": matched_cells,
        "feature_cells_compared": total_cells,
        "feature_cell_agreement": matched_cells / total_cells if total_cells else None,
        "complete_67_feature_vectors": full_vectors,
        "exact_core_rows": exact_core_rows,
        "exact_core_row_fraction": exact_core_rows / total_rows if total_rows else None,
        "complete_vector_rate_within_core_exact": full_vectors / exact_core_rows if exact_core_rows else None,
        "feature_cell_agreement_within_core_exact": (
            core_exact_cells / (exact_core_rows * 67) if exact_core_rows else None
        ),
        "group_agreement": group_agreement,
        "per_feature_agreement": per_feature,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare calibrated and upstream-FIN flow boundaries on evenly spaced PCAP windows."
    )
    parser.add_argument(
        "--pcap-dir",
        type=Path,
        default=BASE_DIR / "datasets/reference_pcaps/spaced-windows",
    )
    parser.add_argument("--pattern", default="Monday-WorkingHours-window-*.pcapng")
    parser.add_argument("--reference-parquet", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=BASE_DIR / "datasets/reference_pcaps/spaced-windows/results",
    )
    parser.add_argument("--capture-timezone", default="Asia/Kolkata")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    pcaps = sorted(args.pcap_dir.glob(args.pattern))
    if not pcaps:
        raise FileNotFoundError(f"No PCAP windows matched {args.pcap_dir / args.pattern}")

    install_training_csv_reference_adapter()
    aggregate_reports: dict[str, list[dict]] = {"current": [], "upstream": []}
    for index, pcap in enumerate(pcaps):
        for boundary in ("current", "upstream"):
            output_csv = args.output_dir / f"{pcap.stem}-{boundary}.csv"
            _run(pcap, output_csv, boundary)
            report = compare(output_csv, args.reference_parquet, args.capture_timezone)
            report_path = args.output_dir / f"{pcap.stem}-{boundary}-parity.json"
            report_path.write_text(json.dumps(report, indent=2) + "\n")
            aggregate_reports[boundary].append(report)
            print(
                f"Window {index + 1}/{len(pcaps)} {boundary}: "
                f"{report['matching']['unique_direct_matches']} matches, "
                f"{report['comparison']['feature_cell_agreement']:.4%} cells, "
                f"{report['comparison']['exact_core_rows']} exact core, "
                f"{report['comparison']['complete_67_feature_vectors']} complete vectors",
                flush=True,
            )

    summary = {
        "source_capture": "datasets/reference_pcaps/Monday-WorkingHours.pcap",
        "window_manifest": str(args.pcap_dir / "Monday-WorkingHours-window-manifest.json"),
        "reference_parquet": str(args.reference_parquet),
        "capture_timezone": args.capture_timezone,
        "sampling": "Evenly spaced packet windows; exact window count, size, and indexes are recorded in the window manifest.",
        "feature_parity_verified": False,
        "limitations": [
            "The traffic comes from the model's training-source dataset and does not measure independent-capture generalization.",
            "Window edges can truncate flows, and the exact CICFlowMeter build used for the training table remains unknown.",
            "The upstream candidate follows the current source-level FIN logic and may not match the historical training generator release.",
            "No attack-detection quality is measured by this benign Monday comparison.",
        ],
        "results": {
            boundary: _aggregate(reports)
            for boundary, reports in aggregate_reports.items()
        },
        "per_window": {
            boundary: [
                {
                    "window": report["sample"]["generated_csv"],
                    "matching": report["matching"]["unique_direct_matches"],
                    "cell_agreement": report["comparison"]["feature_cell_agreement"],
                    "exact_core_rows": report["comparison"]["exact_core_rows"],
                    "complete_vectors": report["comparison"]["complete_67_feature_vectors"],
                }
                for report in reports
            ]
            for boundary, reports in aggregate_reports.items()
        },
    }
    summary_path = args.output_dir / "spaced-windows-parity-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["results"], indent=2))
    print(f"Summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

