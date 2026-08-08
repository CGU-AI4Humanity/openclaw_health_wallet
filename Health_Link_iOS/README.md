# OpenClaw Health Link (iOS)

Thin **iPhone companion** for the OpenClaw Health Assistant monorepo. Scans a **QR code** from the Mac Setup Wizard, reads **Apple HealthKit**, and POSTs JSON to the Mac’s local pairing API (`/v1/health/sync`).

**Mahesh Balan** — Apple Health integration track.

---

## Requirements

- iPhone with **iOS 16+**
- Mac and iPhone on the **same Wi‑Fi**
- Mac running `./scripts/run_setup_wizard.sh` → **Apple Health** tab → **Start pairing + show QR**
- Apple Developer account (free or team) for **HealthKit** capability on device

---

## Open in Xcode

### Option A — XcodeGen (recommended)

```bash
brew install xcodegen
cd Health_Link_iOS
xcodegen generate
open OpenClawHealthLink.xcodeproj
```

1. Select target **OpenClawHealthLink** → **Signing & Capabilities**
2. Set your **Team**
3. Add **HealthKit** capability if not present (entitlements file is included)
4. Run on a **physical iPhone** (HealthKit + camera)

### Option B — Manual Xcode project

1. **File → New → App** → SwiftUI, iOS 16, name `OpenClawHealthLink`
2. Replace generated sources with files in `OpenClawHealthLink/`
3. Set **Info.plist** and **OpenClawHealthLink.entitlements** from this folder
4. Enable **HealthKit** capability

---

## End-to-end workflow

1. **Mac:** `cd Openclaw_Health_Assistant && ./scripts/run_setup_wizard.sh` → Apple Health → **Start pairing + show QR**
2. **iPhone:** Build and run **Health Link** → **Scan QR code**
3. Tap **Authorize & sync to Mac** and grant Health access
4. Confirm pairing on the Mac; SQLite `health_*` tables are populated
5. Complete remaining wizard steps (Ollama, OpenClaw registration), then launch OpenClaw

---

## URL format

```text
openclaw-health://pair?host=192.168.1.10&port=8765&token=<uuid>
```

The app also accepts this string pasted from the terminal pairing script.

---

## Payload

JSON matches `apple-health-bridge/health_sync.py` → `import_health_json_export` (`glucose`, `heart_rate`, `steps`, `blood_pressure`, `lab_results`).

---

## Privacy

- Sync is **HTTP on LAN** to the Mac you paired with (see `NSAllowsLocalNetworking`).
- No account login in this app; pairing token is single-purpose.
- Do not commit PHI or pairing tokens.

---

## Related docs

- [Openclaw_Health_Assistant/README.md](../Openclaw_Health_Assistant/README.md)
- [SETUP_WIZARD_AND_APPLE_HEALTH.md](../Openclaw_Health_Assistant/docs/SETUP_WIZARD_AND_APPLE_HEALTH.md)
