# Apple Health JSON inbox

Drop **`health_export.json`** here for the OpenClaw assistant to import via MCP tool `import_apple_health_json`.

Example shape:

```json
{
  "sync_interval_hours": 24,
  "glucose": [
    {"id": "g1", "value": 105, "unit": "mg/dL", "recorded_at": "2026-08-01T08:00:00Z"}
  ],
  "heart_rate": [
    {"id": "hr1", "value": 72, "unit": "bpm", "recorded_at": "2026-08-01T08:00:00Z"}
  ],
  "steps": [
    {"id": "s1", "count": 4200, "start_at": "2026-08-01T00:00:00Z", "end_at": "2026-08-01T23:59:59Z"}
  ],
  "blood_pressure": [
    {"id": "bp1", "systolic": 120, "diastolic": 80, "recorded_at": "2026-08-01T08:00:00Z"}
  ],
  "lab_results": []
}
```

On macOS, the primary path is **`sync_apple_health_from_phone_database`**, which copies `health_*` tables from a MyWellWallet iPhone SQLite export (same as Brandon’s fixture copy flow).

**Lead:** Mahesh Balan — Apple Health integration.
