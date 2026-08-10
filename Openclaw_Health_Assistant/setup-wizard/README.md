# Setup Wizard

macOS **Tkinter** assistant for OpenClaw Health Assistant onboarding:

```bash
../scripts/run_setup_wizard.sh
```

- Verifies prerequisites (Node 24, Ollama, OpenClaw, Python)
- Initializes SQLite and the SQLite MCP virtual environment
- Captures FHIR API key and patient identity → `config/.env`
- Registers MCP servers
- Displays QR and runs the local Apple Health pairing API
- Configures **Qwen3** for OpenClaw MCP tool calling
- Persists resume state in `~/.openclaw-health-assistant/setup_progress.json`
- Each tab includes an **action log** showing commands run and their output

See [docs/SETUP_WIZARD_AND_APPLE_HEALTH.md](../docs/SETUP_WIZARD_AND_APPLE_HEALTH.md).
