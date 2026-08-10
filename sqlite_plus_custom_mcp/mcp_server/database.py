from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import config

logger = logging.getLogger(__name__)


def _dict_factory(cursor: sqlite3.Cursor, row: tuple[Any, ...]) -> dict[str, Any]:
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    uri = f"file:{config.DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = _dict_factory
    try:
        yield conn
    finally:
        conn.close()


def query_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with get_connection() as conn:
        return conn.execute(sql, params).fetchall()


def query_one(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with get_connection() as conn:
        return conn.execute(sql, params).fetchone()


def resolve_active_user_id() -> str:
    if config.ACTIVE_USER_ID:
        return config.ACTIVE_USER_ID
    row = query_one("SELECT id FROM users ORDER BY created_at LIMIT 1")
    if row is None:
        raise RuntimeError("No users found in the database.")
    return row["id"]
