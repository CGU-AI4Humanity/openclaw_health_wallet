#!/usr/bin/env bash
# Qwen 2.5 + health MCP tool allowlist + workspace AGENTS.md (Brandon Medina solution)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NVM_DIR="${NVM_DIR:-${HOME}/.nvm}"
# shellcheck disable=SC1091
[[ -s "${NVM_DIR}/nvm.sh" ]] && source "${NVM_DIR}/nvm.sh"
nvm use 24 >/dev/null 2>&1 || true

mkdir -p "${HOME}/.openclaw"
grep -q 'OLLAMA_API_KEY' "${HOME}/.openclaw/.env" 2>/dev/null || \
  echo 'OLLAMA_API_KEY=ollama-local' >> "${HOME}/.openclaw/.env"

MODEL="${OLLAMA_TOOLS_MODEL:-qwen2.5:7b}"
if ! ollama show "${MODEL}" >/dev/null 2>&1; then
  echo "Pulling ${MODEL}..."
  ollama pull "${MODEL}"
fi

openclaw config patch --file "${ROOT}/config/openclaw.qwen25.patch.json5"
openclaw config patch --file "${ROOT}/config/openclaw.timeouts.patch.json5"
openclaw config patch --file "${ROOT}/config/openclaw.health-tools.patch.json5"
openclaw config set agents.defaults.model "ollama/${MODEL}"
openclaw config set agents.defaults.model.primary "ollama/${MODEL}" 2>/dev/null || true
openclaw doctor --fix 2>/dev/null || true
openclaw config validate

"${ROOT}/scripts/install_openclaw_workspace.sh"

echo "Default agent: ollama/${MODEL} with health__* tool allowlist."
echo "Start chat: nvm use 24 && openclaw chat (or Control UI after gateway restart)."
