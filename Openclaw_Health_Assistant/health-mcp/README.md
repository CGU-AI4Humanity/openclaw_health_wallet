# Health MCP (typed tools)

Custom MCP server from [Final_Project](../../Final_Project/README.md). The LLM never writes SQL—it calls named tools; Python returns structured vitals/labs with interpretation fields.

```bash
./scripts/setup_health_mcp_venv.sh
HEALTH_DB_PATH=~/.openclaw-health-assistant/final_project.db \
  HEALTH_ACTIVE_USER_ID=PT0001 \
  .venv/bin/python server.py
```

Register with OpenClaw: `./scripts/cleanup_mcp_servers.sh` (server name **`health`**).
