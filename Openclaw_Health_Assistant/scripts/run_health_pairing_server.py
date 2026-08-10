#!/usr/bin/env python3
"""Run Apple Health pairing API on port 8765 (keep terminal open during iPhone sync)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "setup-wizard"))
sys.path.insert(0, str(ROOT / "apple-health-bridge"))

from db_utils import ensure_local_user, expand_path, resolve_db_path  # noqa: E402
from env_utils import load_env  # noqa: E402
from pairing_server import PairingServer  # noqa: E402

ENV_PATH = ROOT / "config" / ".env"
PORT = int(os.environ.get("APPLE_HEALTH_PAIRING_PORT", "8765"))


def lan_ip() -> str:
    for iface in ("en0", "en1", "en2"):
        try:
            out = subprocess.check_output(["ipconfig", "getifaddr", iface], text=True).strip()
            if out:
                return out
        except subprocess.CalledProcessError:
            continue
    return "127.0.0.1"


def main() -> None:
    env = load_env(ENV_PATH)
    db = resolve_db_path(env)
    user_id, msg = ensure_local_user(db, env=env)
    host = os.environ.get("APPLE_HEALTH_PAIRING_HOST") or lan_ip()

    server = PairingServer(db, user_id, host="0.0.0.0", port=PORT)
    server.start()
    url = f"openclaw-health://pair?host={host}&port={PORT}&token={server.token}"

    print(f"Database: {db}")
    print(msg)
    print(f"Listening on 0.0.0.0:{PORT} (iPhone must reach Mac at {host})")
    print(f"\nPair URL:\n  {url}\n")
    print("Scan in Health Link or paste URL. Ctrl+C to stop.")
    try:
        import time

        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        server.stop()
        print("Stopped.")


if __name__ == "__main__":
    main()
