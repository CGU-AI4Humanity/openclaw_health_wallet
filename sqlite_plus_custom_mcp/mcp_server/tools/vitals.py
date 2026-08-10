from __future__ import annotations

import database
from models import BloodPressureReading, VitalReading


def get_latest_blood_pressure() -> BloodPressureReading:
    user_id = database.resolve_active_user_id()
    row = database.query_one(
        "SELECT systolic_real, diastolic_real, unit, recorded_at "
        "FROM health_blood_pressure WHERE user_id = ? "
        "ORDER BY recorded_at DESC LIMIT 1",
        (user_id,),
    )
    if row is None:
        return BloodPressureReading(found=False)
    return BloodPressureReading(
        found=True,
        systolic=row["systolic_real"],
        diastolic=row["diastolic_real"],
        unit=row["unit"],
        recorded_at=row["recorded_at"],
    )


def get_latest_glucose() -> VitalReading:
    return _latest_single_value("health_glucose")


def get_latest_heart_rate() -> VitalReading:
    return _latest_single_value("health_heart_rate")


def _latest_single_value(table: str) -> VitalReading:
    user_id = database.resolve_active_user_id()
    row = database.query_one(
        f"SELECT value_real, unit, recorded_at FROM {table} "
        "WHERE user_id = ? ORDER BY recorded_at DESC LIMIT 1",
        (user_id,),
    )
    if row is None:
        return VitalReading(found=False)
    return VitalReading(
        found=True,
        value=row["value_real"],
        unit=row["unit"],
        recorded_at=row["recorded_at"],
    )


def register(mcp) -> None:
    mcp.tool()(get_latest_blood_pressure)
    mcp.tool()(get_latest_glucose)
    mcp.tool()(get_latest_heart_rate)
