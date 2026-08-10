#!/usr/bin/env bash
# Stack setup: Mahesh Balan (orchestration), Brandon Medina (DB/venv), Leonard Bryant (openclaw mcp add)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/config/.env"

export NVM_DIR="${NVM_DIR:-${HOME}/.nvm}"
# shellcheck disable=SC1091
[[ -s "${NVM_DIR}/nvm.sh" ]] && source "${NVM_DIR}/nvm.sh"

need_node() {
  if ! command -v node >/dev/null 2>&1; then
    echo "Node not found" >&2
    exit 1
  fi
  local major
  major="$(node -p "process.versions.node.split('.')[0]")"
  if [[ "${major}" -lt 22 ]]; then
    echo "Installing Node 24 via nvm (OpenClaw requires Node >= 22.22.3)..."
    nvm install 24
    nvm use 24
  fi
}

need_node

if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${ROOT}/config/.env.example" "${ENV_FILE}"
  echo "Created ${ENV_FILE} — set FHIR_MCP_API_KEY before FHIR probe."
fi
# shellcheck disable=SC1090
source "${ENV_FILE}"

"${ROOT}/scripts/setup_sqlite_mcp_venv.sh"
"${ROOT}/scripts/init_db.sh"

if [[ -n "${COPY_FIXTURE:-}" ]]; then
  "${ROOT}/scripts/copy_fixture_db.sh" "${COPY_FIXTURE}"
fi

OLLAMA_BIN="${OLLAMA_BIN:-/usr/local/opt/ollama/bin/ollama}"
if [[ ! -x "${OLLAMA_BIN}" ]] && command -v ollama >/dev/null 2>&1; then
  OLLAMA_BIN="$(command -v ollama)"
fi

if [[ -x "${OLLAMA_BIN}" ]]; then
  if ! curl -fsS "${OLLAMA_HOST:-http://127.0.0.1:11434}/api/tags" >/dev/null 2>&1; then
    echo "Starting Ollama..."
    brew services start ollama 2>/dev/null || "${OLLAMA_BIN}" serve &
    sleep 3
  fi
  echo "Pulling ${OLLAMA_MEDGEMMA_MODEL:-medgemma:4b} (may take several minutes)..."
  "${OLLAMA_BIN}" pull "${OLLAMA_MEDGEMMA_MODEL:-medgemma:4b}"
else
  echo "Ollama not found. Install: brew install ollama" >&2
fi

mkdir -p "${HOME}/.openclaw"
grep -q 'OLLAMA_API_KEY' "${HOME}/.openclaw/.env" 2>/dev/null || \
  echo 'OLLAMA_API_KEY=ollama-local' >> "${HOME}/.openclaw/.env"

"${ROOT}/scripts/configure_qwen_tools.sh" || true
"${ROOT}/scripts/cleanup_mcp_servers.sh" || true

echo ""
echo "Default MCP agent: ollama/qwen3:4b (configure_qwen_tools.sh)"
echo "Run: openclaw doctor && openclaw mcp status --verbose && openclaw chat"
