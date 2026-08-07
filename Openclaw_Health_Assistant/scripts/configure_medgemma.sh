#!/usr/bin/env bash
# OpenClaw + Ollama MedGemma — Mahesh Balan
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NVM_DIR="${NVM_DIR:-${HOME}/.nvm}"
# shellcheck disable=SC1091
[[ -s "${NVM_DIR}/nvm.sh" ]] && source "${NVM_DIR}/nvm.sh"
nvm use 24 >/dev/null 2>&1 || true

mkdir -p "${HOME}/.openclaw"
grep -q 'OLLAMA_API_KEY' "${HOME}/.openclaw/.env" 2>/dev/null || \
  echo 'OLLAMA_API_KEY=ollama-local' >> "${HOME}/.openclaw/.env"

if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  brew services start ollama 2>/dev/null || true
  sleep 2
fi

MODEL="${OLLAMA_MEDGEMMA_MODEL:-medgemma:4b}"
if ! ollama list 2>/dev/null | grep -q "${MODEL%%:*}"; then
  echo "Pulling ${MODEL}..."
  ollama pull "${MODEL}"
fi

openclaw config patch --file "${ROOT}/config/openclaw.medgemma.patch.json5"
openclaw config validate
echo "Default agent model: ollama/medgemma:4b"
