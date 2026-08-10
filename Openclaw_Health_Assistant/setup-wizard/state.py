"""Persist setup wizard step completion and per-tab action logs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_DIR = Path.home() / ".openclaw-health-assistant"
STATE_FILE = STATE_DIR / "setup_progress.json"

STEPS = [
    "prerequisites",
    "demo_db_and_health_mcp",
    "demo_patient",
    "mcp_wired",
    "apple_health_paired",
    "ollama_qwen",
    "ready",
]

TAB_TITLES = {
    "prerequisites": "1 Prereqs",
    "demo_db_and_health_mcp": "2 Demo DB",
    "demo_patient": "3 Patient",
    "mcp_wired": "4 MCP",
    "apple_health_paired": "5 Apple Hlth",
    "ollama_qwen": "6 Qwen 2.5",
    "ready": "7 Ready",
}


def load() -> dict[str, Any]:
    if not STATE_FILE.is_file():
        return {"completed": {}, "logs": {}, "completed_at": {}, "meta": {}}
    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    data.setdefault("logs", {})
    data.setdefault("completed_at", {})
    return data


def save(data: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def is_done(step: str) -> bool:
    return bool(load().get("completed", {}).get(step))


def all_done() -> bool:
    return all(is_done(step) for step in STEPS)


def get_log(step: str) -> str:
    return str(load().get("logs", {}).get(step, ""))


def set_log(step: str, text: str) -> None:
    data = load()
    data.setdefault("logs", {})[step] = text
    save(data)


def mark_done(step: str, log_text: str | None = None, **meta: Any) -> None:
    data = load()
    data.setdefault("completed", {})[step] = True
    data.setdefault("completed_at", {})[step] = (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    )
    if log_text is not None:
        data.setdefault("logs", {})[step] = log_text
    if meta:
        data.setdefault("meta", {}).update(meta)
    save(data)


def tab_label(step: str) -> str:
    base = TAB_TITLES.get(step, step.replace("_", " ")[:14])
    return f"✓ {base}" if is_done(step) else base


def first_incomplete() -> str:
    for step in STEPS:
        if not is_done(step):
            return step
    return STEPS[-1]


def clear_progress() -> None:
    if STATE_FILE.is_file():
        STATE_FILE.unlink()
