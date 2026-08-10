#!/usr/bin/env python3
"""Remove legacy MCP server keys from ~/.openclaw/openclaw.json."""

from __future__ import annotations

import json
from pathlib import Path

KEEP = {"health", "fhir-remote"}

LEGACY_KEYS = {
    "mywellwallet-sqlite",
    "mywellwallet_sqlite",
    "openclaw_health_sqlite",
    "openclaw-health-sqlite",
    "fhir-remote",
    "health-mcp",
}


def prune(path: Path) -> list[str]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    servers = data.get("mcp", {}).get("servers")
    if not isinstance(servers, dict):
        return []
    removed: list[str] = []
    for key in list(servers.keys()):
        if key in KEEP:
            continue
        if key in LEGACY_KEYS or "mywellwallet" in key.lower():
            del servers[key]
            removed.append(key)
    if removed:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return removed


def main() -> None:
    cfg = Path.home() / ".openclaw" / "openclaw.json"
    removed = prune(cfg)
    for name in removed:
        print(f"Removed mcp.servers.{name} from {cfg}")
    if not removed:
        print("No legacy MCP server keys in openclaw.json")


if __name__ == "__main__":
    main()
