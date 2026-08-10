# Architecture — OpenClaw Health Assistant

**Project management & Apple Health:** Mahesh Balan · **SQLite & testing:** Brandon Medina · **MCP connections:** Leonard Bryant · See [CONTRIBUTORS.md](../CONTRIBUTORS.md).

## Design principles

1. **Parity with MyWellWallet** — Local persistence uses the same table layout and FHIR JSON in `fhir_bundle` / `resource_data` columns so fixtures, exports, and future mobile sync stay compatible.
2. **Agent-native access** — OpenClaw never opens SQLite directly; it uses MCP tools with explicit, auditable operations (list patients, fetch bundle, run approved queries, upsert after FHIR fetch).
3. **Hybrid data plane** — Local DB holds cached FHIR + Apple Health metrics; remote [FHIR MCP Server](https://github.com/maheshbalan/fhir-mcp-server) ([API](https://mcp-fhir-server.com/)) handles authoritative FHIR CRUD, LOINC lookup, and document RAG when online.
4. **Local medical LLM** — [MedGemma on Ollama](https://ollama.com/library/medgemma) aligns with the mobile app’s MedGemma direction while keeping inference on-device.

## Components

| Layer | Technology | Owner | Notes |
| --- | --- | --- | --- |
| Agent | OpenClaw gateway + TUI/Control UI | Mahesh Balan | MCP via `mcp.servers` ([docs](https://docs.openclaw.ai/tools/mcp)) |
| LLM | Ollama **`qwen3:4b`** (MCP tools) · optional **`medgemma:4b`** (chat only) | Mahesh Balan | Native URL `http://127.0.0.1:11434` (no `/v1`) |
| Local tools | `sqlite-mcp` (FastMCP, stdio or streamable-http) | Brandon Medina (server); Leonard Bryant (OpenClaw connect) | Mirrors Santanu’s retina-mcp pattern in Zero_Claw |
| Remote FHIR | `https://mcp-fhir-server.com/mcp` | Leonard Bryant | Streamable HTTP + `X-API-Key`, same as iOS `MCPClientSSE` |
| Wearables | `apple-health-bridge` | Mahesh Balan | macOS Health / export / HealthKit helper → SQLite health_* tables |

## Data flow

### FHIR sync (target)

1. User asks OpenClaw to refresh records from the FHIR backend.
2. Agent calls remote MCP tools (e.g. patient search, resource fetch).
3. A sync tool (local MCP or agent skill) writes bundles into `fhir_patients` and denormalized rows into `fhir_resources`.
4. MedGemma answers from local cache when offline; can re-fetch when online.

### Apple Health (target)

1. Bridge reads authorized metrics (steps, heart rate, BP, glucose, labs).
2. Rows inserted into `health_*` with `user_id` matching `users.id`.
3. Agent correlates FHIR Observations with local wearable series via MCP query tools.

## Security

- API keys and DB paths only in `config/.env` or OpenClaw secret store.
- Default bind: localhost for local MCP HTTP transports.
- No PHI in git; sample data under `fixtures/` (future) must be synthetic.

## Reference implementation

MyWellWallet iOS ([github.com/maheshbalan/myWellWallet](https://github.com/maheshbalan/myWellWallet)): `DatabaseService`, `MCPClientSSE`, `AppleHealthService`.
