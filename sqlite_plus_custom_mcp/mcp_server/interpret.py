from __future__ import annotations

RANGE_UNKNOWN = "unknown"

CLINICAL_RANGES: dict[str, tuple[float | None, float | None, str]] = {
    "systolic": (90, 120, "mmHg"),
    "diastolic": (60, 80, "mmHg"),
    "glucose_fasting": (70, 99, "mg/dL"),
    "heart_rate": (60, 100, "bpm"),
}

_STABLE_BAND = 0.05


def classify_range(
    value: float | None,
    low: float | None,
    high: float | None,
) -> str:
    if value is None or (low is None and high is None):
        return RANGE_UNKNOWN
    if low is not None and value < low:
        return "below"
    if high is not None and value > high:
        return "above"
    return "normal"


def summarize_trend(values: list[float]) -> tuple[str, float | None]:
    n = len(values)
    if n < 2:
        return "insufficient_data", None
    latest = values[-1]
    change_from_previous = round(latest - values[-2], 2)
    prior_mean = sum(values[:-1]) / (n - 1)
    band = abs(prior_mean) * _STABLE_BAND
    if latest > prior_mean + band:
        direction = "rising"
    elif latest < prior_mean - band:
        direction = "falling"
    else:
        direction = "stable"
    return direction, change_from_previous