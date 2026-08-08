#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"
python3 -m venv setup-wizard/.venv 2>/dev/null || true
setup-wizard/.venv/bin/pip install -q -r setup-wizard/requirements.txt 2>/dev/null || pip3 install -q -r setup-wizard/requirements.txt
exec setup-wizard/.venv/bin/python setup-wizard/wizard.py
