"""SQLite access for MyWellWallet-compatible schema."""

from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DB = Path.home() / ".openclaw-health-assistant" / "mywellwallet.db"

_READ_ONLY = re.compile(
    r"^\s*(SELECT|WITH|PRAGMA\s+(table_info|database_list|foreign_key_list))\b",
    re.IGNORECASE | re.DOTALL,
)
_FORBIDDEN = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|REPLACE|ATTACH|DETACH|VACUUM|REINDEX)\b",
    re.IGNORECASE,
)


def db_path() -> Path:
    return Path(os.environ.get("MYWELLWALLET_DB_PATH", str(DEFAULT_DB)))


def connect() -> sqlite3.Connection:
    path = db_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"Database not found at {path}. Run ../scripts/init_db.sh or ../scripts/copy_fixture_db.sh."
        )
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def ensure_schema(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    return [r[0] for r in cur.fetchall()]


def validate_readonly_sql(sql: str) -> str:
    text = sql.strip().rstrip(";")
    if not text:
        raise ValueError("Empty SQL")
    if ";" in text:
        raise ValueError("Only a single statement is allowed")
    if _FORBIDDEN.search(text):
        raise ValueError("Only read-only SELECT/WITH/PRAGMA queries are allowed")
    if not _READ_ONLY.match(text):
        raise ValueError("Query must start with SELECT, WITH, or allowed PRAGMA")
    return text
