from __future__ import annotations

from pydantic import BaseModel, Field


class Patient(BaseModel):
    id: str = Field(description="Internal patient/user id.")
    name: str
    email: str
    date_of_birth: str = Field(description="ISO-8601 date of birth as stored.")
    age: int = Field(description="Age in whole years, computed at query time.")


class BloodPressureReading(BaseModel):
    found: bool = Field(description="False when the patient has no readings.")
    systolic: int | None = Field(default=None, description="Systolic, mmHg.")
    diastolic: int | None = Field(default=None, description="Diastolic, mmHg.")
    unit: str | None = None
    recorded_at: str | None = Field(default=None, description="ISO-8601 timestamp.")


class VitalReading(BaseModel):
    found: bool = Field(description="False when the patient has no readings.")
    value: float | None = None
    unit: str | None = None
    recorded_at: str | None = Field(default=None, description="ISO-8601 timestamp.")


class LabResult(BaseModel):
    found: bool = Field(description="False when no matching lab result exists.")
    name: str | None = None
    value: float | None = None
    unit: str | None = None
    recorded_at: str | None = None
    reference_low: float | None = None
    reference_high: float | None = None
    range_status: str | None = Field(
        default=None, description="below | normal | above | unknown (from the data's own range)."
    )
    is_anomaly: bool | None = Field(
        default=None, description="True when the value is outside its reference range."
    )
    trend: str | None = Field(
        default=None, description="rising | falling | stable | insufficient_data."
    )
    change_from_previous: float | None = None
    readings_considered: int | None = None


class LabResultList(BaseModel):
    count: int
    results: list[LabResult]


class LabTestList(BaseModel):
    count: int
    tests: list[str]