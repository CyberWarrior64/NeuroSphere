from __future__ import annotations

import ipaddress
import threading
import time
from datetime import datetime, timezone

import requests
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/v1/threat-intel", tags=["Threat Intelligence"])

FEED_NAME = "Emerging Threats Compromised IPs"
FEED_URL = "https://rules.emergingthreats.net/blockrules/compromised-ips.txt"
FEED_DESCRIPTION = "Public IPv4 addresses reported as compromised hosts by Emerging Threats."
REFRESH_INTERVAL_SECONDS = 900
RETRY_INTERVAL_SECONDS = 300
REQUEST_TIMEOUT = (3, 8)
MAX_FEED_BYTES = 1_000_000
MAX_FEED_INDICATORS = 20_000

_cache_lock = threading.Lock()
_cache: dict = {
    "indicators": [],
    "last_successful_fetch_at": None,
    "last_checked_at": None,
    "last_success_monotonic": None,
    "last_attempt_monotonic": None,
    "status": "unavailable",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_feed(body: bytes) -> list[dict[str, str]]:
    if len(body) > MAX_FEED_BYTES:
        raise ValueError("Feed exceeded the response size limit")

    text = body.decode("utf-8-sig")
    addresses: set[str] = set()
    for line in text.splitlines():
        value = line.split("#", 1)[0].strip()
        if not value:
            continue
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            continue
        if address.version != 4 or not address.is_global:
            continue
        addresses.add(address.compressed)
        if len(addresses) >= MAX_FEED_INDICATORS:
            break

    return [
        {
            "value": value,
            "type": "IPv4 address",
            "classification": "Compromised host report",
            "source": "Emerging Threats",
        }
        for value in sorted(addresses, key=lambda item: int(ipaddress.ip_address(item)))
    ]


def _refresh_cache() -> dict:
    now = time.monotonic()
    with _cache_lock:
        last_success = _cache["last_success_monotonic"]
        last_attempt = _cache["last_attempt_monotonic"]
        if last_success is not None and now - last_success < REFRESH_INTERVAL_SECONDS:
            return _cache
        if last_attempt is not None and now - last_attempt < RETRY_INTERVAL_SECONDS:
            return _cache

        _cache["last_attempt_monotonic"] = now
        _cache["last_checked_at"] = _utc_now()
        try:
            with requests.get(
                FEED_URL,
                headers={"User-Agent": "NeuroSphere-ThreatIntel-Demo/1.0"},
                timeout=REQUEST_TIMEOUT,
                stream=True,
            ) as response:
                response.raise_for_status()
                chunks: list[bytes] = []
                received = 0
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    received += len(chunk)
                    if received > MAX_FEED_BYTES:
                        raise ValueError("Feed exceeded the response size limit")
                    chunks.append(chunk)
                indicators = _parse_feed(b"".join(chunks))
        except (requests.RequestException, UnicodeDecodeError, ValueError):
            _cache["status"] = "stale" if last_success is not None else "unavailable"
            return _cache

        fetched_at = _utc_now()
        _cache.update(
            {
                "indicators": indicators,
                "last_successful_fetch_at": fetched_at,
                "last_checked_at": fetched_at,
                "last_success_monotonic": time.monotonic(),
                "status": "connected",
            }
        )
        return _cache


def _summary(cache: dict) -> dict:
    return {
        "status": cache["status"],
        "source": FEED_NAME,
        "source_url": FEED_URL,
        "description": FEED_DESCRIPTION,
        "indicator_count": len(cache["indicators"]),
        "last_checked_at": cache["last_checked_at"],
        "last_successful_fetch_at": cache["last_successful_fetch_at"],
        "refresh_interval_seconds": REFRESH_INTERVAL_SECONDS,
        "privacy": "The Ubuntu service fetches the public feed over HTTPS. It sends no analyst, host, or traffic data to the provider.",
        "use_notice": "Indicators are third-party leads, not proof of compromise. No traffic matching, blocking, or response action is performed.",
    }


@router.get("/status")
def get_threat_feed_status():
    return _summary(_refresh_cache())


@router.get("/indicators")
def get_threat_indicators(limit: int = Query(default=200, ge=1, le=500)):
    cache = _refresh_cache()
    return {
        **_summary(cache),
        "returned_count": min(limit, len(cache["indicators"])),
        "indicators": cache["indicators"][:limit],
    }
