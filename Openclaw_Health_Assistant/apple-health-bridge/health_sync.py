"""Apple Health → local SQLite (Health Link pairing API and optional JSON import)."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def import_health_json_export(
    dest_conn: sqlite3.Connection,
    export_path: str | Path,
    user_id: str,
) -> dict[str, Any]:
    """Import Apple Health samples from a JSON file (see apple-health-bridge/inbox/README.md)."""
    path = Path(export_path).expanduser().resolve()
    if not path.is_file():
        return {"status": "error", "message": f"Export not found: {path}"}

    payload = json.loads(path.read_text(encoding="utf-8"))
    now = _now_iso()
    inserted: dict[str, int] = {}

    for item in payload.get("glucose", []):
        dest_conn.execute(
            """
            INSERT OR REPLACE INTO health_glucose
            (id, user_id, value_real, unit, source_bundle_id, recorded_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.get("id", str(uuid.uuid4())),
                user_id,
                float(item["value"]),
                item.get("unit", "mg/dL"),
                item.get("source_bundle_id"),
                item["recorded_at"],
                now,
            ),
        )
    inserted["health_glucose"] = len(payload.get("glucose", []))

    for item in payload.get("heart_rate", []):
        dest_conn.execute(
            """
            INSERT OR REPLACE INTO health_heart_rate
            (id, user_id, value_real, unit, source_bundle_id, recorded_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.get("id", str(uuid.uuid4())),
                user_id,
                float(item["value"]),
                item.get("unit", "bpm"),
                item.get("source_bundle_id"),
                item["recorded_at"],
                now,
            ),
        )
    inserted["health_heart_rate"] = len(payload.get("heart_rate", []))

    for item in payload.get("steps", []):
        dest_conn.execute(
            """
            INSERT OR REPLACE INTO health_steps
            (id, user_id, count, distance_meters, start_at, end_at, source_bundle_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.get("id", str(uuid.uuid4())),
                user_id,
                int(item["count"]),
                float(item.get("distance_meters") or 0.0),
                item["start_at"],
                item["end_at"],
                item.get("source_bundle_id"),
                now,
            ),
        )
    inserted["health_steps"] = len(payload.get("steps", []))

    for item in payload.get("blood_pressure", []):
        dest_conn.execute(
            """
            INSERT OR REPLACE INTO health_blood_pressure
            (id, user_id, systolic_real, diastolic_real, unit, source_bundle_id, recorded_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.get("id", str(uuid.uuid4())),
                user_id,
                float(item["systolic"]),
                float(item["diastolic"]),
                item.get("unit", "mmHg"),
                item.get("source_bundle_id"),
                item["recorded_at"],
                now,
            ),
        )
    inserted["health_blood_pressure"] = len(payload.get("blood_pressure", []))

    for item in payload.get("lab_results", []):
        dest_conn.execute(
            """
            INSERT OR REPLACE INTO health_lab_results
            (id, user_id, name, loinc_code, value_numeric, value_string, unit,
             reference_range_low, reference_range_high, reference_range_text,
             source_name, source_bundle_id, specimen_type, recorded_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.get("id", str(uuid.uuid4())),
                user_id,
                item["name"],
                item.get("loinc_code"),
                item.get("value_numeric"),
                item.get("value_string"),
                item.get("unit"),
                item.get("reference_range_low"),
                item.get("reference_range_high"),
                item.get("reference_range_text"),
                item.get("source_name"),
                item.get("source_bundle_id"),
                item.get("specimen_type"),
                item["recorded_at"],
                now,
            ),
        )
    inserted["health_lab_results"] = len(payload.get("lab_results", []))

    sync_hours = int(payload.get("sync_interval_hours", 24))
    dest_conn.execute(
        """
        INSERT INTO health_sync_settings (user_id, sync_interval_hours, last_synced_at, connected_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
          sync_interval_hours = excluded.sync_interval_hours,
          last_synced_at = excluded.last_synced_at,
          updated_at = excluded.updated_at
        """,
        (user_id, sync_hours, now, now, now),
    )
    dest_conn.commit()
    return {
        "status": "success",
        "user_id": user_id,
        "export_path": str(path),
        "rows_inserted": inserted,
    }
