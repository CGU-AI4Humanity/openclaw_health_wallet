# First-run OpenClaw prompts

Use **after** [README.md](../README.md) Steps 1–9. Start with `nvm use 24 && openclaw tui`.

Replace `FHIR_PATIENT_*` placeholders with values from your gitignored **`config/.env`** (never paste keys into Git).

> Medical disclaimer required on every health answer.

---

## Prompt A — Apple Health (Step 10)

After **Health Link** QR pairing and a successful POST to the Mac pairing API:

```text
Use only openclaw-health-sqlite tools.

1. get_current_user → user_id
2. get_apple_health_sync_status for that user_id
3. If health_* tables are empty, stop and tell me to complete Setup Wizard Apple Health pairing
   (Health Link iOS → scan QR → authorize sync). Do not import from other apps' databases.
4. health_metrics_summary for user_id
5. Summarize steps, heart rate, glucose, BP, labs availability.

Medical disclaimer required.
```

---

## Prompt B — FHIR MCP → SQLite (Step 10)

API key is already in OpenClaw MCP config from `wire_mcp_servers.sh` — **do not** type the key in chat.

```text
Use fhir-remote, then openclaw-health-sqlite.

Patient identity (from my local config, do not ask again):
  First: <FHIR_PATIENT_FIRST_NAME>
  Last: <FHIR_PATIENT_LAST_NAME>
  DOB: <FHIR_PATIENT_DOB>

1. Find and fetch my FHIR resources (Patient, Condition, Observation,
   MedicationRequest, Immunization, Encounter).
2. upsert_fhir_patient / upsert_fhir_resource into local SQLite.
3. sqlite_health and list_fhir_patients to confirm.

Medical disclaimer required.
```

---

## Prompt C — Grounded Q&A (Step 11)

```text
You MUST call openclaw-health-sqlite before answering.

1. Retrieve relevant fhir_resources and health_* rows for my question.
2. Answer using only that data plus general education.
3. Offer fhir-remote refresh only if data looks missing or I ask for "latest from server".

Question: <your question>

Medical disclaimer required.
```

---

## Larger models (64 GB RAM)

```bash
ollama pull medgemma:27b
# Update OLLAMA_MEDGEMMA_MODEL in config/.env
./scripts/configure_medgemma.sh
```
