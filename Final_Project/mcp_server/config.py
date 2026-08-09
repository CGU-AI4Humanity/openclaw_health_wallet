from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

DB_PATH: Path = Path(os.environ.get("HEALTH_DB_PATH", "Final_Project/final_project.db")).resolve()

ACTIVE_USER_ID: str | None = os.environ.get("HEALTH_ACTIVE_USER_ID")

LOG_LEVEL: str = os.environ.get("HEALTH_LOG_LEVEL", "INFO").upper()


def configure_logging() -> None:
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
