"""Live evidence coverage and labelled simulated ingredient-route inputs."""

from datetime import UTC, datetime, timedelta

import pytest

from treatment_planner.interfaces import (
    EvidenceKind,
    PlanningSettings,
    Provenance,
    RiverForecastPoint,
    RiverForecastReport,
    RiverObservation,
    RiverReport,
    TimeWindow,
)
from treatment_planner.rhine_demo import (
    RhineEvidenceState,
    apply_demo_rhine_delay,
    assess_live_evidence,
    build_demo_rhine_override,
    demo_rhine_delay,
)

NOW = datetime(2026, 10, 3, 12, tzinfo=UTC)
INTERVAL = TimeWindow(NOW + timedelta(hours=1), NOW + timedelta(days=2))
SOURCE = "test fixture"
PROVENANCE = Provenance(SOURCE, EvidenceKind.OBSERVATION, NOW, NOW)


def evidence(*, observed_at=NOW, points=None, issued_at=NOW):
    history = RiverReport(
        (RiverObservation("Rheinhalle (2289)", observed_at, PROVENANCE, 4.7, 250),)
    )
    forecast = RiverForecastReport(
        tuple(
            points
            or (RiverForecastPoint(INTERVAL.start, 470), RiverForecastPoint(INTERVAL.end, 480))
        ),
        Provenance("BAFU forecast", EvidenceKind.FORECAST, issued_at, NOW),
    )
    return history, forecast


def test_live_evidence_is_available_only_when_fresh_and_fully_covered():
    history, forecast = evidence()
    result = assess_live_evidence(INTERVAL, NOW, history, forecast)
    assert result.state is RhineEvidenceState.AVAILABLE
    assert result.covered_until == INTERVAL.end


def test_live_loader_uses_live_providers_by_default_without_replay(monkeypatch):
    import treatment_planner.rhine_demo as rhine_demo

    history, forecast = evidence()
    calls = []

    class Provider:
        def __init__(self, maximum_age):
            calls.append(("observations", maximum_age))

        def load(self, window):
            calls.append(("window", window))
            return history

    monkeypatch.setattr(rhine_demo, "RhineObservationProvider", Provider)
    monkeypatch.setattr(rhine_demo, "load_live_forecast", lambda: forecast)
    loaded = rhine_demo.load_live_rhine_evidence(INTERVAL, evaluated_at=NOW)
    assert loaded.state is RhineEvidenceState.AVAILABLE
    assert calls[0] == ("observations", timedelta(hours=6))
    assert calls[1][0] == "window"


def test_missing_observation_and_forecast_are_explicit():
    _, forecast = evidence()
    no_observation = assess_live_evidence(INTERVAL, NOW, RiverReport(()), forecast)
    assert no_observation.state is RhineEvidenceState.MISSING
    assert any("Missing current" in issue for issue in no_observation.issues)

    history, _ = evidence()
    no_forecast = assess_live_evidence(INTERVAL, NOW, history, RiverForecastReport())
    assert no_forecast.state is RhineEvidenceState.MISSING
    assert any("Missing Rhine forecast" in issue for issue in no_forecast.issues)


def test_stale_observation_and_forecast_are_explicit():
    old = NOW - timedelta(hours=7)
    history, forecast = evidence(observed_at=old)
    stale_observation = assess_live_evidence(INTERVAL, NOW, history, forecast)
    assert stale_observation.state is RhineEvidenceState.STALE

    history, stale_forecast = evidence(issued_at=NOW - timedelta(hours=25))
    stale_run = assess_live_evidence(INTERVAL, NOW, history, stale_forecast)
    assert stale_run.state is RhineEvidenceState.STALE


def test_partial_forecast_does_not_extrapolate_past_coverage():
    history, forecast = evidence(
        points=(
            RiverForecastPoint(INTERVAL.start, 470),
            RiverForecastPoint(INTERVAL.end - timedelta(hours=1), 480),
        )
    )
    result = assess_live_evidence(INTERVAL, NOW, history, forecast)
    assert result.state is RhineEvidenceState.OUTSIDE_HORIZON
    assert any("outside" in issue for issue in result.issues)


def test_demo_override_is_labelled_synthetic_and_validated():
    override = build_demo_rhine_override(475.0, INTERVAL, entered_at=NOW)
    assert override.gauge_height_cm == 475.0
    assert override.provenance.kind is EvidenceKind.SYNTHETIC
    assert "simulated" in override.provenance.source
    with pytest.raises(ValueError, match="finite"):
        build_demo_rhine_override(float("nan"), INTERVAL, entered_at=NOW)


def test_demo_delay_mapping_is_labelled_and_does_not_change_live_evidence():
    settings = PlanningSettings(
        ingredient_limit=timedelta(days=10),
        collection_shift_limit=timedelta(days=1),
        sample_limit=timedelta(hours=12),
        production_limit=timedelta(days=1),
        injection_limit=timedelta(hours=8),
        river_order_to_arrival=timedelta(days=6),
        river_delay=timedelta(0),
        truck_travel=timedelta(days=2),
        truck_preparation=timedelta(hours=6),
        bicycle_travel=timedelta(hours=1),
        car_travel=timedelta(hours=1),
        car_preparation=timedelta(hours=8),
        production_processing=timedelta(hours=18),
        hospital_handling=timedelta(hours=1),
        route_status_freshness=timedelta(hours=6),
        bicycle_temperature_limit_c=30,
    )
    baseline_override = build_demo_rhine_override(476.01, INTERVAL, entered_at=NOW)
    low_water_override = build_demo_rhine_override(475.99, INTERVAL, entered_at=NOW)
    missing_override = build_demo_rhine_override(None, INTERVAL, entered_at=NOW)
    baseline = apply_demo_rhine_delay(settings, baseline_override)
    disrupted = apply_demo_rhine_delay(settings, low_water_override)
    assert baseline.river_delay == timedelta(0)
    assert disrupted.river_delay == timedelta(hours=12)
    assert demo_rhine_delay(missing_override) is None
    assert settings.river_delay == timedelta(0)
