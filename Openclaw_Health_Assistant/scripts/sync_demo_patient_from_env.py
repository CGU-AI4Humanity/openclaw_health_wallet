#!/usr/bin/env python3
"""Align demo patient row (default PT0001) with FHIR_PATIENT_* in config/.env."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / "config" / ".env"


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        val = val.strip().strip('"').strip("'")
        out[key.strip()] = val
    return out


def dob_to_db(dob: str) -> str:
    """Store like demo CSV: 1972-08-02T00:00:00.000"""
    dob = dob.strip()[:10]
    return f"{dob}T00:00:00.000"


def main() -> int:
    env = load_env(ENV_FILE)
    first = env.get("FHIR_PATIENT_FIRST_NAME", "").strip()
    last = env.get("FHIR_PATIENT_LAST_NAME", "").strip()
    dob = env.get("FHIR_PATIENT_DOB", "").strip()
    if not (first and last and dob):
        print("Set FHIR_PATIENT_FIRST_NAME, FHIR_PATIENT_LAST_NAME, FHIR_PATIENT_DOB in config/.env", file=sys.stderr)
        return 1

    user_id = env.get("HEALTH_ACTIVE_USER_ID", "PT0001").strip() or "PT0001"
    db_raw = env.get("HEALTH_DB_PATH") or env.get("OPENCLAW_HEALTH_DB_PATH") or ""
    db = Path(os.path.expanduser(os.path.expandvars(db_raw))).resolve()
    if not db.is_file():
        print(f"Database not found: {db}", file=sys.stderr)
        return 1

    display_name = f"{first} {last}"
    email = f"{first.lower()}.{last.lower()}@email.invalid".replace(" ", "")
    dob_db = dob_to_db(dob)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            """
            UPDATE users SET name = ?, email = ?, date_of_birth = ?, updated_at = ?
            WHERE id = ?
            """,
            (display_name, email, dob_db, now, user_id),
        )
        if cur.rowcount == 0:
            print(f"No users row for id={user_id!r}", file=sys.stderr)
            return 1

        conn.execute(
            """
            UPDATE fhir_patients SET patient_name = ?, updated_at = ?
            WHERE patient_id = ?
            """,
            (display_name, now, user_id),
        )

        row = conn.execute(
            """
            SELECT id, resource_data FROM fhir_resources
            WHERE patient_id = ? AND resource_type = 'Patient'
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        if row:
            data = json.loads(row["resource_data"])
            data["birthDate"] = dob[:10]
            names = data.get("name") or [{}]
            if names:
                names[0]["family"] = last
                names[0]["given"] = [first]
            else:
                data["name"] = [{"use": "official", "family": last, "given": [first]}]
            telecom = data.get("telecom") or []
            if telecom:
                telecom[0]["value"] = email
            conn.execute(
                """
                UPDATE fhir_resources SET resource_data = ?, updated_at = ?
                WHERE id = ?
                """,
                (json.dumps(data), now, row["id"]),
            )

        conn.commit()
    finally:
        conn.close()

    print(f"Updated {user_id}: {display_name}, DOB {dob[:10]} in {db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
