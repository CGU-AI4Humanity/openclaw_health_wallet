# Setup — OpenClaw, Ollama, MedGemma, MCP

**Mahesh Balan** — stack overview · **Brandon Medina** — [SQLite / db/README.md](../db/README.md) · **Leonard Bryant** — [MCP connections](./MCP_CONNECTIONS.md)

Step-by-step for the OpenClaw Health Assistant track. Adjust paths if you keep the repo outside `~/openclaw_health_wallet`.

## Prerequisites

- macOS (Apple Silicon or Intel with enough RAM for MedGemma 4B — 8 GB+ recommended)
- Node.js 22+ (OpenClaw installer can provision Node)
- Python 3.11+ (for local MCP, same stack as Zero_Claw retina-mcp)
- SQLite CLI (`sqlite3`)

## 1. Clone this repository

```bash
git clone https://github.com/CGU-AI4Humanity/openclaw_health_wallet.git
cd openclaw_health_wallet/Openclaw_Health_Assistant
```

## 2. Install OpenClaw

Official installer:

```bash
curl -fsSL https://openclaw.ai/install.sh | bash
openclaw onboard --install-daemon
```

Alternative with Ollama integration ([Ollama × OpenClaw](https://docs.ollama.com/integrations/openclaw)):

```bash
ollama launch openclaw --model medgemma:4b --yes
```

Verify:

```bash
openclaw doctor
```

## 3. Install Ollama and MedGemma

```bash
# Install Ollama from https://ollama.com/download if needed
ollama pull medgemma:4b
ollama list
```

Enable local provider discovery for the gateway daemon:

```bash
export OLLAMA_API_KEY=ollama-local
```

Add to `~/.openclaw/.env` so the daemon sees Ollama:

```bash
OLLAMA_API_KEY=ollama-local
```

Point the default agent model at MedGemma using [config/openclaw.example.json5](../config/openclaw.example.json5) or set in onboarding. **Do not** set `baseUrl` to `http://127.0.0.1:11434/v1` — that breaks tool calling ([Ollama provider docs](https://docs.openclaw.ai/providers/ollama)).

OpenClaw recommends **≥64k context** for local agents; MedGemma 4B advertises a large window on Ollama — set `contextWindow` explicitly if doctor warns about context.

## 4. Local SQLite database (Brandon Medina)

See [db/README.md](../db/README.md).

```bash
cp config/.env.example config/.env
# Edit FHIR_MCP_API_KEY and OPENCLAW_HEALTH_DB_PATH if needed
chmod +x scripts/init_db.sh
./scripts/init_db.sh
```

Schema reference: [db/SQLITE_SCHEMA.md](../db/SQLITE_SCHEMA.md).

## 5. Remote FHIR MCP (Leonard Bryant)

See [MCP_CONNECTIONS.md](./MCP_CONNECTIONS.md). Endpoint summary:

Same endpoint as [MyWellWallet](https://github.com/maheshbalan/myWellWallet) mobile client: base URL `https://mcp-fhir-server.com`, path `/mcp`, header `X-API-Key`. Server source: [github.com/maheshbalan/fhir-mcp-server](https://github.com/maheshbalan/fhir-mcp-server).

CLI (headers for API key may require Control UI or config secrets — use whichever `openclaw doctor` accepts on your version):

```bash
openclaw mcp add fhir-remote \
  --url https://mcp-fhir-server.com/mcp \
  --transport streamable-http

openclaw mcp doctor fhir-remote --probe
```

If probe fails on auth, add the API key through **Settings → MCP → fhir-remote → Headers** in the Control UI, or the secret mechanism documented in [Connect MCP servers](https://docs.openclaw.ai/tools/mcp).

Store the key in `config/.env` as `FHIR_MCP_API_KEY` for local scripts; do not commit it.

## 6. Local SQLite MCP (Brandon Medina — server; Leonard Bryant — OpenClaw connect)

Pattern follows `Zero_Claw-Retina_Health-Assistant/retina-mcp/`:

```bash
openclaw mcp add openclaw-health-sqlite \
  --command python3 \
  --arg server.py \
  --cwd "$(pwd)/sqlite-mcp"
```

Implement `sqlite-mcp/server.py` with FastMCP tools: `health_check`, `list_patients`, `get_patient_bundle`, `query_readonly_sql`, etc.

## 7. Apple Health (Mahesh Balan)

See [apple-health-bridge/README.md](../apple-health-bridge/README.md). On macOS, plan for Health app data synced from iPhone or controlled export; full HealthKit parity may require a small native helper or Shortcuts automation feeding the bridge.

## 8. End-to-end smoke test (after MCP implementations)

```bash
openclaw mcp status --verbose
openclaw mcp doctor fhir-remote --probe
# openclaw mcp doctor openclaw-health-sqlite --probe
```

Chat example (Control UI or CLI):

```text
List my locally cached FHIR patients from SQLite, then if online fetch the latest
conditions for the first patient from the FHIR MCP server and summarize in plain language.
Include a medical disclaimer.
```

## Troubleshooting

| Issue | Fix |
| --- | --- |
| Ollama tools not discovered | Set `OLLAMA_API_KEY=ollama-local` in `~/.openclaw/.env`, restart gateway |
| Raw JSON tool calls in chat | Remove `/v1` from Ollama `baseUrl`; use `api: "ollama"` |
| MCP session errors on FHIR | Match mobile flow: initialize → session id → tool calls with `X-API-Key` |
| Empty local DB | Run `./scripts/init_db.sh`, then sync from FHIR MCP |
