from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


REPO = "Ariasyah/cic-ids-2017"
REVISION = "main"
BASE_URL = f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/machine_learning"
FILES = [
    ("Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv.parquet", "Friday", "022ab31ab239f07e11a6458ee771eea0317a001d68398242cb36f5a4be66f972"),
    ("Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv.parquet", "Friday", "a49a5f5230ef15fbd60079a93db12c5a549913dfed66a142592c27c7264b08d7"),
    ("Friday-WorkingHours-Morning.pcap_ISCX.csv.parquet", "Friday", "e3cb0a243142fca1cfe0cd69437fa930a047f550c71353d34afbf618bd120427"),
    ("Monday-WorkingHours.pcap_ISCX.csv.parquet", "Monday", "fd6f986b33712f1986e6057c60f88b729d6e39a93bd107a6b0a53ae33958a22e"),
    ("Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv.parquet", "Thursday", "453bcb6400cf1cff4bd00404a3134f23e28b8541c7346566d984c733f3e62362"),
    ("Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv.parquet", "Thursday", "86ccdefdcd9c85e5d8fa159412d7402a66e97b9d9453c17de0156ac0c6999cc7"),
    ("Tuesday-WorkingHours.pcap_ISCX.csv.parquet", "Tuesday", "9fda00044283648f09ce6257a6bddc39c4e3a967d7a609ff808247727a4fcabb"),
    ("Wednesday-workingHours.pcap_ISCX.csv.parquet", "Wednesday", "3dd43daf2148052d76c2b8daa742a911e066c4d3cd4ba4ce933e53ccd1544592"),
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_one(item: tuple[str, str, str], output_dir: Path) -> dict:
    filename, capture_day, expected_sha256 = item
    target = output_dir / filename
    if target.exists():
        actual = sha256_file(target)
        if actual != expected_sha256:
            raise ValueError(f"Existing file has a checksum mismatch: {target} ({actual})")
        print(f"Verified existing {filename}", flush=True)
        return {
            "filename": filename,
            "capture_day": capture_day,
            "sha256": actual,
            "status": "already_verified",
            "bytes": target.stat().st_size,
        }

    part = output_dir / f"{filename}.part"
    url = f"{BASE_URL}/{filename}"
    last_error = None
    for attempt in range(1, 6):
        digest = hashlib.sha256()
        try:
            request = Request(url, headers={"User-Agent": "NeuroSphere-day-holdout/1.0"})
            with urlopen(request, timeout=90) as response, part.open("wb") as out:
                while chunk := response.read(1024 * 1024):
                    out.write(chunk)
                    digest.update(chunk)
            actual = digest.hexdigest()
            if actual != expected_sha256:
                part.unlink(missing_ok=True)
                raise ValueError(
                    f"Checksum mismatch for {filename}: expected {expected_sha256}, got {actual}"
                )
            os.replace(part, target)
            print(f"Downloaded and verified {filename}", flush=True)
            return {
                "filename": filename,
                "capture_day": capture_day,
                "sha256": actual,
                "status": "downloaded_and_verified",
                "bytes": target.stat().st_size,
            }
        except ValueError:
            raise
        except (URLError, TimeoutError, OSError) as exc:
            last_error = exc
            part.unlink(missing_ok=True)
            if attempt < 5:
                time.sleep(min(2 ** attempt, 16))
    raise RuntimeError(f"Could not download {filename}: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch checksum-pinned CICIDS2017 day flow Parquets.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "datasets/source_day_flows",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(fetch_one, item, args.output_dir) for item in FILES]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda result: result["filename"])
    manifest = {
        "source_repository": f"hf://datasets/{REPO}",
        "revision": REVISION,
        "mirror_status": "unofficial mirror; each downloaded file was checked against its listed SHA-256",
        "files": results,
    }
    manifest_path = args.output_dir / "source_day_flows_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote checksum manifest: {manifest_path}")
    print(f"Verified {len(results)} daily flow files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

