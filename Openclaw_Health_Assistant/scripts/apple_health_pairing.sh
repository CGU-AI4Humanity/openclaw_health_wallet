#!/usr/bin/env bash
# Apple Health QR pairing helper (Mahesh Balan)
# Displays a pairing URL for MyWellWallet on iPhone until full API is deployed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/config/.env"

TOKEN="$(uuidgen 2>/dev/null | tr '[:upper:]' '[:lower:]' || openssl rand -hex 16)"
HOST="${APPLE_HEALTH_PAIRING_HOST:-$(ipconfig getifaddr en0 2>/dev/null || echo 127.0.0.1)}"
PORT="${APPLE_HEALTH_PAIRING_PORT:-8765}"

PAIR_URL="openclaw-health://pair?host=${HOST}&port=${PORT}&token=${TOKEN}"

echo ""
echo "=== Apple Health pairing (OpenClaw Health Link) ==="
echo ""
echo "1. Install the iPhone Health Link companion (see docs/SETUP_WIZARD_AND_APPLE_HEALTH.md)"
echo "   or run: ./scripts/run_setup_wizard.sh for QR on screen"
echo ""
echo "Pairing URL (for QR generator or manual entry):"
echo "  ${PAIR_URL}"
echo ""
echo "Token (save to config/.env as APPLE_HEALTH_DEVICE_TOKEN after phone confirms):"
echo "  ${TOKEN}"
echo ""
echo "Optional API base (when bridge is live):"
echo "  APPLE_HEALTH_API_BASE_URL=http://${HOST}:${PORT}"
echo ""

if command -v qrencode >/dev/null 2>&1; then
  echo "QR (terminal):"
  qrencode -t ANSIUTF8 "${PAIR_URL}"
elif python3 -c "import qrcode" 2>/dev/null; then
  python3 - <<PY
import qrcode
qr = qrcode.QRCode(border=1)
qr.add_data("${PAIR_URL}")
qr.make()
qr.print_ascii(invert=True)
PY
else
  echo "Tip: brew install qrencode  (or pip install qrcode) to show a scannable QR in the terminal."
  echo "Until then, type the token above into MyWellWallet Link Mac."
fi

echo ""
echo "After the phone authorizes Apple Health, add to ${ENV_FILE}:"
echo "  APPLE_HEALTH_DEVICE_TOKEN=${TOKEN}"
echo "  APPLE_HEALTH_API_BASE_URL=http://${HOST}:${PORT}"
echo ""
echo "Interim: use ./scripts/run_setup_wizard.sh to start the local pairing API."
