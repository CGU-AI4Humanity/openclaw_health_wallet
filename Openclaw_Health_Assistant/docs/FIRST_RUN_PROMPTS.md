# First-run prompts (Brandon Medina health MCP + synthetic demo DB)

Use **after** [README.md](../README.md) quick start or the setup wizard.

```bash
cd Openclaw_Health_Assistant
nvm use 24
./scripts/install_local_stack.sh    # seed demo DB, health MCP, qwen2.5:7b, tool allowlist
openclaw chat
```

**Model:** `ollama/qwen2.5:7b` only for tool calling (`ollama show qwen2.5:7b | grep tools`).

**Do not use MedGemma or raw SQLite/FHIR MCP** for this demo — the agent uses typed **`health__*`** tools only.

In chat (optional, speeds up Qwen):

```text
/think off
/verbose on
```

> Medical disclaimer: synthetic data; not medical advice.

---

## Example questions (no paste prompt required)

Ask in plain language after `openclaw chat`:

- What's my most recent blood pressure?
- What's my latest glucose reading?
- What was my most recent A1C, and is it in range?
- List my recent lab results.

The agent should call **`health__get_*`** tools and narrate structured results (`range_status`, `trend`).

---

## Demo patient

Default active patient: **`PT0001`** (`HEALTH_ACTIVE_USER_ID` in `config/.env`).

Align local demo identity with your FHIR demo patient (same name/DOB, no FHIR pull in chat):

```bash
# config/.env
FHIR_PATIENT_FIRST_NAME=Ruben688
FHIR_PATIENT_LAST_NAME=Waters156
FHIR_PATIENT_DOB=1972-08-02

./scripts/sync_demo_patient_from_env.sh
```

**FHIR MCP (demo connectivity only):** set `FHIR_MCP_API_KEY`, run `./scripts/cleanup_mcp_servers.sh`, then `openclaw mcp doctor fhir-remote --probe`. Chat answers still use **`health__*`** tools only.

---

## Legacy: remote FHIR + Apple Health

The older **`openclaw-health-sqlite`** + **`fhir-remote`** flow remains in git history; the class path is **`health`** MCP + **`demo/csv`** (see [sqlite_plus_custom_mcp](../../sqlite_plus_custom_mcp/README.md)).
