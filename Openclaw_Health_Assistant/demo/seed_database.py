from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CSV_DIR = BASE_DIR / "csv"
DEFAULT_DATABASE = BASE_DIR / "final_project.db"


SCHEMA = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS health_sync_settings;
DROP TABLE IF EXISTS health_steps;
DROP TABLE IF EXISTS health_lab_results;
DROP TABLE IF EXISTS health_heart_rate;
DROP TABLE IF EXISTS health_glucose;
DROP TABLE IF EXISTS health_blood_pressure;
DROP TABLE IF EXISTS fhir_resources;
DROP TABLE IF EXISTS fhir_patients;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    date_of_birth TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE fhir_patients (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    patient_name TEXT NOT NULL,
    fhir_bundle TEXT NOT NULL,
    last_synced TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES users(id)
);

CREATE TABLE fhir_resources (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    resource_data TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES users(id)
);

CREATE TABLE health_blood_pressure (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    systolic_real INTEGER NOT NULL,
    diastolic_real INTEGER NOT NULL,
    unit TEXT NOT NULL,
    source_bundle_id TEXT,
    recorded_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE health_glucose (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    value_real REAL NOT NULL,
    unit TEXT NOT NULL,
    source_bundle_id TEXT,
    recorded_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE health_heart_rate (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    value_real REAL NOT NULL,
    unit TEXT NOT NULL,
    source_bundle_id TEXT,
    recorded_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE health_lab_results (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    loinc_code TEXT,
    value_numeric REAL,
    value_string TEXT,
    unit TEXT,
    reference_range_low REAL,
    reference_range_high REAL,
    reference_range_text TEXT,
    source_name TEXT,
    source_bundle_id TEXT,
    specimen_type TEXT,
    recorded_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE health_steps (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    count INTEGER NOT NULL,
    distance_meters REAL NOT NULL,
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    source_bundle_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE health_sync_settings (
    user_id TEXT PRIMARY KEY,
    sync_interval_hours INTEGER NOT NULL DEFAULT 24,
    last_synced_at TEXT,
    connected_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_fhir_patients_patient_id ON fhir_patients(patient_id);
CREATE INDEX idx_fhir_resources_patient_id ON fhir_resources(patient_id);
CREATE INDEX idx_fhir_resources_type ON fhir_resources(resource_type);
CREATE INDEX idx_blood_pressure_user_recorded ON health_blood_pressure(user_id, recorded_at);
CREATE INDEX idx_glucose_user_recorded ON health_glucose(user_id, recorded_at);
CREATE INDEX idx_heart_rate_user_recorded ON health_heart_rate(user_id, recorded_at);
CREATE INDEX idx_lab_results_user_recorded ON health_lab_results(user_id, recorded_at);
CREATE INDEX idx_steps_user_start ON health_steps(user_id, start_at);
"""


TABLES = {
    "users": {
        "file": "users.csv",
        "columns": ["id", "name", "email", "date_of_birth", "created_at", "updated_at"],
        "numeric": {},
    },
    "fhir_patients": {
        "file": "fhir_patients.csv",
        "columns": [
            "id",
            "patient_id",
            "patient_name",
            "fhir_bundle",
            "last_synced",
            "created_at",
            "updated_at",
        ],
        "numeric": {},
    },
    "fhir_resources": {
        "file": "fhir_resources.csv",
        "columns": [
            "id",
            "patient_id",
            "resource_type",
            "resource_id",
            "resource_data",
            "created_at",
            "updated_at",
        ],
        "numeric": {},
    },
    "health_blood_pressure": {
        "file": "health_blood_pressure.csv",
        "columns": [
            "id",
            "user_id",
            "systolic_real",
            "diastolic_real",
            "unit",
            "source_bundle_id",
            "recorded_at",
            "created_at",
        ],
        "numeric": {"systolic_real": int, "diastolic_real": int},
    },
    "health_glucose": {
        "file": "health_glucose.csv",
        "columns": [
            "id",
            "user_id",
            "value_real",
            "unit",
            "source_bundle_id",
            "recorded_at",
            "created_at",
        ],
        "numeric": {"value_real": float},
    },
    "health_heart_rate": {
        "file": "health_heart_rate.csv",
        "columns": [
            "id",
            "user_id",
            "value_real",
            "unit",
            "source_bundle_id",
            "recorded_at",
            "created_at",
        ],
        "numeric": {"value_real": float},
    },
    "health_lab_results": {
        "file": "health_lab_results.csv",
        "columns": [
            "id",
            "user_id",
            "name",
            "loinc_code",
            "value_numeric",
            "value_string",
            "unit",
            "reference_range_low",
            "reference_range_high",
            "reference_range_text",
            "source_name",
            "source_bundle_id",
            "specimen_type",
            "recorded_at",
            "created_at",
        ],
        "numeric": {
            "value_numeric": float,
            "reference_range_low": float,
            "reference_range_high": float,
        },
    },
    "health_steps": {
        "file": "health_steps.csv",
        "columns": [
            "id",
            "user_id",
            "count",
            "distance_meters",
            "start_at",
            "end_at",
            "source_bundle_id",
            "created_at",
        ],
        "numeric": {"count": int, "distance_meters": float},
    },
}


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def convert_value(value: str, converter: type | None) -> object:
    if value == "":
        return None
    if converter is None:
        return value
    return converter(value)


def load_table(connection: sqlite3.Connection, csv_dir: Path, table_name: str) -> int:
    config = TABLES[table_name]
    csv_path = csv_dir / config["file"]
    columns = config["columns"]
    numeric = config["numeric"]

    if not csv_path.exists():
        raise FileNotFoundError(f"Missing CSV file: {csv_path}")

    placeholders = ", ".join(["?"] * len(columns))
    column_sql = ", ".join(quote_identifier(column) for column in columns)
    insert_sql = f"INSERT INTO {quote_identifier(table_name)} ({column_sql}) VALUES ({placeholders})"

    rows = []
    with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames != columns:
            raise ValueError(
                f"{csv_path.name} headers do not match schema.\n"
                f"Expected: {columns}\n"
                f"Found:    {reader.fieldnames}"
            )
        for row in reader:
            rows.append(
                tuple(convert_value(row[column], numeric.get(column)) for column in columns)
            )

    connection.executemany(insert_sql, rows)
    return len(rows)


def seed_database(database_path: Path, csv_dir: Path) -> dict[str, int]:
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA)

        counts = {}
        for table_name in TABLES:
            counts[table_name] = load_table(connection, csv_dir, table_name)

        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(f"Foreign key violations found: {violations}")

        connection.commit()
        return counts
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create and seed final_project.db from Final_Project/data CSV files."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help=f"SQLite database path. Default: {DEFAULT_DATABASE}",
    )
    parser.add_argument(
        "--csv-dir",
        type=Path,
        default=DEFAULT_CSV_DIR,
        help=f"Directory containing source CSV files. Default: {DEFAULT_CSV_DIR}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    database_path = args.database.expanduser().resolve()
    csv_dir = args.csv_dir.expanduser().resolve()

    database_path.parent.mkdir(parents=True, exist_ok=True)
    counts = seed_database(database_path, csv_dir)

    print(f"Seeded {database_path}")
    for table_name, row_count in counts.items():
        print(f"{table_name}: {row_count}")


if __name__ == "__main__":
    main()
