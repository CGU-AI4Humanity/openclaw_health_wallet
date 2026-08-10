# Local AI Health Data Assistant

A fully-local, private assistant that answers natural-language questions about a
patient's health data — _"what's my most recent A1C, and is it in range?"_ — by
querying a local SQLite database through a custom **Model Context Protocol (MCP)**
server, with a local LLM (via **Ollama**) doing the natural-language part.

The LLM **never writes SQL and never touches the database directly.** It calls
purpose-built healthcare tools (`get_latest_blood_pressure`, `get_lab_results`,
…); deterministic Python runs the query, computes any interpretation
(in-range / out-of-range, trend), and hands back a structured result the model
simply narrates. This is what keeps answers accurate instead of hallucinated.

```
You ─▶ OpenClaw (agent + MCP client) ─▶ Ollama (llama3.2 / qwen2.5)
                    │
                    ▼  calls a named tool (never SQL)
         Custom Health MCP Server (Python)
                    │
                    ▼  deterministic query + interpretation
              SQLite (FHIR-derived synthetic data)
```

> All data is **synthetic**.

---

## Repository layout

```
.
├── README.md
├── schema.csv
├── data/
│   ├── users.csv
│   ├── health_blood_pressure.csv
│   ├── health_glucose.csv
│   ├── health_heart_rate.csv
│   ├── health_lab_results.csv
│   ├── health_steps.csv
│   ├── fhir_patients.csv
│   └── fhir_resources.csv
├── seed_database.py            # builds final_project.db from schema + data/
├── final_project.db
├── docs/
│   └── AGENTS.md              # agent instructions (copied into the OpenClaw workspace)
└── mcp_server/
    ├── config.py             # DB path + active patient + logging
    ├── database.py           # read-only SQLite access layer
    ├── models.py             # Pydantic result types
    ├── interpret.py          # deterministic range/trend interpretation
    ├── server.py             # MCP server entry point (FastMCP)
    └── tools/
        ├── __init__.py
        ├── patients.py       # get_patient
        ├── vitals.py         # get_latest_blood_pressure / glucose / heart_rate
        └── labs.py           # list_lab_tests / get_lab_results / get_recent_lab_results
```

---

## Prerequisites

- **macOS** (these steps are written for macOS)
- **Python 3.10+** (the MCP SDK requires it). Check with `python3 --version`.
- **Node.js** — only needed for the optional MCP Inspector (`npx`).
- **Homebrew** — convenient for installing `uv`/Ollama, but not required.

Throughout, replace `PROJECT_DIR` with the absolute path to this repo, e.g.:

```bash
export PROJECT_DIR="$HOME/openclaw_health_wallet/sqlite_plus_custom_mcp"
```

> **Absolute paths matter.** OpenClaw launches the MCP server as a background
> process with its own working directory, so anywhere a path is passed to OpenClaw

---

## Step 1 — Install Ollama and pull a tool-capable model

```bash
# Install (Homebrew) — or download the app from https://ollama.com
brew install ollama

# Start the Ollama service (or launch the Ollama.app so it runs in the menu bar)
ollama serve

# Pull the model that will drive the tools
ollama pull qwen2.5:7b
```

**The model must support tool calling.** Verify:

```bash
curl http://localhost:11434/api/tags
```

Look for `"capabilities":[... "tools"]` on your model.

- `llama3.2` ✅ has `tools`
- **Recommended:** `qwen2.5:7b` (`ollama pull qwen2.5:7b`). It is tool-capable and more reliably picks the right tool and answers concisely.

Confirm Ollama is reachable:

```bash
ollama list                       # your models should be listed
# Visiting http://localhost:11434 in a browser shows "Ollama is running" — that is correct.
```

---

## Step 2 — Install OpenClaw and run the gateway as a service

```bash
npm install -g openclaw
# or follow https://docs.openclaw.ai install docs
openclaw gateway install
openclaw status                  # Gateway should show: reachable ... running
```

Point OpenClaw at Ollama with the onboarding wizard:

```bash
openclaw onboard                 # choose Ollama → local-only → select your model
```

> **Critical:** the Ollama base URL needs to be `http://localhost:11434` **without**
> `/v1`. The `/v1` (the model emits tool calls as plain text the agent can't dispatch).
> The model id should be `ollama/llama3.2` (or `ollama/qwen2.5:7b`).

---

## Step 3 — Build the database and seed it

The synthetic data ships as CSVs in `data/`. Build the SQLite database from the
schema + data:

```bash
cd "$PROJECT_DIR"
python3 seed_database.py
```

Expected output (row counts will match the shipped data):

```
OK    users: 30 rows
OK    health_lab_results: 150 rows
OK    health_steps: 900 rows
...
Built .../final_project.db
```

> The dataset contains **30 synthetic patients** as a test fixture. The deployed
> product is single-tenant (one person per device), so the assistant is configured
> to **one active patient** (Step 5). To demo a different patient, change that one
> setting — no code changes.

Sanity-check the build:

```bash
sqlite3 final_project.db "SELECT COUNT(*) FROM users;"
sqlite3 final_project.db "SELECT DISTINCT name FROM health_lab_results;"
```

---

## Step 4 — Set up the MCP server

```bash
cd "$PROJECT_DIR"
python3 -m venv venv_362
source venv_362/bin/activate
pip install -r mcp_server/requirements.txt
```

`mcp_server/requirements.txt` pins the SDK:

```
mcp==1.13.1
```

> **Do not let this resolve to mcp 2.x.** Version 2.0 relocated `FastMCP` and
> removed APIs the tooling depends on — it breaks the import on the first line.
> Pin `mcp==1.13.1` (or `mcp>=1.2,<2`).

Test the server in isolation (it should print a startup line, then block waiting
for a client — `Ctrl-C` to stop):

```bash
HEALTH_DB_PATH="$PROJECT_DIR/final_project.db" \
  python mcp_server/server.py
# 2026-... INFO health-mcp: Starting health-mcp (db=.../final_project.db)
```

---

## Step 5 — Register the server with OpenClaw

Register your server, pointing at the **venv's** Python (so `mcp` is importable),
your database, and the single active patient:

```bash
openclaw mcp add health \
  --command "$PROJECT_DIR/venv_362/bin/python" \
  --arg     "$PROJECT_DIR/mcp_server/server.py" \
  --env     HEALTH_DB_PATH="$PROJECT_DIR/final_project.db" \
  --env     HEALTH_ACTIVE_USER_ID=PT0001

# Verify OpenClaw can launch it and see the tools:
openclaw mcp doctor health --probe        # expect: health: ok
openclaw mcp probe  health --json         # lists the tools (8 health__* tools)
```

`HEALTH_ACTIVE_USER_ID=PT0001` is what makes the assistant single-tenant. Change it
to `PT0002`, etc., and restart to demo another patient.

---

## Step 6 — Lock the tool allowlist

Restrict the agent to **only** your health tools. This is what prevents the model
from reaching for `web_search`, a messaging tool, or a file editor when asked a
health question. Use the **explicit list** (the `health__*` wildcard proved
unreliable):

```bash
openclaw config set tools.allow '[
  "health__ping",
  "health__get_patient",
  "health__get_latest_blood_pressure",
  "health__get_latest_glucose",
  "health__get_latest_heart_rate",
  "health__list_lab_tests",
  "health__get_lab_results",
  "health__get_recent_lab_results"
]' --strict-json

openclaw gateway restart
```

---

## Step 7 — Set the agent model and workspace instructions

Make sure the agent's model is your tool-capable model:

```bash
openclaw config set agents.defaults.model.primary "ollama/llama3.2"   # or ollama/qwen2.5:7b
openclaw config get agents.defaults.model.fallbacks
```

Copy the agent instructions into the OpenClaw workspace:

```bash
cp docs/AGENTS.md ~/.openclaw/workspace/AGENTS.md

cd ~/.openclaw/workspace
for f in IDENTITY.md USER.md TOOLS.md HEARTBEAT.md; do echo '# unused' > "$f"; done
```

`docs/AGENTS.md` tells the model to call the health tools, how to
narrate the interpretation fields (`range_status`, `trend`), the scope boundary
(state in/out of range and trend, **never diagnose**), and to pass a named test to
`get_lab_results` rather than substituting a different one.

Restart to load everything:

```bash
openclaw gateway restart
```

---

## Step 8 — Open OpenClaw Control

The Gateway serves a web UI. It requires the gateway auth token on first use.

```bash
grep -m1 '"token"' ~/.openclaw/openclaw.json     # copy the token value
```

Open the dashboard with the token:

```
http://127.0.0.1:18789/?token=YOUR_TOKEN_HERE
```

---

## Step 9 — Operation

Start a **fresh** session in the dashboard and ask, in plain language:

- "What's my most recent blood pressure?"
- "What's my latest glucose reading?"
- "What was my most recent A1C, and is it in range?"
- "List my recent lab results."

You should see a **tool card** showing which tool ran and the structured JSON it
returned, followed by a one- or two-sentence answer with the value, its unit, the
date, and (for labs) whether it's in range and its trend.

### Daily startup (after a reboot)

The Gateway auto-starts as a service; you only need Ollama up.

```bash
ollama list        # Ollama running? (models listed = yes)
openclaw status    # Gateway reachable?
# open the dashboard → new session → ask
```

You do **not** start the MCP server yourself — OpenClaw launches it on demand.

---

## Available tools

| Tool                        | Answers                                                      |
| --------------------------- | ------------------------------------------------------------ |
| `get_patient`               | name, age, demographics of the active patient                |
| `get_latest_blood_pressure` | most recent BP (systolic/diastolic, mmHg)                    |
| `get_latest_glucose`        | most recent blood glucose                                    |
| `get_latest_heart_rate`     | most recent heart rate                                       |
| `list_lab_tests`            | which lab tests are on record                                |
| `get_lab_results`           | most recent result for a named test (+ range status + trend) |
| `get_recent_lab_results`    | recent results across all tests                              |

Lab results carry a real `reference_range_low/high` in the data, so "in range" is
**data-driven**. Trend is computed from the patient's history in `interpret.py`.
The model only narrates these fields — it never computes them.

---
