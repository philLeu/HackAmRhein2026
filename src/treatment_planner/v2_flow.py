from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta

from treatment_planner.data.weather_live import WeatherLiveProvider
from treatment_planner.demo import EVIDENCE, ORDER, fixture_request
from treatment_planner.interfaces import (
    Availability,
    CandidatePlan,
    CheckStatus,
    CourierLeg,
    DemoOverrides,
    EnvironmentInputs,
    EvidenceKind,
    IngredientRouteOverride,
    LocalRouteInput,
    LocalRouteOverride,
    PlanningSettings,
    Provenance,
    ResultStatus,
    RiverReport,
    RouteId,
    RouteSnow,
    TimeWindow,
    TransportMode,
    TreatmentRequest,
    WeatherReport,
)
from treatment_planner.planning import PlanningComparator
from treatment_planner.rhine_demo import (
    OBSERVATION_MAX_AGE,
    RhineRouteEvidence,
    apply_demo_rhine_delay,
    demo_rhine_delay,
)
from treatment_planner.weather_demo import DemoWeatherProvider, demo_route_input

DEFAULT_INJECTION_OFFSET = timedelta(hours=165)
LIVE_RHINE_LOCATION = "Basel gauge (FOEN 2289)"
LIVE_WEATHER_POINTS = {
    "4056": "PulseShift production site, Basel",
    "4031": "University Hospital Basel",
}
LOCAL_ROUTE_EVENTS = {
    CourierLeg.OUTBOUND: ("sample", RouteId.SAMPLE, "Outbound"),
    CourierLeg.RETURN: ("return", RouteId.TREATMENT, "Return"),
}


def _live_request(now: datetime) -> TreatmentRequest:
    """Anchor the invented T4 schedule to the actual live planning clock."""
    template = fixture_request()
    offset = now - ORDER
    routes = tuple(
        LocalRouteInput(
            leg=route.leg,
            snow=RouteSnow.UNKNOWN,
            checked_at=None,
            car_availability=Availability.AVAILABLE,
            provenance=Provenance(
                "Awaiting coordinator route check",
                EvidenceKind.MANUAL,
                now,
                now,
            ),
        )
        for route in template.routes
    )
    return replace(
        template,
        order_time=template.order_time + offset,
        original_collection=template.original_collection + offset,
        nominal_departure=template.nominal_departure + offset,
        decision_time=now,
        routes=routes,
    )


def _event(plan: CandidatePlan, event_id: str):
    return next((event for event in plan.events if event.event_id == event_id), None)


def _journey_envelope(plans: tuple[CandidatePlan, ...], event_id: str) -> TimeWindow | None:
    intervals = [event.interval for plan in plans if (event := _event(plan, event_id)) is not None]
    if not intervals:
        return None
    return TimeWindow(
        min(interval.start for interval in intervals),
        max(interval.end for interval in intervals),
    )


def _probe_plans(
    request: TreatmentRequest,
    settings: PlanningSettings,
    *,
    demo: bool,
) -> tuple[CandidatePlan, ...]:
    comparator = PlanningComparator(
        weather_location="Invented Basel route",
        t4_replay=demo,
    )
    return comparator.compare(
        request,
        EnvironmentInputs(RiverReport(()), WeatherReport(())),
        settings,
    )


def _demo_baseline_templates(settings: PlanningSettings) -> DemoOverrides:
    """Build deterministic controls from the original synthetic baseline."""
    request = fixture_request()
    baseline_plan = next(
        plan
        for plan in _probe_plans(request, settings, demo=True)
        if plan.ingredient_mode == TransportMode.SHIP
        and plan.outbound_mode == TransportMode.BICYCLE
        and plan.return_mode == TransportMode.BICYCLE
        and plan.collection_shift == timedelta(0)
    )
    ingredient_event = _event(baseline_plan, "ingredients")
    outbound_event = _event(baseline_plan, "sample")
    return_event = _event(baseline_plan, "return")
    assert ingredient_event and outbound_event and return_event
    return DemoOverrides(
        ingredients=IngredientRouteOverride(480.0, ingredient_event.interval, EVIDENCE),
        sample=LocalRouteOverride(
            CourierLeg.OUTBOUND,
            outbound_event.interval,
            20.0,
            False,
            RouteSnow.CLEAR,
            Availability.AVAILABLE,
            EVIDENCE,
        ),
        treatment=LocalRouteOverride(
            CourierLeg.RETURN,
            return_event.interval,
            20.0,
            False,
            RouteSnow.CLEAR,
            Availability.AVAILABLE,
            EVIDENCE,
        ),
    )


def _request_with_demo_routes(
    request: TreatmentRequest,
    overrides: DemoOverrides,
) -> TreatmentRequest:
    by_leg = {
        CourierLeg.OUTBOUND: overrides.sample,
        CourierLeg.RETURN: overrides.treatment,
    }
    routes = tuple(
        demo_route_input(by_leg[route.leg]) if by_leg[route.leg] else route
        for route in request.routes
    )
    return replace(request, routes=routes)


def _demo_environment(
    request: TreatmentRequest,
    settings: PlanningSettings,
    overrides: DemoOverrides,
    baseline: DemoOverrides,
) -> tuple[EnvironmentInputs, PlanningSettings, tuple[CandidatePlan, ...]]:
    """Apply typed Demo controls to the planner and per-leg weather evidence."""
    settings_for_run = settings
    river_issues = ("Demo mode: Rhine evidence and any delay are simulated.",)
    if overrides.ingredients is not None:
        applied = apply_demo_rhine_delay(settings, overrides.ingredients)
        if applied is not None:
            settings_for_run = applied
        else:
            river_issues += ("Demo Rhine gauge is unknown; the shipping delay is unknown.",)
    river = RiverReport((), river_issues)
    comparator = PlanningComparator("Invented Basel route", t4_replay=True)
    probe = comparator.compare(
        request, EnvironmentInputs(river, WeatherReport(())), settings_for_run
    )
    windows, issues = [], []
    for leg, (event_id, _, _) in LOCAL_ROUTE_EVENTS.items():
        envelope = _journey_envelope(probe, event_id)
        if envelope is None:
            continue
        override = (overrides.sample if leg == CourierLeg.OUTBOUND else overrides.treatment) or (
            baseline.sample if leg == CourierLeg.OUTBOUND else baseline.treatment
        )
        if override is None:
            issues.append(f"Missing simulated conditions for {leg.value}.")
            continue
        report = DemoWeatherProvider(override).load(leg.value, envelope)
        windows.extend(report.windows)
        issues.extend(report.issues)
    environment = EnvironmentInputs(river, WeatherReport(tuple(windows), tuple(issues)))
    plans = comparator.compare(request, environment, settings_for_run)
    if overrides.ingredients is not None and overrides.ingredients.gauge_height_cm is None:
        reason = "Demo Rhine gauge is unknown; the shipping delay cannot be checked."
        plans = tuple(
            replace(
                plan,
                status=ResultStatus.UNCONFIRMED,
                checks=tuple(
                    replace(check, status=CheckStatus.UNKNOWN, reason=reason)
                    if check.constraint == "Rhine evidence"
                    else check
                    for check in plan.checks
                ),
            )
            if plan.ingredient_mode == TransportMode.SHIP and plan.status != ResultStatus.INFEASIBLE
            else plan
            for plan in plans
        )
    return environment, settings_for_run, plans


def _live_environment(
    request: TreatmentRequest,
    settings: PlanningSettings,
    now: datetime,
    weather_providers: dict[str, WeatherLiveProvider],
    rhine_loader,
) -> tuple[EnvironmentInputs, PlanningSettings, tuple[CandidatePlan, ...], RhineRouteEvidence]:
    """Load only live sources; keep missing and unsupported evidence explicit."""
    comparator = PlanningComparator(
        "Invented Basel route",
        t4_replay=False,
        check_temperature=False,
        require_dispatch_route_check=False,
    )
    settings = replace(settings, car_preparation=timedelta(hours=1))
    probe = _probe_plans(request, settings, demo=False)
    ingredient_end = request.order_time + settings.river_order_to_arrival + settings.river_delay
    ingredient_window = TimeWindow(
        request.nominal_departure,
        max(ingredient_end, request.nominal_departure + timedelta(minutes=1)),
    )
    rhine = rhine_loader(ingredient_window, now)
    readings = [
        observation
        for observation in rhine.history.observations
        if observation.observed_at <= now
        and observation.water_level_m is not None
        and now - observation.observed_at <= OBSERVATION_MAX_AGE
    ]
    latest = max(readings, key=lambda observation: observation.observed_at, default=None)
    if latest is None:
        river = RiverReport((), ("A current Basel water-level observation is unavailable.",))
        settings_for_run = settings
    else:
        delay = demo_rhine_delay(
            IngredientRouteOverride(
                latest.water_level_m * 100,
                ingredient_window,
                latest.provenance,
            )
        )
        settings_for_run = replace(settings, river_delay=delay or timedelta(0))
        river = RiverReport((latest,), ())

    windows, issues = [], []
    current_window = TimeWindow(now, now + timedelta(hours=1))
    for postcode, provider in weather_providers.items():
        report = provider.load(LIVE_WEATHER_POINTS[postcode], current_window)
        windows.extend(report.windows)
        issues.extend(f"{LIVE_WEATHER_POINTS[postcode]}: {issue}" for issue in report.issues)
    for leg, (event_id, _, _) in LOCAL_ROUTE_EVENTS.items():
        envelope = _journey_envelope(probe, event_id)
        if envelope is None:
            continue
        for postcode, provider in weather_providers.items():
            report = provider.load(leg.value, envelope)
            windows.extend(report.windows)
            issues.extend(f"{LIVE_WEATHER_POINTS[postcode]}: {issue}" for issue in report.issues)
    environment = EnvironmentInputs(
        river,
        WeatherReport(tuple(windows), tuple(dict.fromkeys(issues))),
    )
    plans = comparator.compare(request, environment, settings_for_run)
    return environment, settings_for_run, plans, rhine


def _baseline_plan(
    plans: tuple[CandidatePlan, ...],
) -> CandidatePlan | None:
    return next(
        (
            plan
            for plan in plans
            if plan.ingredient_mode == TransportMode.SHIP
            and plan.outbound_mode == TransportMode.BICYCLE
            and plan.return_mode == TransportMode.BICYCLE
            and plan.collection_shift == timedelta(0)
        ),
        None,
    )


def _target_for(request: TreatmentRequest) -> datetime:
    return request.order_time + DEFAULT_INJECTION_OFFSET
