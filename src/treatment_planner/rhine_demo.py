"""Live Rhine evidence and explicitly simulated ingredient-route inputs.

The Basel gauge and its forecast describe one station. They do not prove
Rotterdam--Basel navigability or predict an ingredient delivery delay.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path

from treatment_planner.data.rhine import RhineObservationProvider
from treatment_planner.data.rhine_forecast import load_live_forecast
from treatment_planner.interfaces import (
    EvidenceKind,
    IngredientRouteOverride,
    PlanningSettings,
    Provenance,
    RiverForecastReport,
    RiverReport,
    TimeWindow,
)
from treatment_planner.rhine_conditions import forecast_usable

CONFIG = Path(__file__).resolve().parents[2] / "config/rhine.json"
OBSERVATION_MAX_AGE = timedelta(hours=6)
FORECAST_MAX_AGE = timedelta(hours=24)
OBSERVATION_LOOKBACK = timedelta(days=2)


class RhineEvidenceState(StrEnum):
    AVAILABLE = "available"
    MISSING = "missing"
    STALE = "stale"
    OUTSIDE_HORIZON = "outside forecast horizon"


@dataclass(frozen=True)
class RhineRouteEvidence:
    """Station evidence scoped to an ingredient journey interval."""

    interval: TimeWindow
    evaluated_at: datetime
    history: RiverReport
    forecast: RiverForecastReport
    state: RhineEvidenceState
    covered_until: datetime | None
    issues: tuple[str, ...] = ()


def assess_live_evidence(
    interval: TimeWindow,
    evaluated_at: datetime,
    history: RiverReport,
    forecast: RiverForecastReport,
) -> RhineRouteEvidence:
    """Label missing, stale and out-of-horizon station evidence explicitly."""
    if evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
        raise ValueError("Use a timezone-aware evaluation time.")

    issues = list(history.issues + forecast.issues)
    readings = [r for r in history.observations if r.observed_at <= evaluated_at]
    latest = max(readings, key=lambda r: r.observed_at) if readings else None
    if latest is None or latest.water_level_m is None:
        issues.append("Missing current Rhine gauge observation.")
        state = RhineEvidenceState.MISSING
    elif evaluated_at - latest.observed_at > OBSERVATION_MAX_AGE:
        issues.append("Current Rhine gauge observation is stale.")
        state = RhineEvidenceState.STALE
    elif not forecast.points or forecast.provenance is None:
        issues.append("Missing Rhine forecast for the ingredient journey.")
        state = RhineEvidenceState.MISSING
    elif not forecast_usable(forecast, evaluated_at, FORECAST_MAX_AGE):
        issues.append("Rhine forecast is stale or has a future issue time.")
        state = RhineEvidenceState.STALE
    else:
        first = min(p.timestamp for p in forecast.points)
        covered_until = max(p.timestamp for p in forecast.points)
        future_start = max(interval.start, evaluated_at)
        if future_start < first or interval.end > covered_until:
            issues.append(
                "Ingredient journey extends outside the available Rhine forecast horizon."
            )
            state = RhineEvidenceState.OUTSIDE_HORIZON
        else:
            state = RhineEvidenceState.AVAILABLE
    covered_until = max((p.timestamp for p in forecast.points), default=None)
    return RhineRouteEvidence(
        interval,
        evaluated_at,
        history,
        forecast,
        state,
        covered_until,
        tuple(dict.fromkeys(issues)),
    )


def load_live_rhine_evidence(
    interval: TimeWindow,
    *,
    evaluated_at: datetime | None = None,
) -> RhineRouteEvidence:
    """Load live station observations and the current BAFU forecast by default.

    The requested route interval is checked against forecast coverage. No
    replay or synthetic evidence is substituted if either provider fails.
    """
    now = evaluated_at or datetime.now(UTC)
    history_window = TimeWindow(now - OBSERVATION_LOOKBACK, now + timedelta(microseconds=1))
    history = RhineObservationProvider(OBSERVATION_MAX_AGE).load(history_window)
    forecast = load_live_forecast()
    return assess_live_evidence(interval, now, history, forecast)


def build_demo_rhine_override(
    gauge_height_cm: float | None,
    interval: TimeWindow,
    *,
    entered_at: datetime,
) -> IngredientRouteOverride:
    """Create a clearly labelled synthetic Basel gauge override."""
    if gauge_height_cm is not None and (
        isinstance(gauge_height_cm, bool)
        or not isinstance(gauge_height_cm, (int, float))
        or not math.isfinite(gauge_height_cm)
    ):
        raise ValueError("The simulated gauge height must be a finite number of centimetres.")
    if entered_at.tzinfo is None or entered_at.utcoffset() is None:
        raise ValueError("Use a timezone-aware entry time.")
    return IngredientRouteOverride(
        gauge_height_cm=gauge_height_cm,
        interval=interval,
        provenance=Provenance(
            "Demo control: simulated Basel Rhine gauge height (cm)",
            EvidenceKind.SYNTHETIC,
            entered_at,
            entered_at,
        ),
    )


def demo_rhine_delay(override: IngredientRouteOverride) -> timedelta | None:
    """Map a demo-only low-water threshold crossing to the T4 12-hour scenario.

    The mapping is an illustrative simulation, not a delivery prediction.
    Missing gauge input returns None so callers cannot mistake unknown for zero.
    """
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    gauge_height_cm = override.gauge_height_cm
    if gauge_height_cm is None:
        return None
    if (
        isinstance(gauge_height_cm, bool)
        or not isinstance(gauge_height_cm, (int, float))
        or not math.isfinite(gauge_height_cm)
    ):
        return None
    critical_low_water_draft_cm = config["low_thresholds"][0]["limit"]
    available_draft_cm = gauge_height_cm - config["draft_offset_cm"]
    low_water = available_draft_cm < critical_low_water_draft_cm
    hours = config["demo_low_water_delay_hours"] if low_water else 0
    if isinstance(hours, bool) or not isinstance(hours, (int, float)) or not math.isfinite(hours):
        raise ValueError("Configured Rhine demo delay must be a finite number of hours.")
    return timedelta(hours=hours)


def apply_demo_rhine_delay(
    settings: PlanningSettings,
    override: IngredientRouteOverride,
) -> PlanningSettings | None:
    """Apply the demo gauge mapping; None means delay evidence is unknown."""
    delay = demo_rhine_delay(override)
    return None if delay is None else replace(settings, river_delay=delay)
