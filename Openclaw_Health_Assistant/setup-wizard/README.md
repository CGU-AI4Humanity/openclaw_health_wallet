# Setup Wizard

macOS **Tkinter** assistant for the **health MCP demo stack**:

```bash
./scripts/run_setup_wizard.sh
```

| Tab | Action |
|-----|--------|
| 1 Prereqs | Node 24, Ollama, OpenClaw, Python, sqlite3 |
| 2 Demo DB | Seed `final_project.db` + health MCP venv |
| 3 Patient | PT0001, FHIR name/DOB, API key → `config/.env` + SQLite sync |
| 4 MCP | `health` + optional `fhir-remote` probe |
| 5 Apple Hlth | QR pairing (optional) or **Skip** for synthetic demo |
| 6 Qwen 2.5 | `qwen2.5:7b` + tool allowlist + `AGENTS.md` |
| 7 Ready | Mark complete · **Re-verify setup** |

**Tonight:** Step 1 → **Run complete setup (all steps)**.  
**Tomorrow:** Re-open the wizard — tabs show **✓**, action logs restored from `~/.openclaw-health-assistant/setup_progress.json`. Walk through each tab for the demo.

To start fresh: `rm ~/.openclaw-health-assistant/setup_progress.json`

See [docs/SETUP_WIZARD_AND_APPLE_HEALTH.md](../docs/SETUP_WIZARD_AND_APPLE_HEALTH.md) (Apple Health Link).
