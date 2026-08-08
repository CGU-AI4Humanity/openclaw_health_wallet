# Apple Health bridge

**Lead:** Mahesh Balan — Apple Health integration and sync into local SQLite `health_*` tables.

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
| `import_apple_health_json` | Optional import from `inbox/*.json` (engineering / recovery) |

Pairing API ingestion does not require MCP; the pairing server writes SQLite directly.

## macOS HealthKit (future)

Where entitlements allow, a native Mac helper may read the **Health** app database directly when iPhone data is already synced—same SQLite schema, no phone POST.

**Lead:** Mahesh Balan.
