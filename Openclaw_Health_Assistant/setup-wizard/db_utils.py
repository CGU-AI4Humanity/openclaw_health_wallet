"""Resolve and initialize the local SQLite database path for the wizard."""

from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path

DEFAULT_DB = Path.home() / ".openclaw-health-assistant" / "openclaw_health.db"
LEGACY_DB = Path.home() / ".openclaw-health-assistant" / "mywellwallet.db"


def expand_path(raw: str) -> Path:
    text = raw.strip().strip('"').strip("'")
    return Path(os.path.expandvars(os.path.expanduser(text))).resolve()


def resolve_db_path(env: dict[str, str]) -> Path:
    raw = (
        env.get("OPENCLAW_HEALTH_DB_PATH")
        or env.get("MYWELLWALLET_DB_PATH")
        or str(DEFAULT_DB)
    )
    return expand_path(raw)


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


def ensure_local_user(db: Path, user_id: str = "local_user_1") -> tuple[str, str]:
    """Ensure at least one users row exists for Health Link sync."""
    import sqlite3
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    conn = sqlite3.connect(str(db))
    try:
        row = conn.execute(
            "SELECT id FROM users ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if row:
            return row[0], f"Using existing user_id: {row[0]}"
        conn.execute(
            """
            INSERT INTO users (id, name, email, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, "Local User", "local@openclaw.health", now, now),
        )
        conn.commit()
        return user_id, f"Created local user_id: {user_id}"
    finally:
        conn.close()
