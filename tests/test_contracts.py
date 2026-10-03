"""Prove shared boundaries and independent expected values from T4 examples."""

import inspect
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from treatment_planner.demo import (
    ORDER,
    SCENARIOS,
    FixtureComparator,
    SyntheticRiverProvider,
    SyntheticWeatherProvider,
    fixture_environment,
    fixture_request,
    fixture_settings,
)
from treatment_planner.interfaces import (
    CheckStatus,
    PlanComparator,
    ResultStatus,
    RiverProvider,
    TimeWindow,
    WeatherProvider,
    WeatherWindow,
)

IMPLEMENTATIONS = (
    (SyntheticRiverProvider(), RiverProvider, "load"),
    (SyntheticWeatherProvider(), WeatherProvider, "load"),
    (FixtureComparator("Baseline"), PlanComparator, "compare"),
)


@pytest.mark.parametrize("implementation,contract,method", IMPLEMENTATIONS)
def test_component_signature(implementation, contract, method):
    assert isinstance(implementation, contract)
    actual = inspect.signature(getattr(type(implementation), method))
    expected = inspect.signature(getattr(contract, method))
    assert list(actual.parameters) == list(expected.parameters)
    assert [p.kind for p in actual.parameters.values()] == [
        p.kind for p in expected.parameters.values()
    ]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_comparison_returns_shared_models_with_aware_events(scenario):
    plans = FixtureComparator(scenario).compare(
        fixture_request(), fixture_environment(scenario), fixture_settings(scenario)
    )
    assert plans
    assert len({plan.plan_id for plan in plans}) == len(plans)
    for plan in plans:
        assert plan.assumptions
        assert all(event.interval.start.utcoffset() is not None for event in plan.events)
        assert len({event.event_id for event in plan.events}) == len(plan.events)
        if plan.status == ResultStatus.CONFIRMED:
            assert all(check.status == CheckStatus.PASS for check in plan.checks)


def test_low_water_expected_margins_and_waiting():
    keep, postpone, truck = FixtureComparator("Low water").compare(
        fixture_request(), fixture_environment("Low water"), fixture_settings("Low water")
    )
    assert keep.status == ResultStatus.INFEASIBLE
    production = next(check for check in keep.checks if check.constraint == "Production completion")
    assert production.margin == timedelta(hours=-5)
    assert next(
        event for event in keep.events if event.event_id == "waiting"
    ).interval == TimeWindow(
        datetime(2026, 11, 7, 9, tzinfo=UTC), datetime(2026, 11, 7, 20, tzinfo=UTC)
    )
    assert postpone.collection_shift == timedelta(hours=12)
    assert postpone.status == truck.status == ResultStatus.CONFIRMED
    assert next(event for event in truck.events if event.event_id == "truck-prep").interval == (
        TimeWindow(ORDER, datetime(2026, 11, 1, 14, tzinfo=UTC))
    )


def test_hot_return_has_advance_preparation_and_handling():
    bicycle, car = FixtureComparator("Hot return").compare(
        fixture_request(), fixture_environment("Hot return"), fixture_settings("Hot return")
    )
    assert bicycle.status == ResultStatus.INFEASIBLE
    assert car.status == ResultStatus.CONFIRMED
    preparation = next(event for event in car.events if event.event_id == "return-prep")
    assert preparation.interval == TimeWindow(
        datetime(2026, 11, 7, 19, tzinfo=UTC), datetime(2026, 11, 8, 3, tzinfo=UTC)
    )
    handling = next(event for event in car.events if event.event_id == "handling")
    assert handling.interval.end == datetime(2026, 11, 8, 5, tzinfo=UTC)


def test_fixture_comparator_cannot_claim_to_replan_changed_inputs():
    changed = replace(fixture_request(), decision_time=ORDER + timedelta(hours=1))
    with pytest.raises(ValueError, match="changed inputs"):
        FixtureComparator("Baseline").compare(
            changed, fixture_environment("Baseline"), fixture_settings()
        )


def test_missing_forecast_coverage_and_values_remain_unknown():
    provider = SyntheticWeatherProvider()
    window = TimeWindow(ORDER, ORDER + timedelta(days=20))
    report = provider.load("Basel", window)
    assert not report.windows
    assert report.issues
    known = provider.load("Basel", TimeWindow(ORDER, ORDER + timedelta(hours=1))).windows[0]
    unknown = WeatherWindow(known.location, known.interval, None, None, known.provenance)
    assert unknown.maximum_temperature_c is None and unknown.snowfall is None


def test_timestamp_and_route_boundaries_reject_ambiguous_inputs():
    with pytest.raises(ValueError, match="timezone-aware"):
        TimeWindow(datetime(2026, 11, 1), datetime(2026, 11, 2))
    with pytest.raises(ValueError, match="end after"):
        TimeWindow(ORDER, ORDER)
    request = fixture_request()
    with pytest.raises(ValueError, match="each courier leg"):
        replace(request, routes=(request.routes[0], request.routes[0]))


def test_app_comparison_and_inspection_stay_in_sync():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run(timeout=20)
    assert not app.exception
    assert "Synthetic foundation" in app.warning[0].value
    app.selectbox[0].select("Low water").run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 3
    app.selectbox[1].select(2).run()
    assert not app.exception
    assert any(header.value == "Truck + original collection" for header in app.subheader)
    assert "Truck approval / preparation" in app.dataframe[2].value["Event"].tolist()
    app.selectbox[0].select("Hot return").run()
    app.selectbox[1].select(1).run()
    assert not app.exception
    assert "Return car preparation" in app.dataframe[2].value["Event"].tolist()
