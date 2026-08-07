# First-run OpenClaw prompts

After `./scripts/install_local_stack.sh` and `openclaw tui`, run these **once** (one at a time) so local SQLite is populated. Replace placeholders with values from your gitignored `config/.env`.

> Include a **medical disclaimer** in every health-facing reply. This is research software, not clinical care.

---

## Step 1 — Apple Health → SQLite

Paste into OpenClaw (adjust path if needed):

```text
Using mywellwallet-sqlite only:

1. Call get_current_user to obtain user_id.
2. Call sync_apple_health_from_phone_database with source_sqlite_path set to
   the path in my APPLE_HEALTH_PHONE_DB_PATH (or my latest iPhone MyWellWallet export).
3. Call get_apple_health_sync_status for that user_id.
4. Summarize what was synced (counts for health_steps, health_heart_rate,
   health_glucose, health_blood_pressure, health_lab_results).

Do not call fhir-remote yet. End with a medical disclaimer.
```

**Alternative:** drop a JSON file in `apple-health-bridge/inbox/` and ask the agent to call `import_apple_health_json` with that path.

---

## Step 2 — FHIR MCP → refresh EHR cache

Use the **name and DOB from config/.env** (FHIR_PATIENT_FIRST_NAME, FHIR_PATIENT_LAST_NAME, FHIR_PATIENT_DOB):

```text
Using fhir-remote MCP tools:

1. Find my patient record using first name "<FHIR_PATIENT_FIRST_NAME>",
   last name "<FHIR_PATIENT_LAST_NAME>", birth date "<FHIR_PATIENT_DOB>".
2. Fetch recent relevant FHIR resources (Patient, Condition, Observation, MedicationRequest,
   Immunization, Encounter — as available).
3. Using mywellwallet-sqlite, upsert the patient bundle and individual fhir_resources
   so my local cache is current.
4. Confirm with sqlite_health and list_fhir_patients.

End with a medical disclaimer.
```

You should **not** need to re-enter API keys or Apple Health passwords in chat—those live in local config and OS permissions.

---

## Step 3 — Ongoing questions (SQLite-grounded answers)

```text
For my health question below:
1. Use mywellwallet-sqlite to load context (list_fhir_patients, search_fhir_resources,
   execute_read_query on health_* tables as needed).
2. Answer using only that retrieved context plus general medical education.
3. If local data is stale, say so and offer to refresh from fhir-remote.

Question: <your question here>

Medical disclaimer required.
```

---

## Optional — larger local models (64 GB RAM e.g. iMac Pro)

```bash
ollama pull medgemma:27b
# or: ollama pull qwen3:4b
```

Update `OLLAMA_MEDGEMMA_MODEL` in `config/.env` and re-run `./scripts/configure_medgemma.sh`, editing `config/openclaw.medgemma.patch.json5` if you change model id or context window.
