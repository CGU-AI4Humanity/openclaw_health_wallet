# Apple Health JSON inbox

Optional **file-based import** when operators supply a pre-built JSON export. The SQLite MCP tool **`import_apple_health_json`** reads files placed here.

The **standard workflow** uses [Health Link](../../../Health_Link_iOS/) and the Mac pairing API—not this inbox.

Example payload:

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

**Lead:** Mahesh Balan.
