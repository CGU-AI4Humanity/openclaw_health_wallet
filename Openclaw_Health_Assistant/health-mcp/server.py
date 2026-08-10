from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

import config
from database import resolve_active_user_id
from tools import patients, vitals, labs

config.configure_logging()
logger = logging.getLogger("health-mcp")

mcp = FastMCP("health-mcp")


@mcp.tool()
def ping() -> dict:
    user_id = resolve_active_user_id()
    return {
        "status": "ok",
        "active_user_id": user_id,
        "db_path": str(config.DB_PATH),
    }

patients.register(mcp)
vitals.register(mcp)
labs.register(mcp)

if __name__ == "__main__":
    logger.info("Starting health-mcp (db=%s)", config.DB_PATH)
    mcp.run()  # stdio transport by default