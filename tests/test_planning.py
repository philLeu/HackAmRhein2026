"""Executable T4 acceptance scenarios and uncertainty/deadline boundaries."""

import inspect
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from treatment_planner.demo import EVIDENCE, ORDER, fixture_request
from treatment_planner.interfaces import (
    Availability,
    CandidatePlan,
    CheckStatus,
    CourierLeg,
    EnvironmentInputs,
    EvidenceKind,
    PlanComparator,
    ResultStatus,
    RiverReport,
    RouteSnow,
    TimeWindow,
    TransportMode,
    WeatherReport,
    WeatherWindow,
)
from treatment_planner.planning import PlanningComparator, load_settings

H = timedelta(hours=1)
MINUTE = timedelta(minutes=1)
SHIP, TRUCK, BIKE, CAR = (
    TransportMode.SHIP,
    TransportMode.TRUCK,
    TransportMode.BICYCLE,
    TransportMode.CAR,
)


@pytest.fixture
def settings():
    return load_settings(Path(__file__).resolve().parents[1] / "config/planning.json")


def environment(*, temperature=20, snowfall=False, end=400):
    return EnvironmentInputs(
        RiverReport(()),
        WeatherReport(
            (
                WeatherWindow(
                    "Invented Basel route",
                    TimeWindow(ORDER, ORDER + end * H),
                    temperature,
                    snowfall,
                    EVIDENCE,
                ),
            )
        ),
    )


def evaluate(
    settings,
    *,
    request=None,
    env=None,
    shipment=SHIP,
    outbound=BIKE,
    returning=BIKE,
    shift=timedelta(),
    replay=True,
    late=False,
):
    return PlanningComparator(t4_replay=replay).evaluate(
        request or fixture_request(),
        env or environment(),
        settings,
        shipment,
        outbound,
        returning,
        shift,
        prepare_return_at_completion=late,
    )


def check(plan, name):
    return next(c for c in plan.checks if c.constraint == name)


def event(plan, name):
    return next(e for e in plan.events if e.event_id == name).interval


def test_real_comparator_contract_and_unique_outputs(settings):
    comparator = PlanningComparator(t4_replay=True)
    assert isinstance(comparator, PlanComparator)
    assert list(inspect.signature(comparator.compare).parameters) == [
        "request",
        "environment",
        "settings",
    ]
    plans = comparator.compare(fixture_request(), environment(), settings)
    assert all(isinstance(p, CandidatePlan) for p in plans)
    assert len({p.plan_id for p in plans}) == len(plans)
    for plan in plans:
        assert timedelta() <= plan.collection_shift <= 24 * H
        assert len({e.event_id for e in plan.events}) == len(plan.events)
        if plan.status == ResultStatus.CONFIRMED:
            assert all(c.status == CheckStatus.PASS for c in plan.checks)


def test_s1_baseline(settings):
    plan = evaluate(settings)
    assert plan.status == ResultStatus.CONFIRMED
    for name, margin in [
        ("Ingredient arrival", 96),
        ("Sample arrival", 11),
        ("Production completion", 6),
        ("Injection", 6),
    ]:
        assert check(plan, name).margin == margin * H
    assert event(plan, "ingredients") == TimeWindow(ORDER + 6 * H, ORDER + 144 * H)
    assert event(plan, "processing") == TimeWindow(ORDER + 145 * H, ORDER + 163 * H)
    assert event(plan, "handling").end == ORDER + 165 * H


def test_s2_keep_postpone_and_truck_generated(settings):
    settings = replace(settings, river_delay=12 * H)
    plans = PlanningComparator(t4_replay=True).compare(fixture_request(), environment(), settings)

    def find(mode, shift):
        return next(
            p
            for p in plans
            if p.ingredient_mode == mode
            and p.collection_shift == shift
            and p.outbound_mode == p.return_mode == BIKE
        )

    keep, postpone, truck = find(SHIP, 0 * H), find(SHIP, 12 * H), find(TRUCK, 0 * H)
    assert keep.status == ResultStatus.INFEASIBLE
    assert check(keep, "Production completion").margin == -5 * H
    assert check(keep, "Ingredient arrival").margin == 84 * H
    assert event(keep, "waiting") == TimeWindow(ORDER + 145 * H, ORDER + 156 * H)
    assert postpone.status == truck.status == ResultStatus.CONFIRMED
    assert event(postpone, "handling").end == ORDER + 177 * H
    assert event(truck, "truck-prep") == TimeWindow(ORDER, ORDER + 6 * H)
    assert event(truck, "ingredients") == TimeWindow(ORDER + 6 * H, ORDER + 54 * H)
    assert check(truck, "Ingredient arrival").margin == 186 * H
    # The critical-time search also finds first recovery, at exactly zero margin.
    assert check(find(SHIP, 5 * H), "Production completion").margin == 0 * H


def hot_environment(leg, temperature):
    start = 144 if leg == CourierLeg.OUTBOUND else 163
    return replace(
        environment(),
        weather=WeatherReport(
            tuple(
                WeatherWindow(
                    "Invented Basel route",
                    TimeWindow(ORDER + a * H, ORDER + b * H),
                    value,
                    False,
                    EVIDENCE,
                )
                for a, b, value in [
                    (0, start, 20),
                    (start, start + 1, temperature),
                    (start + 1, 400, 20),
                ]
            )
        ),
    )


@pytest.mark.parametrize("leg", list(CourierLeg))
def test_s3_heat_boundary_and_mixed_modes(settings, leg):
    assert evaluate(settings, env=hot_environment(leg, 30)).status == ResultStatus.CONFIRMED
    hot = hot_environment(leg, 30.1)
    assert evaluate(settings, env=hot).status == ResultStatus.INFEASIBLE
    plan = evaluate(
        settings,
        env=hot,
        outbound=CAR if leg == CourierLeg.OUTBOUND else BIKE,
        returning=CAR if leg == CourierLeg.RETURN else BIKE,
    )
    assert plan.status == ResultStatus.CONFIRMED
    prep = event(plan, "outbound-prep" if leg == CourierLeg.OUTBOUND else "return-prep")
    assert prep == TimeWindow(
        ORDER + (136 if leg == CourierLeg.OUTBOUND else 155) * H,
        ORDER + (144 if leg == CourierLeg.OUTBOUND else 163) * H,
    )
    assert check(plan, "Injection").margin == 6 * H


def test_s3_late_preparation_and_decision_limit(settings):
    late = evaluate(settings, returning=CAR, late=True)
    assert late.status == ResultStatus.INFEASIBLE
    assert check(late, "Injection").margin == -2 * H
    request = replace(fixture_request(), decision_time=ORDER + 142 * H)
    plan = evaluate(settings, request=request, outbound=CAR, returning=CAR)
    assert event(plan, "outbound-prep").start == request.decision_time
    assert check(plan, "Outbound preparation").status == CheckStatus.FAIL
    assert event(plan, "sample").start == ORDER + 150 * H
    assert event(plan, "return-prep").start >= request.decision_time
    assert event(plan, "return-prep").end <= event(plan, "return").start
    assert event(plan, "return-prep").start < event(plan, "processing").end


def test_s4_snow_and_two_independent_cars(settings):
    request = fixture_request()
    request = replace(
        request,
        routes=tuple(
            replace(r, snow=RouteSnow.PRESENT) if r.leg == CourierLeg.RETURN else r
            for r in request.routes
        ),
    )
    env = replace(
        environment(),
        weather=WeatherReport(
            (
                WeatherWindow(
                    CourierLeg.OUTBOUND.value,
                    TimeWindow(ORDER, ORDER + 400 * H),
                    20,
                    True,
                    EVIDENCE,
                ),
                WeatherWindow(
                    CourierLeg.RETURN.value, TimeWindow(ORDER, ORDER + 400 * H), 20, False, EVIDENCE
                ),
            )
        ),
    )
    assert evaluate(settings, request=request, env=env).status == ResultStatus.INFEASIBLE
    car = evaluate(settings, request=request, env=env, outbound=CAR, returning=CAR)
    assert car.status == ResultStatus.CONFIRMED
    assert event(car, "outbound-prep") == TimeWindow(ORDER + 136 * H, ORDER + 144 * H)
    assert event(car, "return-prep") == TimeWindow(ORDER + 155 * H, ORDER + 163 * H)
    assert check(car, "Production completion").margin == 6 * H


@pytest.mark.parametrize(
    "availability,status",
    [
        (Availability.UNAVAILABLE, ResultStatus.INFEASIBLE),
        (Availability.UNKNOWN, ResultStatus.UNCONFIRMED),
    ],
)
def test_car_availability_independent_per_leg(settings, availability, status):
    request = fixture_request()
    request = replace(
        request,
        routes=tuple(
            replace(r, car_availability=availability) if r.leg == CourierLeg.RETURN else r
            for r in request.routes
        ),
    )
    assert evaluate(settings, request=request, returning=CAR).status == status
    assert evaluate(settings, request=request, outbound=CAR).status == ResultStatus.CONFIRMED


def test_s5_all_supported_alternatives_fail(settings):
    settings = replace(settings, river_delay=48 * H)
    request = fixture_request()
    request = replace(
        request,
        decision_time=ORDER + 136 * H,
        routes=tuple(replace(r, checked_at=ORDER + 136 * H) for r in request.routes),
    )
    plans = PlanningComparator(t4_replay=True).compare(request, environment(), settings)
    assert all(p.ingredient_mode == SHIP and p.status == ResultStatus.INFEASIBLE for p in plans)
    latest = evaluate(settings, request=request, shift=24 * H)
    assert check(latest, "Production completion").margin == -17 * H
    assert check(latest, "Ingredient arrival").margin == 48 * H
    assert (
        "future departure"
        in check(evaluate(settings, request=request, shipment=TRUCK), "Shipment switch").reason
    )


@pytest.mark.parametrize(
    "extra,status", [(timedelta(), CheckStatus.PASS), (MINUTE, CheckStatus.FAIL)]
)
def test_collection_boundary(settings, extra, status):
    assert check(evaluate(settings, shift=24 * H + extra), "Collection shift").status == status


@pytest.mark.parametrize(
    "name,field,boundary",
    [
        ("Ingredient arrival", "river_order_to_arrival", 240),
        ("Sample arrival", "bicycle_travel", 12),
        ("Production completion", "production_processing", 24),
        ("Injection", "hospital_handling", 7),
    ],
)
@pytest.mark.parametrize(
    "extra,status", [(timedelta(), CheckStatus.PASS), (MINUTE, CheckStatus.FAIL)]
)
def test_deadline_boundaries(settings, name, field, boundary, extra, status):
    plan = evaluate(replace(settings, **{field: boundary * H + extra}))
    assert check(plan, name).status == status
    assert check(plan, name).margin == -extra


@pytest.mark.parametrize(
    "decision,status",
    [(0, CheckStatus.PASS), (1, CheckStatus.FAIL), (6, CheckStatus.FAIL), (7, CheckStatus.FAIL)],
)
def test_truck_preparation_and_departure(settings, decision, status):
    request = replace(fixture_request(), decision_time=ORDER + decision * H)
    plan = evaluate(settings, request=request, shipment=TRUCK)
    assert check(plan, "Shipment switch").status == status
    assert event(plan, "truck-prep").start == request.decision_time


@pytest.mark.parametrize(
    "age,expected",
    [
        (6 * H, CheckStatus.PASS),
        (6 * H + MINUTE, CheckStatus.UNKNOWN),
        (-MINUTE, CheckStatus.UNKNOWN),
        (None, CheckStatus.UNKNOWN),
    ],
)
def test_manual_route_timestamp_boundaries(settings, age, expected):
    request = fixture_request()
    request = replace(
        request,
        routes=tuple(
            replace(r, checked_at=None if age is None else ORDER - age) for r in request.routes
        ),
    )
    assert check(evaluate(settings, request=request), "Outbound route snow").status == expected


def test_future_dispatch_and_missing_rhine_remain_unconfirmed(settings):
    plan = evaluate(settings, replay=False)
    assert plan.status == ResultStatus.UNCONFIRMED
    assert check(plan, "Outbound route snow").status == CheckStatus.UNKNOWN
    assert check(plan, "Rhine evidence").status == CheckStatus.UNKNOWN
    request = fixture_request()
    request = replace(
        request,
        routes=tuple(
            replace(r, provenance=replace(EVIDENCE, kind=EvidenceKind.MANUAL))
            for r in request.routes
        ),
    )
    assert evaluate(settings, request=request).status == ResultStatus.UNCONFIRMED


@pytest.mark.parametrize(
    "env",
    [
        environment(end=163),
        environment(temperature=None),
        environment(snowfall=None),
        environment(temperature=float("nan")),
        replace(environment(), weather=WeatherReport((), ("Stale forecast",))),
    ],
)
def test_unknown_weather_is_not_safe(settings, env):
    assert evaluate(settings, env=env).status == ResultStatus.UNCONFIRMED


def test_coverage_gap_and_half_open_heat_intervals(settings):
    gap = replace(
        environment(),
        weather=WeatherReport(
            (
                WeatherWindow(
                    "Invented Basel route",
                    TimeWindow(ORDER, ORDER + 144.5 * H),
                    20,
                    False,
                    EVIDENCE,
                ),
                WeatherWindow(
                    "Invented Basel route",
                    TimeWindow(ORDER + 144.75 * H, ORDER + 400 * H),
                    20,
                    False,
                    EVIDENCE,
                ),
            )
        ),
    )
    assert check(evaluate(settings, env=gap), "Outbound weather").status == CheckStatus.UNKNOWN
    # Heat starting exactly at arrival cannot block the preceding half-open journey.
    hot = hot_environment(CourierLeg.OUTBOUND, 30.1)
    assert (
        check(evaluate(settings, env=hot, shift=H), "Outbound weather").status == CheckStatus.PASS
    )


def test_failure_takes_priority_over_unknown(settings):
    plan = evaluate(settings, env=environment(temperature=31), replay=False)
    assert plan.status == ResultStatus.INFEASIBLE
    assert check(plan, "Rhine evidence").status == CheckStatus.UNKNOWN


def test_configuration_rejects_invalid_durations(settings):
    with pytest.raises(ValueError, match="production_processing"):
        evaluate(replace(settings, production_processing=timedelta()))


def test_inputs_are_not_modified(settings):
    request, env = fixture_request(), environment()
    saved = (repr(request), repr(env), repr(settings))
    PlanningComparator(t4_replay=True).compare(request, env, settings)
    assert saved == (repr(request), repr(env), repr(settings))


@pytest.mark.parametrize(
    "extra,status", [(timedelta(), CheckStatus.PASS), (MINUTE, CheckStatus.FAIL)]
)
def test_car_preparation_exact_boundary(settings, extra, status):
    request = replace(fixture_request(), decision_time=ORDER + 136 * H + extra)
    plan = evaluate(settings, request=request, outbound=CAR)
    assert check(plan, "Outbound preparation").status == status
    assert check(plan, "Outbound preparation").margin == -extra


def test_overlapping_unknown_weather_stays_unconfirmed(settings):
    known = environment()
    unknown = replace(known.weather.windows[0], maximum_temperature_c=None)
    env = replace(known, weather=WeatherReport(known.weather.windows + (unknown,)))
    assert evaluate(settings, env=env).status == ResultStatus.UNCONFIRMED


def test_both_car_legs_do_not_require_bicycle_weather(settings):
    env = replace(environment(), weather=WeatherReport((), ("No forecast",)))
    assert evaluate(settings, env=env, outbound=CAR, returning=CAR).status == ResultStatus.CONFIRMED
