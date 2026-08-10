#!/usr/bin/env bash
# Reset local OpenClaw to Brandon health-demo stack (qwen2.5:7b + health MCP only).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/config/.env"
export NVM_DIR="${NVM_DIR:-${HOME}/.nvm}"
# shellcheck disable=SC1091
[[ -s "${NVM_DIR}/nvm.sh" ]] && source "${NVM_DIR}/nvm.sh"
nvm use 24 >/dev/null 2>&1 || true

echo "=== 1. Normalize config/.env (demo DB + PT0001) ==="
if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${ROOT}/config/.env.example" "${ENV_FILE}"
fi
DEMO_DB="${HOME}/.openclaw-health-assistant/final_project.db"
python3 - <<PY
from pathlib import Path
import re
path = Path("${ENV_FILE}")
text = path.read_text(encoding="utf-8")
updates = {
    "HEALTH_DB_PATH": "${DEMO_DB}",
    "OPENCLAW_HEALTH_DB_PATH": "${DEMO_DB}",
    "HEALTH_ACTIVE_USER_ID": "PT0001",
    "OLLAMA_TOOLS_MODEL": "qwen2.5:7b",
}
for key, val in updates.items():
    pat = re.compile(rf"^{re.escape(key)}=.*$", re.M)
    line = f'{key}="{val}"' if "PATH" in key else f"{key}={val}"
    if pat.search(text):
        text = pat.sub(line, text, count=1)
    else:
        text = text.rstrip() + "\n" + line + "\n"
path.write_text(text, encoding="utf-8")
print("Updated", path)
PY

echo "=== 2. Clear stale chat sessions (old qwen3:4b pin) ==="
SESSIONS_DIR="${HOME}/.openclaw/agents/main/sessions"
STAMP="$(date +%Y%m%d-%H%M%S)"
if [[ -d "${SESSIONS_DIR}" ]]; then
  mkdir -p "${HOME}/.openclaw/backups"
  tar -czf "${HOME}/.openclaw/backups/sessions-${STAMP}.tar.gz" -C "${SESSIONS_DIR}" . 2>/dev/null || true
  rm -f "${SESSIONS_DIR}"/*.jsonl "${SESSIONS_DIR}"/*.trajectory.jsonl "${SESSIONS_DIR}/sessions.json" 2>/dev/null || true
  echo "Archived prior sessions to ~/.openclaw/backups/sessions-${STAMP}.tar.gz"
  echo "Start a fresh session on next openclaw chat."
fi
rm -f "${HOME}/.openclaw/tui/last-session.json" 2>/dev/null || true

echo "=== 3. Reset setup wizard progress (optional clean tabs) ==="
rm -f "${HOME}/.openclaw-health-assistant/setup_progress.json"

echo "=== 4. Legacy MCP removal + health MCP wire ==="
# shellcheck disable=SC1090
set -a && source "${ENV_FILE}" && set +a
"${ROOT}/scripts/setup_health_mcp_venv.sh"
"${ROOT}/scripts/seed_demo_database.sh"
python3 - <<PY
import sys
sys.path.insert(0, "${ROOT}/setup-wizard")
from pathlib import Path
from db_utils import ensure_apple_health_tables
ensure_apple_health_tables(Path("${DEMO_DB}"))
print("Apple Health tables OK on demo DB")
PY
"${ROOT}/scripts/cleanup_mcp_servers.sh"

echo "=== 5. Default model qwen2.5:7b + tool allowlist + AGENTS.md ==="
OLLAMA_TOOLS_MODEL=qwen2.5:7b "${ROOT}/scripts/configure_health_assistant.sh"

openclaw config set agents.defaults.model "ollama/qwen2.5:7b"
openclaw config set agents.defaults.model.primary "ollama/qwen2.5:7b" 2>/dev/null || true

echo ""
echo "=== Done ==="
openclaw config get agents.defaults.model
openclaw mcp status --verbose 2>/dev/null | head -12
echo ""
echo "Next: nvm use 24 && openclaw chat   (new session → ollama/qwen2.5:7b)"
echo "Wizard: ./scripts/run_setup_wizard.sh"
