"""Independent threshold and forecast-window acceptance cases."""

from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from treatment_planner.data.rhine_forecast import load_forecast_replay
from treatment_planner.interfaces import RiverForecastPoint, RiverStatus
from treatment_planner.rhine_conditions import assess_conditions, summarize_conditions

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "height,status",
    [
        (475.99, "critical"),
        (476, "warning"),
        (479.7, "warning"),
        (596, "watch"),
        (601, "watch"),
        (601.01, "normal"),
        (615, "watch"),
        (620, "watch"),
        (620.01, "warning"),
        (670, "warning"),
        (700, "warning"),
        (790, "warning"),
        (790.01, "critical"),
        (None, "unknown"),
        (float("nan"), "unknown"),
        (float("inf"), "unknown"),
    ],
)
def test_notebook_boundaries(height, status):
    assert assess_conditions(height).status.value == status


def test_warning_can_also_approach_critical():
    assessment = assess_conditions(479.7)
    assert assessment.status == RiverStatus.WARNING
    assert [(f.state, f.severity.value) for f in assessment.findings] == [
        ("breached", "warning"),
        ("margin", "critical"),
    ]


def test_worst_future_class_excludes_past_and_exposes_partial_horizon():
    history, forecast, now = load_forecast_replay(ROOT / "data/replay/rhine/forecast-capture")
    forecast = replace(
        forecast,
        points=(
            RiverForecastPoint(now - timedelta(hours=1), 800),
            RiverForecastPoint(now + timedelta(hours=1), 610),
            RiverForecastPoint(now + timedelta(hours=2), 475),
            RiverForecastPoint(now + timedelta(hours=3), 610),
        ),
    )
    summary = summarize_conditions(
        history, forecast, now, 5, timedelta(hours=6), timedelta(hours=24)
    )
    assert summary.forecast.status == RiverStatus.CRITICAL
    assert summary.first_at == now + timedelta(hours=2)
    assert not summary.complete
    assert summary.covered_until == now + timedelta(hours=3)


def test_stale_and_future_issued_runs_are_unknown():
    history, forecast, now = load_forecast_replay(ROOT / "data/replay/rhine/forecast-capture")
    stale = summarize_conditions(
        history, forecast, now + timedelta(days=2), 1, timedelta(hours=6), timedelta(hours=24)
    )
    assert stale.current.status == stale.forecast.status == RiverStatus.UNKNOWN
    future = replace(
        forecast, provenance=replace(forecast.provenance, source_time=now + timedelta(hours=1))
    )
    summary = summarize_conditions(history, future, now, 1, timedelta(hours=6), timedelta(hours=24))
    assert summary.forecast.status == RiverStatus.UNKNOWN
