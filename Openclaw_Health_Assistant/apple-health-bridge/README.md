# Apple Health bridge

**Lead:** Mahesh Balan — Apple Health integration and sync into MyWellWallet-compatible SQLite `health_*` tables.

SQLite schema and MCP access: **Brandon Medina**. OpenClaw MCP registration: **Leonard Bryant**.

## Standard workflow

1. Mac **Setup Wizard** or **`pairing_server.py`** listens on the local network.
2. iPhone **[Health Link](../../Health_Link_iOS/)** scans the QR code and authorizes HealthKit.
3. The phone POSTs normalized JSON to **`/v1/health/sync`**; rows land in `health_glucose`, `health_heart_rate`, `health_steps`, `health_blood_pressure`, `health_lab_results`, and related tables.

See [README Step 5](../README.md#step-5-connect-apple-health-qr--local-api) and [SETUP_WIZARD_AND_APPLE_HEALTH.md](../docs/SETUP_WIZARD_AND_APPLE_HEALTH.md).

## Components

| File | Role |
| --- | --- |
| `pairing_server.py` | Local HTTP API and token validation |
| `health_sync.py` | JSON → SQLite insert logic |
| `inbox/` | Optional file-based JSON import |

## MCP tools (via SQLite MCP server)

| Tool | Purpose |
| --- | --- |
| `get_apple_health_sync_status` | Read `health_sync_settings` |
| `import_apple_health_json` | Import structured JSON from `inbox/` |
| `sync_apple_health_from_phone_database` | Legacy bulk copy from an exported SQLite file (engineering use) |

## macOS HealthKit (future)

Where entitlements allow, a native Mac helper may read the **Health** app database directly when iPhone data is already synced—same SQLite schema, no phone POST.

## Reference

Related mobile research: [MyWellWallet](https://github.com/maheshbalan/myWellWallet).

**Lead:** Mahesh Balan.
