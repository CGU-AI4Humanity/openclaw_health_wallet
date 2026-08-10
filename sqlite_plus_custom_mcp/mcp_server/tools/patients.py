from __future__ import annotations

from datetime import date

import database
from models import Patient


def _age_from_dob(dob: str) -> int:
    born = date.fromisoformat(dob[:10])
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def get_patient() -> Patient:
    user_id = database.resolve_active_user_id()
    row = database.query_one(
        "SELECT id, name, email, date_of_birth FROM users WHERE id = ?",
        (user_id,),
    )
    if row is None:
        raise ValueError(f"No patient found for id {user_id!r}.")
    return Patient(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        date_of_birth=row["date_of_birth"],
        age=_age_from_dob(row["date_of_birth"]),
    )


def register(mcp) -> None:
    """Attach this module's tools to the MCP server."""
    mcp.tool()(get_patient)
