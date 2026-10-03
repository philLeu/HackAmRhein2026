"""Independent simulated route conditions feed real planner checks."""

from dataclasses import replace
from datetime import timedelta

import pytest

from treatment_planner.demo import ORDER, fixture_environment, fixture_request, fixture_settings
from treatment_planner.interfaces import (
    Availability,
    CheckStatus,
    CourierLeg,
    DemoOverrides,
    EvidenceKind,
    LocalRouteOverride,
    ResultStatus,
    RouteSnow,
    TimeWindow,
    TransportMode,
    WeatherProvider,
    WeatherReport,
)
from treatment_planner.planning import PlanningComparator
from treatment_planner.weather_demo import DemoWeatherProvider, demo_carry_over, demo_route_input


def override(leg, interval, **changes):
    provenance = fixture_request().routes[0].provenance
    baseline = LocalRouteOverride(
        leg, interval, 20, False, RouteSnow.CLEAR, Availability.AVAILABLE, provenance
    )
    return replace(baseline, **changes)


def baseline_journeys():
    comparator = PlanningComparator(t4_replay=True)
    plan = comparator.evaluate(
        fixture_request(),
        fixture_environment("Baseline"),
        fixture_settings(),
        TransportMode.SHIP,
        TransportMode.BICYCLE,
        TransportMode.BICYCLE,
        timedelta(0),
    )
    return {e.event_id: e.interval for e in plan.events if e.event_id in ("sample", "return")}


def evaluate_demo(overrides, outbound=TransportMode.BICYCLE, returning=TransportMode.BICYCLE):
    intervals = baseline_journeys()
    request = replace(
        fixture_request(),
        routes=(demo_route_input(overrides.sample), demo_route_input(overrides.treatment)),
    )
    reports = [
        DemoWeatherProvider(value).load(value.leg.value, intervals[event])
        for value, event in ((overrides.sample, "sample"), (overrides.treatment, "return"))
    ]
    environment = replace(
        fixture_environment("Baseline"),
        weather=WeatherReport(tuple(w for report in reports for w in report.windows)),
    )
    return PlanningComparator(t4_replay=True).evaluate(
        request,
        environment,
        fixture_settings(),
        TransportMode.SHIP,
        outbound,
        returning,
        timedelta(0),
    )


def test_only_return_heat_changes_return_check_and_car_recovers():
    journeys = baseline_journeys()
    sample = override(CourierLeg.OUTBOUND, journeys["sample"])
    treatment = override(CourierLeg.RETURN, journeys["return"], maximum_temperature_c=30.1)
    overrides = DemoOverrides(sample=sample, treatment=treatment)
    bicycle = evaluate_demo(overrides)
    checks = {check.constraint: check.status for check in bicycle.checks}
    assert checks["Outbound weather"] == CheckStatus.PASS
    assert checks["Return weather"] == CheckStatus.FAIL
    assert bicycle.status == ResultStatus.INFEASIBLE
    assert evaluate_demo(overrides, returning=TransportMode.CAR).status == ResultStatus.CONFIRMED
    assert overrides.sample.maximum_temperature_c == 20


def test_forecast_snow_route_snow_and_car_availability_remain_independent():
    journeys = baseline_journeys()
    sample = override(CourierLeg.OUTBOUND, journeys["sample"], route_snow=RouteSnow.PRESENT)
    treatment = override(
        CourierLeg.RETURN, journeys["return"], car_availability=Availability.UNAVAILABLE
    )
    overrides = DemoOverrides(sample=sample, treatment=treatment)
    blocked = evaluate_demo(overrides)
    checks = {check.constraint: check.status for check in blocked.checks}
    assert checks["Outbound weather"] == CheckStatus.PASS
    assert checks["Outbound route snow"] == CheckStatus.FAIL
    assert checks["Return route snow"] == CheckStatus.PASS
    assert evaluate_demo(overrides, outbound=TransportMode.CAR).status == ResultStatus.CONFIRMED
    both_cars = evaluate_demo(overrides, TransportMode.CAR, TransportMode.CAR)
    assert any(
        c.constraint == "Return car availability" and c.status == CheckStatus.FAIL
        for c in both_cars.checks
    )


def test_unknown_demo_values_never_establish_bicycle_eligibility():
    journeys = baseline_journeys()
    overrides = DemoOverrides(
        sample=override(
            CourierLeg.OUTBOUND,
            journeys["sample"],
            maximum_temperature_c=None,
            forecast_snowfall=None,
            route_snow=RouteSnow.UNKNOWN,
        ),
        treatment=override(CourierLeg.RETURN, journeys["return"]),
    )
    plan = evaluate_demo(overrides)
    checks = {c.constraint: c.status for c in plan.checks}
    assert checks["Outbound weather"] == CheckStatus.UNKNOWN
    assert checks["Outbound route snow"] == CheckStatus.UNKNOWN
    assert checks["Return weather"] == CheckStatus.PASS
    assert plan.status == ResultStatus.UNCONFIRMED


def test_carry_over_preserves_original_simulated_evidence_and_unknowns():
    original = TimeWindow(ORDER + timedelta(hours=1), ORDER + timedelta(hours=2))
    moved = TimeWindow(original.start + timedelta(days=10), original.end + timedelta(days=10))
    entered = override(
        CourierLeg.OUTBOUND, original, maximum_temperature_c=None, forecast_snowfall=None
    )
    provider = DemoWeatherProvider(entered)
    assert isinstance(provider, WeatherProvider)
    assert demo_carry_over(entered, original) is None
    assert demo_carry_over(entered, moved) == original
    weather = provider.load(CourierLeg.OUTBOUND.value, moved).windows[0]
    assert weather.interval == moved
    assert weather.provenance == entered.provenance
    assert weather.maximum_temperature_c is None and weather.snowfall is None
    assert demo_route_input(entered).checked_at == ORDER
    assert entered.interval == original


def test_demo_adapter_rejects_real_provenance_and_wrong_route():
    entered = override(CourierLeg.OUTBOUND, baseline_journeys()["sample"])
    real = replace(entered, provenance=replace(entered.provenance, kind=EvidenceKind.MANUAL))
    with pytest.raises(ValueError, match="synthetic"):
        DemoWeatherProvider(real)
    with pytest.raises(ValueError, match="synthetic"):
        demo_carry_over(real, real.interval)
    with pytest.raises(ValueError, match="own courier leg"):
        DemoWeatherProvider(entered).load(CourierLeg.RETURN.value, entered.interval)


@pytest.mark.parametrize("temperature", [float("nan"), float("inf"), True])
def test_invalid_simulated_temperature_cannot_be_used_as_evidence(temperature):
    entered = override(CourierLeg.OUTBOUND, baseline_journeys()["sample"])
    with pytest.raises(ValueError, match="finite or unknown"):
        DemoWeatherProvider(replace(entered, maximum_temperature_c=temperature))
