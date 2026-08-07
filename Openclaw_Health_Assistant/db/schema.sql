-- MyWellWallet-compatible schema (SQLite version 4)
-- Source: myWellWallet lib/services/database_service.dart

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  date_of_birth TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fhir_patients (
  id TEXT PRIMARY KEY,
  patient_id TEXT NOT NULL,
  patient_name TEXT NOT NULL,
  fhir_bundle TEXT NOT NULL,
  last_synced TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fhir_resources (
  id TEXT PRIMARY KEY,
  patient_id TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id TEXT NOT NULL,
  resource_data TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(patient_id, resource_type, resource_id)
);

CREATE TABLE IF NOT EXISTS fetch_summaries (
  id TEXT PRIMARY KEY,
  patient_id TEXT NOT NULL,
  total_resources INTEGER NOT NULL,
  resource_counts TEXT NOT NULL,
  completed_at TEXT NOT NULL,
  errors TEXT,
  stored_in_database INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fhir_patients_patient_id ON fhir_patients(patient_id);
CREATE INDEX IF NOT EXISTS idx_fhir_resources_patient_id ON fhir_resources(patient_id);
CREATE INDEX IF NOT EXISTS idx_fhir_resources_type ON fhir_resources(resource_type);
CREATE INDEX IF NOT EXISTS idx_fetch_summaries_patient_id ON fetch_summaries(patient_id);

-- Apple Health mirror tables (same as MyWellWallet iOS)
CREATE TABLE IF NOT EXISTS health_glucose (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  value_real REAL NOT NULL,
  unit TEXT NOT NULL DEFAULT 'mg/dL',
  source_bundle_id TEXT,
  recorded_at TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS health_heart_rate (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  value_real REAL NOT NULL,
  unit TEXT NOT NULL DEFAULT 'bpm',
  source_bundle_id TEXT,
  recorded_at TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS health_steps (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  count INTEGER NOT NULL,
  distance_meters REAL,
  start_at TEXT NOT NULL,
  end_at TEXT NOT NULL,
  source_bundle_id TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS health_blood_pressure (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  systolic_real REAL NOT NULL,
  diastolic_real REAL NOT NULL,
  unit TEXT NOT NULL DEFAULT 'mmHg',
  source_bundle_id TEXT,
  recorded_at TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS health_sync_settings (
  user_id TEXT PRIMARY KEY,
  sync_interval_hours INTEGER NOT NULL DEFAULT 24,
  last_synced_at TEXT,
  connected_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS health_lab_results (
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
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_health_glucose_user_recorded ON health_glucose(user_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_heart_rate_user_recorded ON health_heart_rate(user_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_steps_user_created ON health_steps(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_blood_pressure_user_recorded ON health_blood_pressure(user_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_health_lab_results_user_recorded ON health_lab_results(user_id, recorded_at DESC);
