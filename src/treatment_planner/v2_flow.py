"""Compose V2 evidence, planner output and route verdicts for the screen."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from treatment_planner.data.weather import WeatherLiveProvider
from treatment_planner.demo import EVIDENCE, ORDER, fixture_request
from treatment_planner.interfaces import (
    Availability,
    CandidatePlan,
    CheckStatus,
    ConstraintResult,
    CourierLeg,
    DemoOverrides,
    EnvironmentInputs,
    EvidenceKind,
    EvidenceMode,
    IngredientRouteOverride,
    LocalRouteInput,
    LocalRouteOverride,
    PlanningSettings,
    Provenance,
    ResultStatus,
    RiverReport,
    RouteId,
    RouteSnow,
    RouteStatus,
    RouteSummary,
    TimeWindow,
    TransportMode,
    TreatmentRequest,
    WeatherReport,
)
from treatment_planner.planning import PlanningComparator
from treatment_planner.rhine_demo import (
    apply_demo_rhine_delay,
    demo_rhine_delay,
    load_live_rhine_evidence,
)
from treatment_planner.weather_demo import DemoWeatherProvider, demo_carry_over, demo_route_input

LOCATION = "Basel 4056 forecast point"
FORECAST_AGE = timedelta(hours=24)  # Inspection value; no approved operational policy.


@dataclass(frozen=True)
class PlanningFlow:
    """One consistent comparison snapshot, including its evidence."""

    request: TreatmentRequest
    environment: EnvironmentInputs
    plans: tuple[CandidatePlan, ...]
    summaries: tuple[RouteSummary, ...]


def live_request(now: datetime) -> TreatmentRequest:
    """Move synthetic process clocks to now; require new manual route checks."""
    original = fixture_request()
    offset = now - ORDER
    routes = tuple(
        LocalRouteInput(
            leg,
            RouteSnow.UNKNOWN,
            None,
            Availability.UNKNOWN,
            Provenance("Coordinator route status not entered", EvidenceKind.MANUAL, now, now),
        )
        for leg in CourierLeg
    )
    return replace(
        original,
        order_time=now,
        decision_time=now,
        original_collection=original.original_collection + offset,
        nominal_departure=original.nominal_departure + offset,
        routes=routes,
    )


def baseline_overrides(settings: PlanningSettings) -> DemoOverrides:
    """Give each demo button an independent initial journey interval."""
    request = fixture_request()
    probe = PlanningComparator(t4_replay=True).compare(
        request, EnvironmentInputs(RiverReport(()), WeatherReport(())), settings
    )
    baseline = next(
        p
        for p in probe
        if p.ingredient_mode == TransportMode.SHIP
        and p.outbound_mode == p.return_mode == TransportMode.BICYCLE
        and p.collection_shift == timedelta()
    )
    intervals = {event.event_id: event.interval for event in baseline.events}
    return DemoOverrides(
        IngredientRouteOverride(500.0, intervals["ingredients"], EVIDENCE),
        LocalRouteOverride(
            CourierLeg.OUTBOUND,
            intervals["sample"],
            20.0,
            False,
            RouteSnow.CLEAR,
            Availability.AVAILABLE,
            EVIDENCE,
        ),
        LocalRouteOverride(
            CourierLeg.RETURN,
            intervals["return"],
            20.0,
            False,
            RouteSnow.CLEAR,
            Availability.AVAILABLE,
            EVIDENCE,
        ),
    )


def _journey_envelopes(plans: tuple[CandidatePlan, ...]) -> dict[str, TimeWindow]:
    envelopes = {}
    for event_id in ("ingredients", "sample", "return"):
        journeys = [e.interval for p in plans for e in p.events if e.event_id == event_id]
        envelopes[event_id] = TimeWindow(
            min(w.start for w in journeys), max(w.end for w in journeys)
        )
    return envelopes


def _demo_inputs(
    settings: PlanningSettings, overrides: DemoOverrides, baseline: DemoOverrides
) -> tuple[TreatmentRequest, PlanningSettings, EnvironmentInputs]:
    effective = DemoOverrides(
        overrides.ingredients or baseline.ingredients,
        overrides.sample or baseline.sample,
        overrides.treatment or baseline.treatment,
    )
    request = replace(
        fixture_request(),
        routes=(demo_route_input(effective.sample), demo_route_input(effective.treatment)),
    )
    adjusted = apply_demo_rhine_delay(settings, effective.ingredients)
    if adjusted is None:
        # No level cannot prove a zero delay; ship plans remain unconfirmed.
        river = RiverReport(
            (), ("Simulated Rhine gauge height is unknown; delivery delay unknown.",)
        )
        adjusted = settings
    else:
        river = RiverReport(())
    probe = PlanningComparator(t4_replay=True).compare(
        request, EnvironmentInputs(river, WeatherReport(())), adjusted
    )
    envelopes = _journey_envelopes(probe)
    reports = (
        DemoWeatherProvider(effective.sample).load(CourierLeg.OUTBOUND.value, envelopes["sample"]),
        DemoWeatherProvider(effective.treatment).load(CourierLeg.RETURN.value, envelopes["return"]),
    )
    weather = WeatherReport(tuple(w for report in reports for w in report.windows))
    return request, adjusted, EnvironmentInputs(river, weather)


def _live_inputs(
    request: TreatmentRequest, settings: PlanningSettings, weather: WeatherLiveProvider
) -> EnvironmentInputs:
    probe = PlanningComparator(weather_location=LOCATION).compare(
        request, EnvironmentInputs(RiverReport(()), WeatherReport(())), settings
    )
    envelopes = _journey_envelopes(probe)
    rhine = load_live_rhine_evidence(envelopes["ingredients"], evaluated_at=request.decision_time)
    reports = (
        weather.load(CourierLeg.OUTBOUND.value, envelopes["sample"]),
        weather.load(CourierLeg.RETURN.value, envelopes["return"]),
    )
    return EnvironmentInputs(
        RiverReport(rhine.history.observations, rhine.issues),
        WeatherReport(
            tuple(w for report in reports for w in report.windows),
            tuple(dict.fromkeys(issue for report in reports for issue in report.issues)),
        ),
    )


def _route_summary(
    plan: CandidatePlan,
    request: TreatmentRequest,
    route: RouteId,
    mode: EvidenceMode,
    overrides: DemoOverrides,
    baseline: DemoOverrides,
    environment: EnvironmentInputs,
) -> RouteSummary:
    event_id, transport, checks = {
        RouteId.INGREDIENTS: (
            "ingredients",
            plan.ingredient_mode,
            ("Rhine evidence", "Rhine delay", "Ingredient arrival"),
        ),
        RouteId.SAMPLE: (
            "sample",
            plan.outbound_mode,
            ("Outbound weather", "Outbound route snow", "Outbound car availability"),
        ),
        RouteId.TREATMENT: (
            "return",
            plan.return_mode,
            ("Return weather", "Return route snow", "Return car availability"),
        ),
    }[route]
    interval = next(e.interval for e in plan.events if e.event_id == event_id)
    relevant = tuple(c for c in plan.checks if c.constraint in checks)
    if any(c.status == CheckStatus.FAIL for c in relevant):
        status = RouteStatus.BLOCKED
    elif any(c.status == CheckStatus.UNKNOWN for c in relevant):
        status = RouteStatus.UNKNOWN
    elif (
        route == RouteId.INGREDIENTS
        and mode == EvidenceMode.DEMO
        and plan.ingredient_mode == TransportMode.SHIP
        and (demo_rhine_delay(overrides.ingredients or baseline.ingredients) or timedelta())
        > timedelta()
    ):
        status = RouteStatus.AT_RISK
    else:
        status = RouteStatus.NORMAL
    reason = "; ".join(c.reason for c in relevant if c.status != CheckStatus.PASS)
    if not reason:
        if status == RouteStatus.AT_RISK:
            reason = "Simulated low-water delivery delay; station level is not route navigability"
        else:
            reason = (
                "Synthetic route condition applied"
                if mode == EvidenceMode.DEMO
                else "Available checks pass"
            )
    if route == RouteId.INGREDIENTS:
        source = overrides.ingredients or baseline.ingredients
        evidence = (
            (source.provenance,)
            if mode == EvidenceMode.DEMO
            else tuple(o.provenance for o in environment.river.observations)
        )
        carried = (
            source.interval if mode == EvidenceMode.DEMO and source.interval != interval else None
        )
    else:
        leg = CourierLeg.OUTBOUND if route == RouteId.SAMPLE else CourierLeg.RETURN
        source = (
            (overrides.sample or baseline.sample)
            if route == RouteId.SAMPLE
            else (overrides.treatment or baseline.treatment)
        )
        evidence = (
            (source.provenance,)
            if mode == EvidenceMode.DEMO
            else (
                next(r.provenance for r in request.routes if r.leg == leg),
                *(w.provenance for w in environment.weather.windows if w.location == leg.value),
            )
        )
        carried = demo_carry_over(source, interval) if mode == EvidenceMode.DEMO else None
    delay = None
    if status == RouteStatus.NORMAL:
        delay = timedelta()
    elif status == RouteStatus.AT_RISK and route == RouteId.INGREDIENTS:
        delay = demo_rhine_delay(overrides.ingredients or baseline.ingredients)
    return RouteSummary(
        plan.plan_id,
        route,
        interval,
        transport,
        mode,
        status,
        reason,
        tuple(dict.fromkeys(evidence)),
        delay,
        (),
        carried,
    )


def build_flow(
    mode: EvidenceMode,
    settings: PlanningSettings,
    overrides: DemoOverrides,
    baseline: DemoOverrides,
    *,
    request: TreatmentRequest | None = None,
    weather: WeatherLiveProvider | None = None,
) -> PlanningFlow:
    """Compute every candidate and matching route summary from one snapshot."""
    if mode == EvidenceMode.DEMO:
        request, settings, environment = _demo_inputs(settings, overrides, baseline)
    else:
        if request is None or weather is None:
            raise ValueError("Live mode needs a current request and weather provider.")
        environment = _live_inputs(request, settings, weather)
    plans = PlanningComparator(
        weather_location=LOCATION, t4_replay=mode == EvidenceMode.DEMO
    ).compare(request, environment, settings)
    if (
        mode == EvidenceMode.DEMO
        and demo_rhine_delay(overrides.ingredients or baseline.ingredients) is None
    ):
        plans = tuple(
            replace(
                plan,
                status=ResultStatus.UNCONFIRMED,
                checks=plan.checks
                + (
                    ConstraintResult(
                        "Rhine delay",
                        CheckStatus.UNKNOWN,
                        "Simulated gauge height is unknown; "
                        "ship delivery delay cannot be evaluated.",
                    ),
                ),
            )
            if plan.ingredient_mode == TransportMode.SHIP
            else plan
            for plan in plans
        )
    summaries = tuple(
        _route_summary(plan, request, route, mode, overrides, baseline, environment)
        for plan in plans
        for route in RouteId
    )
    return PlanningFlow(request, environment, plans, summaries)
