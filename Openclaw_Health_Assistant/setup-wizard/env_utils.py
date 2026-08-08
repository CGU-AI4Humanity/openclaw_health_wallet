"""Read/write config/.env key=value pairs."""

from __future__ import annotations

from pathlib import Path


def load_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip().strip('"')
    return out


def write_env(path: Path, values: dict[str, str]) -> None:
    existing = load_env(path) if path.is_file() else {}
    existing.update({k: v for k, v in values.items() if v is not None})
    lines = [
        "# Generated/updated by OpenClaw Setup Wizard — do not commit",
        "",
    ]
    order = [
        "OPENCLAW_HEALTH_DB_PATH",
        "FHIR_MCP_BASE_URL",
        "FHIR_MCP_API_KEY",
        "FHIR_PATIENT_FIRST_NAME",
        "FHIR_PATIENT_LAST_NAME",
        "FHIR_PATIENT_DOB",
        "APPLE_HEALTH_API_BASE_URL",
        "APPLE_HEALTH_DEVICE_TOKEN",
        "OLLAMA_API_KEY",
        "OLLAMA_HOST",
        "OLLAMA_MEDGEMMA_MODEL",
    ]
    seen = set()
    for key in order:
        if key in existing:
            lines.append(f'{key}="{existing[key]}"')
            seen.add(key)
    for key, val in sorted(existing.items()):
        if key not in seen:
            lines.append(f'{key}="{val}"')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o600)
