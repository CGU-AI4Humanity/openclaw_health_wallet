#!/usr/bin/env bash
# Switch default agent to Qwen3 for reliable Ollama MCP tool calling.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NVM_DIR="${NVM_DIR:-${HOME}/.nvm}"
# shellcheck disable=SC1091
[[ -s "${NVM_DIR}/nvm.sh" ]] && source "${NVM_DIR}/nvm.sh"
nvm use 24 >/dev/null 2>&1 || true

mkdir -p "${HOME}/.openclaw"
grep -q 'OLLAMA_API_KEY' "${HOME}/.openclaw/.env" 2>/dev/null || \
  echo 'OLLAMA_API_KEY=ollama-local' >> "${HOME}/.openclaw/.env"

MODEL="${OLLAMA_TOOLS_MODEL:-qwen3:4b}"
if ! ollama list 2>/dev/null | grep -q "${MODEL%%:*}"; then
  echo "Pulling ${MODEL}..."
  ollama pull "${MODEL}"
fi

openclaw config patch --file "${ROOT}/config/openclaw.qwen-tools.patch.json5"
openclaw doctor --fix 2>/dev/null || true
openclaw config validate
echo "Default agent model: ollama/${MODEL} (MCP tool calling). Switch back to medgemma:4b in config when chatting without tools."
