from __future__ import annotations

import configparser
import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/deception", tags=["Deception Analytics"])

DEFAULT_COWRIE_DIR = Path("/mnt/neurosphere/cowrie")
MAX_AUDIT_BYTES = 1_048_576
EVENT_GROUPS = {
    "connections_24h": {"cowrie.session.connect"},
    "failed_logins_24h": {"cowrie.login.failed"},
    "successful_logins_24h": {"cowrie.login.success"},
    "commands_24h": {"cowrie.command.input"},
    "download_events_24h": {"cowrie.session.file_download", "cowrie.session.file_upload"},
}


def _state_dir() -> Path:
    return Path(os.environ.get("NS_COWRIE_STATE_DIR", str(DEFAULT_COWRIE_DIR)))


def _config(state_dir: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read(state_dir / "etc" / "cowrie.cfg", encoding="utf-8")
    except OSError:
        pass
    return parser


def _is_cowrie_running(state_dir: Path) -> bool:
    try:
        raw_pid = (state_dir / "var" / "run" / "cowrie.pid").read_text(encoding="ascii").strip()
        pid = int(raw_pid)
        command = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").lower()
        return b"twistd" in command and b"cowrie" in command
    except (OSError, ValueError):
        return False


def _event_counts(log_path: Path) -> tuple[dict[str, int], str | None, Counter[str]]:
    counts = {key: 0 for key in EVENT_GROUPS}
    types: Counter[str] = Counter()
    last_event: datetime | None = None
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    try:
        with log_path.open("rb") as log_file:
            log_file.seek(0, os.SEEK_END)
            size = log_file.tell()
            log_file.seek(max(0, size - MAX_AUDIT_BYTES))
            if size > MAX_AUDIT_BYTES:
                log_file.readline()
            lines = log_file.read(MAX_AUDIT_BYTES).decode("utf-8", errors="replace").splitlines()
    except OSError:
        return counts, None, types

    grouped = {event_id: metric for metric, event_ids in EVENT_GROUPS.items() for event_id in event_ids}
    for line in lines:
        try:
            event: dict[str, Any] = json.loads(line)
            event_id = event.get("eventid")
            timestamp = event.get("timestamp")
            if not isinstance(event_id, str) or not isinstance(timestamp, str):
                continue
            parsed_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if parsed_at.tzinfo is None:
                parsed_at = parsed_at.replace(tzinfo=timezone.utc)
        except (json.JSONDecodeError, ValueError, TypeError):
            continue
        if parsed_at < cutoff:
            continue
        types[event_id] += 1
        metric = grouped.get(event_id)
        if metric:
            counts[metric] += 1
        if last_event is None or parsed_at > last_event:
            last_event = parsed_at

    return counts, last_event.isoformat() if last_event else None, types


@router.get("/cowrie/status")
def get_cowrie_status():
    state_dir = _state_dir()
    config_path = state_dir / "etc" / "cowrie.cfg"
    if not config_path.is_file():
        return {
            "status": "not_configured",
            "sensor": "Cowrie",
            "source": "local-cowrie-audit-log",
            "bind_scope": None,
            "event_counts": {key: 0 for key in EVENT_GROUPS},
            "last_event_at": None,
            "event_types_24h": {},
            "privacy": "Raw usernames, passwords, source addresses, and command text are not returned.",
        }

    config = _config(state_dir)
    ssh_endpoints = config.get("ssh", "listen_endpoints", fallback="")
    ssh_loopback_only = bool(ssh_endpoints.strip()) and all(
        "interface=127.0.0.1" in endpoint for endpoint in ssh_endpoints.split()
    )
    telnet_enabled = config.getboolean("telnet", "enabled", fallback=False)
    running = _is_cowrie_running(state_dir)
    if not ssh_loopback_only:
        status = "unsafe_bind"
    elif not running:
        status = "stopped"
    else:
        status = "connected"

    counts, last_event_at, event_types = _event_counts(state_dir / "var" / "log" / "cowrie" / "cowrie.json")
    return {
        "status": status,
        "sensor": "Cowrie",
        "version": config.get("honeypot", "version", fallback="Cowrie"),
        "source": "local-cowrie-audit-log",
        "bind_scope": "127.0.0.1" if ssh_loopback_only else "not-loopback",
        "ssh_port": 2222 if ssh_loopback_only else None,
        "telnet_enabled": telnet_enabled,
        "event_counts": counts,
        "last_event_at": last_event_at,
        "event_types_24h": dict(event_types.most_common(8)),
        "privacy": "Counts and event types only; raw usernames, passwords, source addresses, and command text are not returned.",
    }
