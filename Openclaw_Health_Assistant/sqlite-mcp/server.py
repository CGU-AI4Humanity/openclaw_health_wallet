"""MyWellWallet-compatible SQLite MCP server for OpenClaw."""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

_BRIDGE = Path(__file__).resolve().parent.parent / "apple-health-bridge"
if str(_BRIDGE) not in sys.path:
    sys.path.insert(0, str(_BRIDGE))

import db

mcp = FastMCP(
    name="MyWellWallet SQLite",
    stateless_http=os.getenv("MCP_TRANSPORT") == "streamable-http",
    json_response=True,
    host=os.getenv("MCP_HOST", "127.0.0.1"),
    port=int(os.getenv("MCP_PORT", "8010")),
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@mcp.tool()
def sqlite_health() -> Dict[str, Any]:
    """Verify database path, connectivity, and list table names."""
    path = db.db_path()
    try:
        with db.connect() as conn:
            tables = db.ensure_schema(conn)
            counts: dict[str, int] = {}
            for name in (
                "users",
                "fhir_patients",
                "fhir_resources",
                "health_heart_rate",
                "health_steps",
            ):
                if name in tables:
                    counts[name] = conn.execute(
                        f"SELECT COUNT(*) FROM {name}"
                    ).fetchone()[0]
        return {
            "status": "success",
            "database_path": str(path),
            "tables": tables,
            "counts": counts,
        }
    except FileNotFoundError as exc:
        return {"status": "error", "message": str(exc), "database_path": str(path)}
    except Exception as exc:
        return {"status": "error", "message": str(exc), "database_path": str(path)}


@mcp.tool()
def list_users(limit: int = 20) -> dict[str, Any]:
    """List user profiles (id, name, email, date_of_birth)."""
    limit = max(1, min(limit, 100))
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT id, name, email, date_of_birth, created_at, updated_at "
            "FROM users ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return {"status": "success", "users": db.rows_to_dicts(rows)}


@mcp.tool()
def get_current_user() -> dict[str, Any]:
    """Return the most recently created user profile row."""
    with db.connect() as conn:
        row = conn.execute(
            "SELECT id, name, email, date_of_birth, created_at, updated_at "
            "FROM users ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return {"status": "success", "user": None}
    return {"status": "success", "user": dict(row)}


@mcp.tool()
def list_fhir_patients(limit: int = 50) -> dict[str, Any]:
    """List cached FHIR patients (metadata only, not full bundles)."""
    limit = max(1, min(limit, 200))
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT id, patient_id, patient_name, last_synced, created_at, updated_at
            FROM fhir_patients
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return {"status": "success", "patients": db.rows_to_dicts(rows)}


@mcp.tool()
def get_fhir_patient_bundle(patient_id: str) -> dict[str, Any]:
    """Return the full FHIR Bundle JSON for a patient_id."""
    with db.connect() as conn:
        row = conn.execute(
            """
            SELECT patient_id, patient_name, fhir_bundle, last_synced
            FROM fhir_patients
            WHERE patient_id = ?
            """,
            (patient_id,),
        ).fetchone()
    if row is None:
        return {
            "status": "error",
            "message": f"No patient with patient_id={patient_id}",
        }
    bundle = json.loads(row["fhir_bundle"])
    return {
        "status": "success",
        "patient_id": row["patient_id"],
        "patient_name": row["patient_name"],
        "last_synced": row["last_synced"],
        "fhir_bundle": bundle,
    }


@mcp.tool()
def search_fhir_resources(
    patient_id: str,
    resource_type: Optional[str] = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Search denormalized fhir_resources rows for a patient."""
    limit = max(1, min(limit, 500))
    with db.connect() as conn:
        if resource_type:
            rows = conn.execute(
                """
                SELECT resource_type, resource_id, resource_data, updated_at
                FROM fhir_resources
                WHERE patient_id = ? AND resource_type = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (patient_id, resource_type, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT resource_type, resource_id, resource_data, updated_at
                FROM fhir_resources
                WHERE patient_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (patient_id, limit),
            ).fetchall()
    resources = []
    for row in rows:
        resources.append(
            {
                "resource_type": row["resource_type"],
                "resource_id": row["resource_id"],
                "resource": json.loads(row["resource_data"]),
                "updated_at": row["updated_at"],
            }
        )
    return {
        "status": "success",
        "patient_id": patient_id,
        "resource_type_filter": resource_type,
        "resources": resources,
    }


@mcp.tool()
def execute_read_query(sql: str, max_rows: int = 100) -> dict[str, Any]:
    """
    Run a single read-only SQL statement (SELECT / WITH / safe PRAGMA).
    Use for health_* and FHIR tables; writes are not allowed through this tool.
    """
    max_rows = max(1, min(max_rows, 500))
    try:
        safe_sql = db.validate_readonly_sql(sql)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}

    with db.connect() as conn:
        cur = conn.execute(safe_sql)
        if cur.description is None:
            return {"status": "success", "columns": [], "rows": []}
        columns = [d[0] for d in cur.description]
        rows = cur.fetchmany(max_rows)
    return {
        "status": "success",
        "columns": columns,
        "rows": [list(r) for r in rows],
        "truncated": len(rows) >= max_rows,
    }


@mcp.tool()
def upsert_fhir_patient(
    patient_id: str,
    patient_name: str,
    fhir_bundle_json: str,
    last_synced: Optional[str] = None,
) -> dict[str, Any]:
    """
    Insert or replace a FHIR patient bundle in fhir_patients.
    fhir_bundle_json must be a JSON string of a FHIR Bundle.
    """
    synced = last_synced or _now_iso()
    now = _now_iso()
    try:
        bundle = json.loads(fhir_bundle_json)
    except json.JSONDecodeError as exc:
        return {"status": "error", "message": f"Invalid JSON: {exc}"}

    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO fhir_patients (
              id, patient_id, patient_name, fhir_bundle, last_synced, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              patient_name = excluded.patient_name,
              fhir_bundle = excluded.fhir_bundle,
              last_synced = excluded.last_synced,
              updated_at = excluded.updated_at
            """,
            (
                patient_id,
                patient_id,
                patient_name,
                json.dumps(bundle),
                synced,
                now,
                now,
            ),
        )
        conn.commit()
    return {
        "status": "success",
        "patient_id": patient_id,
        "patient_name": patient_name,
        "last_synced": synced,
    }


@mcp.tool()
def upsert_fhir_resource(
    patient_id: str,
    resource_type: str,
    resource_id: str,
    resource_data_json: str,
) -> dict[str, Any]:
    """Insert or update one row in fhir_resources."""
    now = _now_iso()
    row_id = f"{patient_id}:{resource_type}:{resource_id}"
    try:
        resource = json.loads(resource_data_json)
    except json.JSONDecodeError as exc:
        return {"status": "error", "message": f"Invalid JSON: {exc}"}

    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO fhir_resources (
              id, patient_id, resource_type, resource_id, resource_data, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              resource_data = excluded.resource_data,
              updated_at = excluded.updated_at
            """,
            (
                row_id,
                patient_id,
                resource_type,
                resource_id,
                json.dumps(resource),
                now,
                now,
            ),
        )
        conn.commit()
    return {
        "status": "success",
        "id": row_id,
        "patient_id": patient_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
    }


@mcp.tool()
def health_metrics_summary(user_id: str, days: int = 30) -> dict[str, Any]:
    """Summarize recent Apple Health mirror tables for a user_id."""
    days = max(1, min(days, 365))
    with db.connect() as conn:
        summary: dict[str, Any] = {"user_id": user_id, "days_requested": days}
        for table, col in (
            ("health_heart_rate", "recorded_at"),
            ("health_blood_pressure", "recorded_at"),
            ("health_glucose", "recorded_at"),
            ("health_steps", "created_at"),
            ("health_lab_results", "recorded_at"),
        ):
            try:
                count = conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE user_id = ?",
                    (user_id,),
                ).fetchone()[0]
                summary[table] = {
                    "row_count": count,
                    "time_column": col,
                }
            except sqlite3.OperationalError:
                summary[table] = {"row_count": 0, "time_column": col}
    return {"status": "success", "summary": summary}


@mcp.tool()
def get_apple_health_sync_status(user_id: str) -> dict[str, Any]:
    """Return health_sync_settings for a user (Apple Health connection metadata)."""
    with db.connect() as conn:
        row = conn.execute(
            """
            SELECT user_id, sync_interval_hours, last_synced_at, connected_at, updated_at
            FROM health_sync_settings WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    if row is None:
        return {"status": "success", "connected": False, "settings": None}
    return {"status": "success", "connected": True, "settings": dict(row)}


@mcp.tool()
def sync_apple_health_from_phone_database(
    source_sqlite_path: str,
    user_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Copy Apple Health mirror tables from a MyWellWallet iPhone SQLite export
    into the local assistant database. Default source: ~/myWellWallet/fixtures/...
    """
    from health_sync import sync_health_tables_from_phone_db

    path = source_sqlite_path.strip() or os.path.expanduser(
        "~/myWellWallet/fixtures/test_database_export/mywellwallet_phone.sqlite3"
    )
    with db.connect() as conn:
        return sync_health_tables_from_phone_db(conn, path, user_id)


@mcp.tool()
def import_apple_health_json(
    export_json_path: str,
    user_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Import Apple Health samples from a JSON export file
    (see apple-health-bridge/inbox/README.md).
    """
    from health_sync import import_health_json_export

    with db.connect() as conn:
        if user_id is None:
            row = conn.execute(
                "SELECT id FROM users ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            if row is None:
                return {
                    "status": "error",
                    "message": "No local user; pass user_id or create a users row first.",
                }
            user_id = row[0]
        return import_health_json_export(conn, export_json_path, user_id)


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "streamable-http":
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")
