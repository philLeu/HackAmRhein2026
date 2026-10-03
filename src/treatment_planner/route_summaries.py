"""Build evidence-backed route summaries for integrated V2 alternatives."""

from datetime import timedelta

from treatment_planner.interfaces import (
    CandidatePlan,
    CheckStatus,
    CourierLeg,
    DemoOverrides,
    EnvironmentInputs,
    EvidenceMode,
    PlanningSettings,
    Provenance,
    RouteId,
    RouteStatus,
    RouteSummary,
    TransportMode,
    TreatmentRequest,
)
from treatment_planner.rhine_demo import RhineRouteEvidence
from treatment_planner.weather_advisories import weather_recheck_warnings
from treatment_planner.weather_demo import demo_carry_over

from .v2_flow import EVIDENCE, LOCAL_ROUTE_EVENTS, _event


def _sources_for_windows(windows) -> tuple[Provenance, ...]:
    return tuple(dict.fromkeys(window.provenance for window in windows))


def build_route_summaries(
    plans: tuple[CandidatePlan, ...],
    request: TreatmentRequest,
    environment: EnvironmentInputs,
    mode: EvidenceMode,
    settings: PlanningSettings,
    *,
    overrides: DemoOverrides = DemoOverrides(),
    baseline: DemoOverrides = DemoOverrides(),
    rhine: RhineRouteEvidence | None = None,
) -> tuple[RouteSummary, ...]:
    """Build one evidence-backed summary for each candidate's three routes."""
    summaries = []
    for plan in plans:
        checks = {check.constraint: check for check in plan.checks}
        ingredient_event = _event(plan, "ingredients")
        if ingredient_event is not None:
            if mode == EvidenceMode.LIVE and plan.ingredient_mode == TransportMode.SHIP:
                latest = max(
                    environment.river.observations,
                    key=lambda value: value.observed_at,
                    default=None,
                )
                evidence = (latest.provenance,) if latest is not None else ()
                delay = (
                    settings.river_delay
                    if latest is not None and not environment.river.issues
                    else None
                )
                issues = environment.river.issues
                if latest is None or issues:
                    status = RouteStatus.UNKNOWN
                    reason = (
                        "A current Basel gauge reading is needed for the simplified ship model."
                    )
                elif delay and delay > timedelta(0):
                    status = RouteStatus.AT_RISK
                    reason = (
                        f"Simplified Basel-gauge model adds {delay.total_seconds() / 3600:g} h "
                        "for the whole ship route; this is not a provider ETA."
                    )
                else:
                    status = RouteStatus.NORMAL
                    reason = (
                        "Simplified Basel-gauge model adds no delay; Basel level is assumed "
                        "to apply along the whole ship route. This is not a provider ETA."
                    )
            elif plan.ingredient_mode == TransportMode.SHIP:
                ingredient_override = overrides.ingredients
                provenance = (
                    ingredient_override.provenance if ingredient_override is not None else EVIDENCE
                )
                evidence = (provenance,)
                if ingredient_override is not None and ingredient_override.gauge_height_cm is None:
                    status = RouteStatus.UNKNOWN
                    reason = "Demo gauge is unknown; shipping delay remains unknown."
                    delay = None
                    issues = (reason,)
                else:
                    delay = settings.river_delay
                    if delay > timedelta(0):
                        status = RouteStatus.AT_RISK
                        reason = (
                            f"Demo-only low-water mapping adds {delay.total_seconds() / 3600:g} h."
                        )
                    else:
                        status = RouteStatus.NORMAL
                        reason = "Synthetic baseline assumes no additional Rhine delay."
                    issues = ()
            else:
                status = RouteStatus.NORMAL if mode == EvidenceMode.DEMO else RouteStatus.UNKNOWN
                reason = (
                    "Refrigerated-truck duration is an invented demo assumption."
                    if mode == EvidenceMode.DEMO
                    else "Truck route: Rotterdam to PulseShift in Basel. No live truck travel-time "
                    "data is available; the configured duration is a model assumption."
                )
                evidence = (EVIDENCE,) if mode == EvidenceMode.DEMO else ()
                delay, issues = None, ()
            summaries.append(
                RouteSummary(
                    plan.plan_id,
                    RouteId.INGREDIENTS,
                    ingredient_event.interval,
                    plan.ingredient_mode,
                    mode,
                    status,
                    reason,
                    evidence,
                    delay,
                    tuple(issues),
                )
            )

        for leg, (event_id, route_id, prefix) in LOCAL_ROUTE_EVENTS.items():
            event = _event(plan, event_id)
            if event is None:
                continue
            route_input = next(route for route in request.routes if route.leg == leg)
            mode_for_route = plan.outbound_mode if leg == CourierLeg.OUTBOUND else plan.return_mode
            location_windows = tuple(
                window
                for window in environment.weather.windows
                if window.location == leg.value
                and window.interval.start < event.interval.end
                and window.interval.end > event.interval.start
            )
            evidence = _sources_for_windows(location_windows) or (route_input.provenance,)
            names = (
                (f"{prefix} car availability",)
                if mode_for_route == TransportMode.CAR
                else (f"{prefix} weather", f"{prefix} route snow")
            )
            relevant = [checks[name] for name in names if name in checks]
            failures = [item for item in relevant if item.status == CheckStatus.FAIL]
            unknown = [item for item in relevant if item.status == CheckStatus.UNKNOWN]
            if failures:
                status = RouteStatus.BLOCKED
                reason = "; ".join(item.reason for item in failures)
            elif unknown:
                status = RouteStatus.UNKNOWN
                reason = "; ".join(item.reason for item in unknown)
            else:
                advisories = weather_recheck_warnings(
                    environment.weather,
                    event.interval,
                    location=leg.value,
                    trip_label="Sample trip" if leg == CourierLeg.OUTBOUND else "Treatment return",
                )
                if advisories:
                    status, reason = RouteStatus.AT_RISK, advisories[0]
                else:
                    status = RouteStatus.NORMAL
                    reason = (
                        "Car availability is recorded as available."
                        if mode_for_route == TransportMode.CAR
                        else "Weather and route-snow checks pass for this journey."
                    )
            carried = None
            if mode == EvidenceMode.DEMO:
                override = (
                    overrides.sample if leg == CourierLeg.OUTBOUND else overrides.treatment
                ) or (baseline.sample if leg == CourierLeg.OUTBOUND else baseline.treatment)
                if override is not None:
                    carried = demo_carry_over(override, event.interval)
            summaries.append(
                RouteSummary(
                    plan.plan_id,
                    route_id,
                    event.interval,
                    mode_for_route,
                    mode,
                    status,
                    reason,
                    evidence,
                    None,
                    tuple(item.reason for item in relevant if item.status != CheckStatus.PASS),
                    carried,
                )
            )
    return tuple(summaries)
