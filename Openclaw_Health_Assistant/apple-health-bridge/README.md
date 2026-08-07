# Apple Health bridge

**Lead:** Mahesh Balan — Apple Health integration and sync into MyWellWallet-compatible SQLite `health_*` tables.

SQLite schema and MCP data access: **Brandon Medina**. OpenClaw MCP wiring: **Leonard Bryant**.

Ingest Apple Health data into the same tables as MyWellWallet iOS (`health_glucose`, `health_heart_rate`, `health_steps`, `health_blood_pressure`, `health_lab_results`, `health_sync_settings`).

## macOS considerations

- The **Health** app on Mac shows data synced from iPhone; programmatic access differs from iOS HealthKit.
- Options to evaluate:
  1. **Native Swift CLI** with HealthKit (macOS 13+ where entitlements allow).
  2. **Shortcuts / automation** exporting CSV or JSON on a schedule into `data/inbox/`.
  3. **Companion sync** from the MyWellWallet iOS app via encrypted export (longer term).

## Apple Health on macOS

**Primary (target):** QR pairing via `./scripts/apple_health_pairing.sh` → MyWellWallet on iPhone → **API** → SQLite. See [README Step 5](../README.md#step-5-connect-apple-health-qr--api).

**Interim (testing):** iPhone SQLite export or JSON inbox — MCP tools below.

| Tool | Purpose |
| --- | --- |
| `get_apple_health_sync_status` | Read `health_sync_settings` |
| `sync_apple_health_from_phone_database` | Copy `health_*` tables from iPhone MyWellWallet SQLite export |
| `import_apple_health_json` | Import `apple-health-bridge/inbox/*.json` |

Example prompt in OpenClaw:

```text
Call get_apple_health_sync_status for my current user, then summarize health_steps
and health_heart_rate counts from health_metrics_summary. Medical disclaimer.
```

## Reference

MyWellWallet iOS: [github.com/maheshbalan/myWellWallet](https://github.com/maheshbalan/myWellWallet) — `lib/services/apple_health_service.dart`, `docs/APPLE_HEALTH_SETUP.md`.

## Files to add

```text
apple-health-bridge/
├── README.md
├── (swift or python ingest)
└── config/sync_types.json
```
