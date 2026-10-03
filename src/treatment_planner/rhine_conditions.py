"""Notebook navigation classes and forecast summaries, independent of the UI."""

import json
import math
from datetime import datetime, timedelta
from pathlib import Path

from treatment_planner.interfaces import (
    RiverAssessment,
    RiverFinding,
    RiverForecastReport,
    RiverReport,
    RiverStatus,
    RiverSummary,
)

RULES = json.loads((Path(__file__).resolve().parents[2] / "config/rhine.json").read_text("utf-8"))
RANK = {
    RiverStatus.NORMAL: 0,
    RiverStatus.WATCH: 1,
    RiverStatus.WARNING: 2,
    RiverStatus.CRITICAL: 3,
}


def assess_conditions(gauge_height_cm: float | None) -> RiverAssessment:
    """Preserve notebook strict crossings, equality/watch and severity precedence."""
    if gauge_height_cm is None or not math.isfinite(gauge_height_cm):
        return RiverAssessment(RiverStatus.UNKNOWN, None, None)
    draft = gauge_height_cm - RULES["draft_offset_cm"]
    findings = []
    for family, value, quantity, too_high in (
        ("high_thresholds", gauge_height_cm, "water level", True),
        ("low_thresholds", draft, "available draft", False),
    ):
        for rule in RULES[family]:
            gap = value - rule["limit"] if too_high else rule["limit"] - value
            if gap < -RULES["margin_cm"]:
                continue
            crossed = gap > 0
            state = "breached" if crossed else "margin"
            direction = "above" if too_high else "below"
            detail = (
                f"{abs(gap):.1f} cm {direction} the threshold"
                if crossed
                else f"within {RULES['margin_cm']} cm of the threshold"
            )
            message = (
                f"{quantity.capitalize()} {value:.1f} cm: {detail} of "
                f"{rule['limit']} cm ({rule['label']}); {abs(gap):.1f} cm from the limit. "
                f"{'Consequence' if crossed else 'If crossed'}: {rule['consequence']}."
            )
            findings.append(
                RiverFinding(
                    state,
                    RiverStatus(rule["severity"]),
                    quantity,
                    rule["limit"],
                    abs(gap),
                    rule["consequence"],
                    message,
                )
            )
            if crossed:
                break
    findings.sort(key=lambda f: -RANK[f.severity if f.state == "breached" else RiverStatus.WATCH])
    status = max(
        (f.severity if f.state == "breached" else RiverStatus.WATCH for f in findings),
        key=RANK.get,
        default=RiverStatus.NORMAL,
    )
    return RiverAssessment(status, gauge_height_cm, draft, tuple(findings))


def forecast_usable(report: RiverForecastReport, now: datetime, maximum_age: timedelta) -> bool:
    """Unknown/future issue times and stale runs cannot support a verdict."""
    return bool(
        report.points
        and report.provenance
        and timedelta(0) <= now - report.provenance.source_time <= maximum_age
    )


def summarize_conditions(
    history: RiverReport,
    forecast: RiverForecastReport,
    now: datetime,
    days: int,
    observation_age: timedelta,
    forecast_age: timedelta,
) -> RiverSummary:
    """Worst future median class over the requested window, without extrapolation."""
    current = assess_conditions(None)
    issues = list(history.issues + forecast.issues)
    readings = [r for r in history.observations if r.observed_at <= now]
    if readings:
        latest = max(readings, key=lambda r: r.observed_at)
        if now - latest.observed_at <= observation_age:
            current = assess_conditions(
                None if latest.water_level_m is None else round(latest.water_level_m * 100, 6)
            )
        else:
            issues.append("Current Rhine assessment unavailable: observations are stale.")
    else:
        issues.append("Current Rhine assessment unavailable: no observations.")
    end = now + timedelta(days=days)
    points = [p for p in forecast.points if now < p.timestamp <= end]
    until = forecast.points[-1].timestamp if forecast.points else None
    usable = forecast_usable(forecast, now, forecast_age)
    if not usable:
        issues.append("Forecast assessment unavailable: missing, stale or future-issued forecast.")
    complete = bool(usable and points and forecast.points[0].timestamp <= now and until >= end)
    if usable and points:
        worst = max(points, key=lambda p: RANK[assess_conditions(p.median_cm).status])
        assessment = assess_conditions(worst.median_cm)
        first_at = worst.timestamp
    else:
        assessment, first_at = assess_conditions(None), None
    if not complete:
        issues.append(
            "Requested forecast window is not fully covered; no assessment beyond coverage."
        )
    return RiverSummary(
        current, assessment, first_at, until, complete, tuple(dict.fromkeys(issues))
    )
