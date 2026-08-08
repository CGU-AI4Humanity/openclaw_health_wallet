# OpenClaw Health Assistant — Step-by-Step Setup Guide

A **local-first personal health companion** on macOS: **OpenClaw** calls MCP tools, **MedGemma** (via **Ollama**) answers using **your** data in **SQLite**—no frontier cloud model required for chat.

> **Medical disclaimer:** Research prototype only—not for diagnosis or treatment decisions.

**Contributors:** Mahesh Balan (integration, Apple Health, PM) · Brandon Medina (SQLite + SQLite MCP) · Leonard Bryant (OpenClaw MCP wiring). See [CONTRIBUTORS.md](./CONTRIBUTORS.md). Monorepo overview: [../README.md](../README.md).

---

## Before you start (checklist)

You will complete these **in order**:

| Step | What | Ollama / OpenClaw chat? |
| --- | --- | --- |
| [1](#step-1-clone-the-repository) | Clone repo | No |
| [2](#step-2-install-system-software) | Node 24, Python, Ollama (install only), OpenClaw CLI | No |
| [3](#step-3-create-local-config-never-commit-secrets) | `config/.env` — FHIR key + your name/DOB | No |
| [4](#step-4-connect-to-the-fhir-mcp-server) | FHIR MCP admin key + patient identity | No |
| [5](#step-5-connect-apple-health-qr--api) | iPhone pairing (QR) → Health API → SQLite | No |
| [6](#step-6-local-sqlite-database) | Initialize DB | No |
| [7](#step-7-sqlite-mcp-server) | Python venv + tools | No |
| [8](#step-8-register-mcp-servers-in-openclaw) | Wire SQLite + FHIR MCP | No |
| [9](#step-9-start-ollama-and-medgemma) | Pull model, point OpenClaw at MedGemma | Start Ollama |
| [10](#step-10-start-openclaw-and-sync-data-once) | `openclaw tui` + one-time sync prompts | **Yes** |
| [11](#step-11-everyday-prompts-sqlite-context--medgemma) | Grounded Q&A | **Yes** |

Do **not** skip to Step 9 until Steps 3–8 are done—otherwise MCP tools and credentials will be missing.

---

## Architecture (what you are wiring)

```mermaid
flowchart LR
  U[User] --> OC[OpenClaw]
  OC --> MG[Ollama MedGemma]
  OC --> SMCP[SQLite MCP]
  OC --> FMCP[FHIR MCP]
  SMCP --> DB[(SQLite cache)]
  PH[iPhone Health Link app] --> API[Local Health API :8765]
  API --> DB
  FMCP --> EHR[FHIR backend]
```

- **[FHIR MCP Server](https://github.com/maheshbalan/fhir-mcp-server)** — hosted API at [mcp-fhir-server.com](https://mcp-fhir-server.com/).
- **[MyWellWallet](https://github.com/maheshbalan/myWellWallet)** — related iOS health wallet research app (FHIR); **not required** for Apple Health pairing in this track.
- **iPhone “Health Link” companion** (thin app) — scans QR, reads HealthKit, POSTs to Mac — see [docs/SETUP_WIZARD_AND_APPLE_HEALTH.md](./docs/SETUP_WIZARD_AND_APPLE_HEALTH.md).

---

## Easiest path: Setup Wizard (recommended for class demo)

One Mac app walks through install checks, FHIR form, QR pairing, and marks steps **done** so you can resume later:

```bash
./scripts/run_setup_wizard.sh
```

Design and iPhone companion plan: **[docs/SETUP_WIZARD_AND_APPLE_HEALTH.md](./docs/SETUP_WIZARD_AND_APPLE_HEALTH.md)**.

Manual steps below match the same order if you prefer the terminal.

## Step 1 — Clone the repository

```bash
git clone https://github.com/CGU-AI4Humanity/openclaw_health_wallet.git
cd openclaw_health_wallet/Openclaw_Health_Assistant
```

---

## Step 2 — Install system software

Install tools only—**do not** start chatting yet.

### 2a. Node.js 24 (required for OpenClaw)

```bash
export NVM_DIR="$HOME/.nvm" && source "$NVM_DIR/nvm.sh"
nvm install 24 && nvm use 24
node -v   # should be v24.x
```

### 2b. OpenClaw CLI

```bash
npm install -g openclaw@latest --allow-scripts openclaw
openclaw --version
```

Optional onboarding (gateway daemon):

```bash
curl -fsSL https://openclaw.ai/install.sh | bash
# or: openclaw onboard --install-daemon
```

Docs: [OpenClaw install](https://docs.openclaw.ai/install/) · [Ollama provider](https://docs.openclaw.ai/providers/ollama) (native URL `http://127.0.0.1:11434` — **never** `/v1`).

### 2c. Ollama (install + service, pull model in Step 9)

```bash
brew install ollama
brew services start ollama
```

### 2d. Python + SQLite

- Python **3.11+** (macOS or Homebrew).
- `sqlite3` (Xcode Command Line Tools).

### 2e. Gateway env for Ollama discovery

```bash
mkdir -p ~/.openclaw
grep -q OLLAMA_API_KEY ~/.openclaw/.env 2>/dev/null || echo 'OLLAMA_API_KEY=ollama-local' >> ~/.openclaw/.env
```

---

## Step 3 — Create local config (never commit secrets)

```bash
cp config/.env.example config/.env
chmod 600 config/.env
```

**Important:** `config/.env` is in [`.gitignore`](./.gitignore). **Never** put API keys, DOB, or health data **in the Git repository**. Admins send keys to you privately; you paste them only into **`config/.env` on your Mac**.

| Variable | You fill in | Purpose |
| --- | --- | --- |
| `FHIR_MCP_API_KEY` | From FHIR MCP admin (Step 4) | Authenticates to hosted FHIR MCP |
| `FHIR_PATIENT_FIRST_NAME` | Your legal first name | Patient search on FHIR server |
| `FHIR_PATIENT_LAST_NAME` | Your legal last name | Patient search |
| `FHIR_PATIENT_DOB` | `YYYY-MM-DD` | Patient search |
| `MYWELLWALLET_DB_PATH` | Usually default | Local SQLite file |
| `FHIR_MCP_BASE_URL` | Usually `https://mcp-fhir-server.com` | API host |
| `APPLE_HEALTH_API_BASE_URL` | After QR pairing | Mac local sync API |
| `APPLE_HEALTH_DEVICE_TOKEN` | After QR pairing | Pairing secret (local `.env` only) |
| `OLLAMA_MEDGEMMA_MODEL` | e.g. `medgemma:4b` | Local LLM tag |

---

## Step 4 — Connect to the FHIR MCP Server

### 4a. Request an API key (admin)

1. Contact the **FHIR MCP Server administrator** for your class or org (see [fhir-mcp-server](https://github.com/maheshbalan/fhir-mcp-server) / course instructions).
2. Admin creates an **`X-API-Key`** for you on the hosted service ([mcp-fhir-server.com](https://mcp-fhir-server.com/)).
3. Admin sends the key through a **private channel** (email, 1Password, etc.)—**not** via a public GitHub issue or commit.
4. You paste the key into **`config/.env`**:

   ```bash
   FHIR_MCP_API_KEY=your-key-here
   FHIR_PATIENT_FIRST_NAME=Jane
   FHIR_PATIENT_LAST_NAME=Doe
   FHIR_PATIENT_DOB=1990-06-15
   ```

These three patient fields are stored locally so OpenClaw **does not ask again every session**—the agent uses them when calling FHIR MCP tools to find **your** record.

### 4b. What the FHIR MCP connection does

OpenClaw talks to **`https://mcp-fhir-server.com/mcp`** over **Streamable HTTP** with header:

`X-API-Key: <FHIR_MCP_API_KEY>`

That is the same pattern as the [MyWellWallet](https://github.com/maheshbalan/myWellWallet) iOS app. Tools fetch FHIR resources (conditions, labs, meds, etc.) and document RAG when enabled on the server.

Actual MCP registration in OpenClaw happens in [Step 8](#step-8-register-mcp-servers-in-openclaw) after `config/.env` is complete.

---

## Step 5 — Connect Apple Health (QR + local API)

Apple Health is authorized on **iPhone**; metrics are sent to a **small HTTP API on your Mac** (no MyWellWallet export path).

### Option A — Setup Wizard (best for demo)

```bash
./scripts/run_setup_wizard.sh
```

1. Open the **Apple Health** tab → **Start pairing + show QR**.
2. On iPhone, open the **Health Link** companion (see [SETUP_WIZARD_AND_APPLE_HEALTH.md](./docs/SETUP_WIZARD_AND_APPLE_HEALTH.md)) and scan the QR.
3. Grant **HealthKit** read access; the phone `POST`s JSON to `http://<your-mac>:8765/v1/health/sync` with header `X-Pairing-Token`.
4. Wizard writes `APPLE_HEALTH_API_BASE_URL` and `APPLE_HEALTH_DEVICE_TOKEN` to **`config/.env`** and loads **`health_*`** SQLite tables.

### Option B — Terminal QR only

```bash
./scripts/apple_health_pairing.sh   # prints QR if qrencode/qrcode installed
# In another terminal, keep pairing server running via the wizard or pairing_server.py
```

### Mac HealthKit (optional accelerator)

If the **Health** app on your Mac already syncs iPhone data, a future native helper can read **Mac HealthKit** directly—same SQLite tables, no phone POST. See design doc **Path A**.

Developer-only tools (`sync_apple_health_from_phone_database`, JSON inbox) remain in SQLite MCP for lab use but are **not** part of the class happy path.

---

## Step 6 — Local SQLite database

Creates an empty MyWellWallet-compatible schema (Brandon Medina):

```bash
./scripts/init_db.sh
```

Default file: `~/.openclaw-health-assistant/mywellwallet.db` (override with `MYWELLWALLET_DB_PATH` in `config/.env`).

Optional: copy a populated test export (PHI—local only):

```bash
./scripts/copy_fixture_db.sh /path/to/mywellwallet.db
```

Schema docs: [db/schema.sql](./db/schema.sql) · [db/SQLITE_SCHEMA.md](./db/SQLITE_SCHEMA.md).

---

## Step 7 — SQLite MCP server

This is a **local Python MCP server** (stdio) that exposes SQLite to OpenClaw—**no API key**; it reads `MYWELLWALLET_DB_PATH`.

```bash
./scripts/setup_sqlite_mcp_venv.sh
```

Main tools (Brandon Medina):

| Tool | Use |
| --- | --- |
| `sqlite_health` | DB path + table counts |
| `list_fhir_patients` / `get_fhir_patient_bundle` | Cached EHR |
| `search_fhir_resources` | Conditions, Observations, etc. |
| `execute_read_query` | Read-only SQL on `health_*` / FHIR tables |
| `upsert_fhir_patient` / `upsert_fhir_resource` | After FHIR MCP fetch |
| `sync_apple_health_from_phone_database` | Interim Apple Health import |
| `get_apple_health_sync_status` | Pairing/sync metadata |

Requires **`mcp[cli]==1.12.4`** (installed by the script).

---

## Step 8 — Register MCP servers in OpenClaw

Leonard Bryant’s wiring script reads **`config/.env`** and registers both servers in `~/.openclaw/openclaw.json`.

```bash
cd /path/to/openclaw_health_wallet/Openclaw_Health_Assistant
export NVM_DIR="$HOME/.nvm" && source "$NVM_DIR/nvm.sh" && nvm use 24
set -a && source config/.env && set +a
./scripts/wire_mcp_servers.sh
```

### What this configures

| OpenClaw name | Type | How it runs |
| --- | --- | --- |
| **`mywellwallet-sqlite`** | stdio | `sqlite-mcp/.venv/bin/python server.py` with env `MYWELLWALLET_DB_PATH=...` |
| **`fhir-remote`** | streamable-http | URL `{FHIR_MCP_BASE_URL}/mcp` + header `X-API-Key: {FHIR_MCP_API_KEY}` |

### Verify connections

```bash
openclaw mcp doctor mywellwallet-sqlite --probe
openclaw mcp doctor fhir-remote --probe
openclaw mcp status --verbose
```

Both should report **ok**. If FHIR fails with 401, recheck `FHIR_MCP_API_KEY` in `config/.env` and re-run `./scripts/wire_mcp_servers.sh`.

Manual reference: [docs/MCP_CONNECTIONS.md](./docs/MCP_CONNECTIONS.md).

---

## Step 9 — Start Ollama and MedGemma

Now start the **local LLM** and bind OpenClaw to it:

```bash
brew services start ollama
ollama pull medgemma:4b
```

**64 GB RAM (e.g. iMac Pro):** optional `ollama pull medgemma:27b` or `ollama pull qwen3:4b`, then set `OLLAMA_MEDGEMMA_MODEL` in `config/.env`.

```bash
./scripts/configure_medgemma.sh
```

This sets default agent model **`ollama/medgemma:4b`** in `~/.openclaw/openclaw.json` (see [config/openclaw.medgemma.patch.json5](./config/openclaw.medgemma.patch.json5)).

Quick Ollama check:

```bash
ollama list
curl -s http://127.0.0.1:11434/api/tags | head
```

---

## Step 10 — Start OpenClaw and sync data (once)

```bash
nvm use 24
openclaw tui
```

Run **one prompt at a time** (copy from below; replace names/DOB with your `config/.env` values).

### Prompt A — Apple Health (after QR/API or interim export)

```text
Use only mywellwallet-sqlite tools.

1. get_current_user → user_id
2. If APPLE_HEALTH is linked via API, confirm with get_apple_health_sync_status.
   If not, call sync_apple_health_from_phone_database using my configured export path.
3. health_metrics_summary for that user_id
4. Summarize available steps, heart rate, glucose, BP, and lab row counts.

Medical disclaimer required.
```

### Prompt B — FHIR MCP → update SQLite cache

Uses **first name, last name, DOB from config/.env** (not from chat memory):

```text
Use fhir-remote MCP tools, then mywellwallet-sqlite to persist locally.

1. Find patient: first name "<FHIR_PATIENT_FIRST_NAME>", last name "<FHIR_PATIENT_LAST_NAME>",
   birth date "<FHIR_PATIENT_DOB>".
2. Fetch Patient, Condition, Observation, MedicationRequest, Immunization, Encounter as available.
3. upsert_fhir_patient and upsert_fhir_resource so SQLite matches the server.
4. sqlite_health and list_fhir_patients to confirm.

Do not ask me for API key or DOB again—they are already configured.
Medical disclaimer required.
```

More prompts: [docs/FIRST_RUN_PROMPTS.md](./docs/FIRST_RUN_PROMPTS.md).

---

## Step 11 — Everyday prompts (SQLite context → MedGemma)

After Steps 10A/B, **routine questions should hit SQLite first**, then MedGemma explains. Paste this **before** your question:

```text
You must use mywellwallet-sqlite before answering.

1. list_fhir_patients (if needed identify my patient_id)
2. search_fhir_resources and/or execute_read_query on health_* tables for data relevant to my question
3. Answer ONLY using retrieved rows plus general education—not guesses
4. If cache might be stale, offer once to refresh via fhir-remote (use configured patient name/DOB)

My question: <write your question here>

Include a medical disclaimer.
```

Example questions:

- “What conditions are in my cached FHIR data?”
- “Summarize my last 30 days of step counts from health_steps.”
- “Explain my latest lab results rows in plain language.”

---

## Optional — one script after `config/.env` is ready

```bash
./scripts/install_local_stack.sh
```

Runs Steps 6–9 automation (venv, DB, MedGemma patch, MCP wire, smoke test). You still complete Steps 3–5 manually first.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `openclaw` Node error | `nvm use 24` |
| SQLite MCP probe fails | `./scripts/setup_sqlite_mcp_venv.sh`; check `MYWELLWALLET_DB_PATH` |
| FHIR MCP 401 | Valid `FHIR_MCP_API_KEY`; re-run `wire_mcp_servers.sh` |
| Wrong patient | Fix `FHIR_PATIENT_*` in `config/.env` |
| Empty `health_*` tables | Complete Step 5 (QR/API or interim sync prompt) |
| Model ignores tools | Confirm `openclaw mcp status`; use explicit “must use mywellwallet-sqlite” prompts |
| Raw JSON tool output | Ollama `baseUrl` must not use `/v1`; re-run `configure_medgemma.sh` |

---

## Repository layout

```text
Openclaw_Health_Assistant/
├── README.md                 ← this guide
├── config/.env.example       ← copy to .env (gitignored)
├── db/                       ← SQLite schema (Brandon)
├── sqlite-mcp/               ← local MCP (Brandon)
├── apple-health-bridge/      ← Health API / sync (Mahesh)
├── docs/MCP_CONNECTIONS.md   ← MCP detail (Leonard)
└── scripts/                  ← install, wire, test, pairing
```

---

## Project lead

**Mahesh Balan** — OpenClaw Health Assistant, CGU IST 362 / DTech.
