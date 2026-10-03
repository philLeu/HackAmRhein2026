"""Real capture parser validation, including malformed and missing ensemble data."""

import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from treatment_planner.data.rhine_forecast import load_forecast_replay, parse_forecast
from treatment_planner.interfaces import EvidenceKind, RiverForecastPoint

CAPTURE = Path(__file__).resolve().parents[1] / "data/replay/rhine/forecast-capture"
NOW = datetime(2026, 10, 3, 11, 30, tzinfo=UTC)


def payload():
    return json.loads((CAPTURE / "forecast.json").read_text("utf-8"))


def test_real_capture_units_times_and_bounds():
    history, forecast, now = load_forecast_replay(CAPTURE)
    assert len(history.observations) == 576
    assert len(forecast.points) == 118
    assert now == NOW
    assert forecast.provenance.kind == EvidenceKind.REPLAY
    assert forecast.provenance.source_time == datetime(2026, 10, 3, 9, tzinfo=UTC)
    point = forecast.points[0]
    assert isinstance(point, RiverForecastPoint)
    assert point.median_cm == 477
    assert point.minimum_cm <= point.p25_cm <= point.median_cm <= point.p75_cm <= point.maximum_cm
    assert not forecast.issues
    assert max(r.observed_at for r in history.observations) < now


@pytest.mark.parametrize(
    "mutation",
    ["nan", "duplicate", "offset", "polygon", "missing_issue", "issue_disagree", "bounds"],
)
def test_bad_source_never_becomes_normal(mutation):
    source = copy.deepcopy(payload())
    median = next(t for t in source["plot"]["data"] if t["name"] == "Median")
    if mutation == "nan":
        median["y"][0] = float("nan")
    elif mutation == "duplicate":
        median["x"][1] = median["x"][0]
    elif mutation == "offset":
        median["x"][0] = "2026-10-03T11:00:00"
    elif mutation == "polygon":
        next(t for t in source["plot"]["data"] if "Percentile" in t["name"])["x"][0] = median["x"][
            1
        ]
    elif mutation == "missing_issue":
        source["plot"]["layout"]["annotations"] = []
    elif mutation == "issue_disagree":
        source["plot"]["layout"]["annotations"][1]["x"] = median["x"][1]
    elif mutation == "bounds":
        median["y"][0] = 250
    report = parse_forecast(source, NOW)
    assert not report.points
    assert report.issues


def test_missing_bands_keep_median_and_explicit_issues():
    source = payload()
    source["plot"]["data"] = [
        t for t in source["plot"]["data"] if t["name"] in ("Median", "Measured")
    ]
    report = parse_forecast(source, NOW)
    assert len(report.points) == 118
    assert len(report.issues) == 2
    assert report.points[0].minimum_cm is None


def test_missing_replay_is_explicit(tmp_path):
    history, forecast, now = load_forecast_replay(tmp_path)
    assert history.issues and forecast.issues
    assert not history.observations and not forecast.points
    assert now == NOW


def test_forecast_contract_rejects_naive_time():
    with pytest.raises(ValueError, match="timezone-aware"):
        RiverForecastPoint(datetime(2026, 10, 3), 477)


def test_live_failure_does_not_fallback_to_replay(monkeypatch):
    from treatment_planner.data import rhine_forecast

    def unavailable(*args):
        raise OSError("network unavailable")

    monkeypatch.setattr(rhine_forecast, "_fetch_json", unavailable)
    report = rhine_forecast.load_live_forecast()
    assert not report.points
    assert "retrieval failed" in report.issues[0]
