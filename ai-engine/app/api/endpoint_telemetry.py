from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/endpoint", tags=["Endpoint Telemetry"])


def _memory() -> dict[str, int | None]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            values[key] = int(value.strip().split()[0]) * 1024
    except (OSError, ValueError, IndexError):
        return {"total_bytes": None, "available_bytes": None}
    return {
        "total_bytes": values.get("MemTotal"),
        "available_bytes": values.get("MemAvailable"),
    }


def _ssh_auth_summary() -> dict[str, int | bool]:
    """Read a bounded SSH journal window and return counts only, never log text."""
    journalctl = shutil.which("journalctl")
    if not journalctl:
        return {"available": False, "failed_logins_24h": 0, "successful_logins_24h": 0}
    try:
        result = subprocess.run(
            [
                journalctl,
                "--unit=ssh.service",
                "--since=24 hours ago",
                "--lines=500",
                "--output=json",
                "--no-pager",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if result.returncode != 0:
            return {"available": False, "failed_logins_24h": 0, "successful_logins_24h": 0}
        failed = successful = 0
        for line in result.stdout.splitlines():
            try:
                message = str(json.loads(line).get("MESSAGE", "")).lower()
            except (json.JSONDecodeError, AttributeError):
                continue
            if any(term in message for term in ("failed password", "authentication failure", "maximum authentication attempts")):
                failed += 1
            if "accepted " in message and ("password" in message or "publickey" in message):
                successful += 1
        return {"available": True, "failed_logins_24h": failed, "successful_logins_24h": successful}
    except (OSError, subprocess.TimeoutExpired):
        return {"available": False, "failed_logins_24h": 0, "successful_logins_24h": 0}


@router.get("/telemetry")
def get_endpoint_telemetry():
    memory = _memory()
    disk = shutil.disk_usage("/")
    load = None
    try:
        load = os.getloadavg()[0]
    except (AttributeError, OSError):
        pass
    try:
        uptime_seconds = float(Path("/proc/uptime").read_text().split()[0])
    except (OSError, ValueError, IndexError):
        uptime_seconds = 0.0
    return {
        "status": "connected",
        "source": "local-linux-host",
        "hostname": socket.gethostname(),
        "operating_system": f"{platform.system()} {platform.release()}",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": int(uptime_seconds),
        "cpu": {"logical_cores": os.cpu_count(), "load_average_1m": load},
        "memory": memory,
        "root_disk": {"total_bytes": disk.total, "free_bytes": disk.free},
        "ssh_authentication_24h": _ssh_auth_summary(),
        "privacy": "Aggregate SSH counts only; raw journal messages, usernames, and addresses are not returned or stored.",
    }
