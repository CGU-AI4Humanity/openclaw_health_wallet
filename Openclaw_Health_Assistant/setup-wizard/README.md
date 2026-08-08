# Setup Wizard (prototype)

Mac **Tkinter** assistant for class demos:

```bash
../scripts/run_setup_wizard.sh
```

- Checks prerequisites (Node 24, Ollama, OpenClaw, Python)
- Initializes SQLite + MCP venv
- Form: FHIR API key + first / last name + DOB → `config/.env`
- Wires MCP servers
- **QR + local pairing API** for Apple Health
- Ollama MedGemma configure
- Resume via `~/.openclaw-health-assistant/setup_progress.json`

See [docs/SETUP_WIZARD_AND_APPLE_HEALTH.md](../docs/SETUP_WIZARD_AND_APPLE_HEALTH.md).
