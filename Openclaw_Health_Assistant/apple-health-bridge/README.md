# Apple Health bridge (planned)

Ingest Apple Health data into the same `health_*` tables MyWellWallet uses on iOS (`health_glucose`, `health_heart_rate`, `health_steps`, `health_blood_pressure`, `health_lab_results`, `health_sync_settings`).

## macOS considerations

- The **Health** app on Mac shows data synced from iPhone; programmatic access differs from iOS HealthKit.
- Options to evaluate:
  1. **Native Swift CLI** with HealthKit (macOS 13+ where entitlements allow).
  2. **Shortcuts / automation** exporting CSV or JSON on a schedule into `data/inbox/`.
  3. **Companion sync** from the MyWellWallet iOS app via encrypted export (longer term).

## Target behavior

1. User grants Health permissions once.
2. Bridge runs on interval (see `health_sync_settings.sync_interval_hours`).
3. Normalized rows land in SQLite with ISO8601 timestamps and `user_id`.
4. OpenClaw queries via `sqlite-mcp` alongside FHIR MCP answers.

## Reference

MyWellWallet iOS: `lib/services/apple_health_service.dart`, `docs/APPLE_HEALTH_SETUP.md` (sibling repo).

## Files to add

```text
apple-health-bridge/
├── README.md
├── (swift or python ingest)
└── config/sync_types.json
```
