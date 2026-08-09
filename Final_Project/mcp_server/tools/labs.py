import database
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import interpret
from models import LabResult, LabResultList, LabTestList


def list_lab_tests() -> LabTestList:
    user_id = database.resolve_active_user_id()
    rows = database.query_all(
        "SELECT DISTINCT name FROM health_lab_results WHERE user_id = ? ORDER BY name",
        (user_id,),
    )
    return LabTestList(count=len(rows), tests=[r["name"] for r in rows])


def get_lab_results(test_name: str) -> LabResult:
    user_id = database.resolve_active_user_id()
    rows = database.query_all(
        "SELECT name, value_numeric, unit, reference_range_low, reference_range_high, recorded_at "
        "FROM health_lab_results "
        "WHERE user_id = ? AND name LIKE ? "
        "ORDER BY recorded_at ASC", 
        (user_id, f"%{test_name}%"),
    )
    if not rows:
        return LabResult(found=False)

    latest = rows[-1]
    numeric_series = [r["value_numeric"] for r in rows if r["value_numeric"] is not None]
    direction, change = interpret.summarize_trend(numeric_series)
    status = interpret.classify_range(
        latest["value_numeric"],
        latest["reference_range_low"],
        latest["reference_range_high"],
    )
    return LabResult(
        found=True,
        name=latest["name"],
        value=latest["value_numeric"],
        unit=latest["unit"],
        recorded_at=latest["recorded_at"],
        reference_low=latest["reference_range_low"],
        reference_high=latest["reference_range_high"],
        range_status=status,
        is_anomaly=status in ("below", "above"),
        trend=direction,
        change_from_previous=change,
        readings_considered=len(numeric_series),
    )


def get_recent_lab_results(limit: int = 5) -> LabResultList:
    user_id = database.resolve_active_user_id()
    rows = database.query_all(
        "SELECT name, value_numeric, unit, reference_range_low, reference_range_high, recorded_at "
        "FROM health_lab_results WHERE user_id = ? "
        "ORDER BY recorded_at DESC LIMIT ?",
        (user_id, limit),
    )
    results: list[LabResult] = []
    for r in rows:
        status = interpret.classify_range(
            r["value_numeric"], r["reference_range_low"], r["reference_range_high"]
        )
        results.append(
            LabResult(
                found=True,
                name=r["name"],
                value=r["value_numeric"],
                unit=r["unit"],
                recorded_at=r["recorded_at"],
                reference_low=r["reference_range_low"],
                reference_high=r["reference_range_high"],
                range_status=status,
                is_anomaly=status in ("below", "above"),
            )
        )
    return LabResultList(count=len(results), results=results)


def register(mcp) -> None:
    """Attach this module's tools to the MCP server."""
    mcp.tool()(list_lab_tests)
    mcp.tool()(get_lab_results)
    mcp.tool()(get_recent_lab_results)