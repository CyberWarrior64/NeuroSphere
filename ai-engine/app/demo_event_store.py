from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("NEUROSPHERE_DEMO_DB", BASE_DIR / "data" / "demo-events.sqlite3"))
MAX_EVENTS = 1000


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if "NEUROSPHERE_DEMO_DB" not in os.environ:
        os.chmod(DB_PATH.parent, 0o700)
    connection = sqlite3.connect(DB_PATH, timeout=5.0)
    try:
        os.chmod(DB_PATH, 0o600)
    except FileNotFoundError:
        connection.close()
        raise
    connection.row_factory = sqlite3.Row
    return connection


def initialize_store() -> None:
    with _connect() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS prediction_events (
                id TEXT PRIMARY KEY,
                recorded_at TEXT NOT NULL,
                input_source TEXT NOT NULL,
                capture_mode TEXT NOT NULL DEFAULT 'unspecified',
                model_version TEXT NOT NULL,
                rf_classification TEXT NOT NULL,
                rf_probability REAL NOT NULL,
                rf_threshold REAL NOT NULL,
                rf_flagged INTEGER NOT NULL,
                if_classification TEXT NOT NULL,
                if_score REAL NOT NULL,
                if_threshold REAL NOT NULL,
                if_flagged INTEGER NOT NULL,
                detector_agreement TEXT
            )
        """)
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(prediction_events)")}
        if "capture_mode" not in columns:
            connection.execute(
                "ALTER TABLE prediction_events ADD COLUMN capture_mode TEXT NOT NULL DEFAULT 'unspecified'"
            )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_prediction_events_recorded_at "
            "ON prediction_events(recorded_at DESC)"
        )


def record_prediction(input_source: str, result: dict[str, Any], capture_mode: str = "unspecified") -> dict[str, Any]:
    detection = result["detection"]
    rf = detection["random_forest"]
    isolation = detection["isolation_forest"]
    if not isinstance(capture_mode, str) or capture_mode not in {"live", "pcap"}:
        capture_mode = "unspecified"
    event = {
        "id": str(uuid.uuid4()),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "input_source": input_source,
        "capture_mode": capture_mode,
        "model_version": str(result.get("model_version", "unknown")),
        "rf_classification": str(rf["classification"]),
        "rf_probability": float(rf["attack_probability"]),
        "rf_threshold": float(rf["threshold"]),
        "rf_flagged": bool(rf["flagged"]),
        "if_classification": str(isolation["classification"]),
        "if_score": float(isolation["anomaly_score"]),
        "if_threshold": float(isolation["threshold"]),
        "if_flagged": bool(isolation["flagged"]),
        "detector_agreement": result.get("risk_assessment", {}).get("detector_agreement"),
        "simulated": False,
    }
    with _connect() as connection:
        connection.execute("""
            INSERT INTO prediction_events (
                id, recorded_at, input_source, capture_mode, model_version,
                rf_classification, rf_probability, rf_threshold, rf_flagged,
                if_classification, if_score, if_threshold, if_flagged,
                detector_agreement
            ) VALUES (
                :id, :recorded_at, :input_source, :capture_mode, :model_version,
                :rf_classification, :rf_probability, :rf_threshold, :rf_flagged,
                :if_classification, :if_score, :if_threshold, :if_flagged,
                :detector_agreement
            )
        """, event)
        connection.execute("""
            DELETE FROM prediction_events
            WHERE id NOT IN (
                SELECT id FROM prediction_events
                ORDER BY recorded_at DESC, id DESC LIMIT ?
            )
        """, (MAX_EVENTS,))
    return event


def recent_predictions(limit: int = 100) -> list[dict[str, Any]]:
    bounded_limit = max(1, min(int(limit), 250))
    with _connect() as connection:
        rows = connection.execute("""
            SELECT id, recorded_at, input_source, capture_mode, model_version,
                   rf_classification, rf_probability, rf_threshold, rf_flagged,
                   if_classification, if_score, if_threshold, if_flagged,
                   detector_agreement
            FROM prediction_events
            ORDER BY recorded_at DESC, id DESC
            LIMIT ?
        """, (bounded_limit,)).fetchall()
    return [{**dict(row), "rf_flagged": bool(row["rf_flagged"]),
             "if_flagged": bool(row["if_flagged"]), "simulated": False}
            for row in rows]
