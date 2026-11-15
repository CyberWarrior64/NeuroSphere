from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / 'datasets/reference_pcaps/friday-reference'
REPOSITORY = 'https://huggingface.co/datasets/bvsam/cic-ids-2017/resolve/main/'
LABELS = [
    ('traffic_labels/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv.parquet', '7c5876d52189fc01af54bad6cf23afe9f7fbc0e3ca6c3595920754f0c3ba8f66'),
    ('traffic_labels/Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv.parquet', '4d78cee297c27f1a9947b9384793e587a46c7a3ea89db199553dabddc9835d4a'),
    ('traffic_labels/Friday-WorkingHours-Morning.pcap_ISCX.csv.parquet', '2c00236b13a69f4b1c222b8f4a89451dc2148cb04a8cd0c45c2a87af51471774'),
]
PCAP = ('pcap/Friday-WorkingHours.pcap', 'beff0dcce1eebc9b2454582f4dc8ed0ba0112b2c619a710bf03af93147254cd0')


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def download(relative_path: str, expected_sha256: str) -> dict:
    name = Path(relative_path).name
    destination = OUTPUT_DIR / name
    partial = OUTPUT_DIR / (name + '.part')
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        actual = file_sha256(destination)
        if actual == expected_sha256:
            print(f'Already verified: {name}', flush=True)
            return {'filename': name, 'sha256': actual, 'status': 'already_verified', 'bytes': destination.stat().st_size}
        raise RuntimeError(f'Existing file has unexpected hash; leaving it untouched: {destination}')

    offset = partial.stat().st_size if partial.exists() else 0
    headers = {'Accept-Encoding': 'identity'}
    if offset:
        headers['Range'] = f'bytes={offset}-'
    url = REPOSITORY + relative_path
    print(f'Downloading {name}; existing partial bytes={offset:,}', flush=True)
    with requests.get(url, headers=headers, stream=True, timeout=(30, 300)) as response:
        response.raise_for_status()
        append = offset > 0 and response.status_code == 206
        mode = 'ab' if append else 'wb'
        initial = offset if append else 0
        total = int(response.headers.get('Content-Length', '0') or 0) + initial
        received = initial
        last_report = (received // (1024**3))
        with partial.open(mode) as handle:
            for chunk in response.iter_content(chunk_size=8 * 1024 * 1024):
                if not chunk:
                    continue
                handle.write(chunk)
                received += len(chunk)
                gib = received // (1024**3)
                if gib > last_report:
                    last_report = gib
                    suffix = f' / {total:,} bytes' if total else ''
                    print(f'{name}: {received:,}{suffix}', flush=True)
            handle.flush()
            os.fsync(handle.fileno())
    actual = file_sha256(partial)
    if actual != expected_sha256:
        raise RuntimeError(f'SHA-256 mismatch for {name}: expected {expected_sha256}, received {actual}; partial retained.')
    os.replace(partial, destination)
    print(f'Verified SHA-256: {name} ({destination.stat().st_size:,} bytes)', flush=True)
    return {'filename': name, 'sha256': actual, 'status': 'downloaded_and_verified', 'bytes': destination.stat().st_size}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--labels-only', action='store_true')
    parser.add_argument('--pcap-only', action='store_true')
    args = parser.parse_args()
    if args.labels_only and args.pcap_only:
        raise SystemExit('Choose one option.')
    selected = []
    if not args.pcap_only:
        selected.extend(LABELS)
    if not args.labels_only:
        selected.append(PCAP)
    records = [download(path, digest) for path, digest in selected]
    manifest_path = OUTPUT_DIR / 'friday_reference_manifest.json'
    current = {'source_repository': 'hf://datasets/bvsam/cic-ids-2017', 'revision': 'main', 'integrity': 'Each file verified against the Hugging Face file-page SHA-256.', 'files': records}
    if manifest_path.exists():
        prior = json.loads(manifest_path.read_text())
        merged = {entry['filename']: entry for entry in prior.get('files', [])}
        merged.update({entry['filename']: entry for entry in records})
        current['files'] = list(merged.values())
    manifest_path.write_text(json.dumps(current, indent=2) + '\n')
    print(f'Wrote {manifest_path.relative_to(ROOT)}', flush=True)


if __name__ == '__main__':
    main()
