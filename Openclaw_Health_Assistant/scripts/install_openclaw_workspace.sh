#!/usr/bin/env bash
# Copy AGENTS.md into OpenClaw workspace (Brandon Medina Final_Project flow)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WS="${OPENCLAW_WORKSPACE:-${HOME}/.openclaw/workspace}"
mkdir -p "${WS}"
cp "${ROOT}/docs/AGENTS.md" "${WS}/AGENTS.md"
# OpenClaw default BOOTSTRAP.md tells the model to roleplay "who am I?" — conflicts with health demo.
rm -f "${WS}/BOOTSTRAP.md"
for f in IDENTITY.md USER.md TOOLS.md HEARTBEAT.md; do
  if [[ ! -f "${WS}/${f}" ]]; then
    echo '# unused' > "${WS}/${f}"
  fi
done
echo "Workspace instructions: ${WS}/AGENTS.md"
