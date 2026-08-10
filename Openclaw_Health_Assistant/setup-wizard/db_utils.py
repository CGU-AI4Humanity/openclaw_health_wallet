"""Resolve and initialize the local SQLite database path for the wizard."""

from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path

DEFAULT_DB = Path.home() / ".openclaw-health-assistant" / "final_project.db"
LEGACY_DB = Path.home() / ".openclaw-health-assistant" / "mywellwallet.db"


def expand_path(raw: str) -> Path:
    text = raw.strip().strip('"').strip("'")
    return Path(os.path.expandvars(os.path.expanduser(text))).resolve()


def resolve_db_path(env: dict[str, str]) -> Path:
    raw = (
        env.get("HEALTH_DB_PATH")
        or env.get("OPENCLAW_HEALTH_DB_PATH")
        or env.get("MYWELLWALLET_DB_PATH")
        or str(DEFAULT_DB)
    )
    return expand_path(raw)


def ensure_apple_health_tables(db: Path) -> None:
    """Add Health Link metadata table if missing (demo DB from seed_database.py)."""
    conn = sqlite3.connect(str(db))
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS health_sync_settings (
              user_id TEXT PRIMARY KEY,
              sync_interval_hours INTEGER NOT NULL DEFAULT 24,
              last_synced_at TEXT,
              connected_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def ensure_database(db: Path, schema_sql: Path) -> tuple[bool, str]:
    """Create parent dir and DB file if missing. Returns (ok, log text)."""
    lines: list[str] = []
    db.parent.mkdir(parents=True, exist_ok=True)
    lines.append(f"Database path: {db}")

    if db.is_file():
        lines.append("Status: using existing file.")
        return True, "\n".join(lines)

    if LEGACY_DB.is_file() and LEGACY_DB.resolve() != db.resolve():
        shutil.copy2(LEGACY_DB, db)
        lines.append(f"Status: copied legacy DB from {LEGACY_DB}")
        return True, "\n".join(lines)

    if not schema_sql.is_file():
        lines.append(f"ERROR: schema not found at {schema_sql}")
        return False, "\n".join(lines)

    conn = sqlite3.connect(str(db))
    try:
        conn.executescript(schema_sql.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()
    lines.append("Status: initialized empty schema (db/schema.sql).")
    return True, "\n".join(lines)


def ensure_local_user(
    db: Path,
    user_id: str | None = None,
    env: dict[str, str] | None = None,
) -> tuple[str, str]:
    """Prefer HEALTH_ACTIVE_USER_ID (demo PT0001) so Apple Health updates the same patient."""
    from datetime import datetime, timezone

    env = env or {}
    preferred = user_id or env.get("HEALTH_ACTIVE_USER_ID") or "PT0001"
    ensure_apple_health_tables(db)

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    conn = sqlite3.connect(str(db))
    try:
        row = conn.execute("SELECT id FROM users WHERE id = ?", (preferred,)).fetchone()
        if row:
            return preferred, f"Using user_id {preferred} (Health Link → health_* for this patient)"

        row = conn.execute(
            "SELECT id FROM users ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if row:
            return row[0], f"Using existing user_id: {row[0]}"

        conn.execute(
            """
            INSERT INTO users (id, name, email, date_of_birth, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                preferred,
                "Local User",
                "local@openclaw.health",
                "1990-01-01T00:00:00.000",
                now,
                now,
            ),
        )
        conn.commit()
        return preferred, f"Created user_id: {preferred}"
    finally:
        conn.close()
