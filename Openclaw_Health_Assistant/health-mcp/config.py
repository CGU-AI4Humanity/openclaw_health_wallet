from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

_ASSISTANT_ROOT = Path(__file__).resolve().parent.parent

DB_PATH: Path = Path(
    os.environ.get(
        "HEALTH_DB_PATH",
        Path.home() / ".openclaw-health-assistant" / "final_project.db",
    )
).expanduser().resolve()

ACTIVE_USER_ID: str | None = os.environ.get("HEALTH_ACTIVE_USER_ID", "PT0001") or None

LOG_LEVEL: str = os.environ.get("HEALTH_LOG_LEVEL", "INFO").upper()


def configure_logging() -> None:
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
