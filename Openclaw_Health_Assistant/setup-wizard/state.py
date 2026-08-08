"""Persist setup wizard step completion."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

STATE_DIR = Path.home() / ".openclaw-health-assistant"
STATE_FILE = STATE_DIR / "setup_progress.json"

STEPS = [
    "prerequisites",
    "sqlite_and_mcp_venv",
    "fhir_config",
    "mcp_wired",
    "apple_health_paired",
    "ollama_medgemma",
    "ready",
]


def load() -> dict[str, Any]:
    if not STATE_FILE.is_file():
        return {"completed": {}, "meta": {}}
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save(data: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def is_done(step: str) -> bool:
    return bool(load().get("completed", {}).get(step))


def mark_done(step: str, **meta: Any) -> None:
    data = load()
    data.setdefault("completed", {})[step] = True
    if meta:
        data.setdefault("meta", {}).update(meta)
    save(data)


def first_incomplete() -> str:
    for step in STEPS:
        if not is_done(step):
            return step
    return STEPS[-1]
