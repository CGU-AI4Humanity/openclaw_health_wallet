#!/usr/bin/env bash
# Switch default agent to Qwen 2.5 for health MCP tool calling (delegates to configure_health_assistant.sh).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "${ROOT}/scripts/configure_health_assistant.sh"
