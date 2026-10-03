"""T5 scheduling and evidence checks, independent of providers and the screen.

compare() generates critical-time alternatives, not ranked recommendations.
evaluate() also accepts an explicit collection shift for boundary checks.
The default requires actual evidence; t4_replay explicitly enables the agreed
synthetic delay and renewed-dispatch route assumptions for fixture walkthroughs.
"""

from __future__ import annotations

import json
from dataclasses import fields
from datetime import timedelta
from itertools import product
from math import isfinite
from pathlib import Path

from treatment_planner.interfaces import (
    Availability,
    CandidatePlan,
    CheckStatus,
    ConstraintResult,
    CourierLeg,
    EnvironmentInputs,
    EvidenceKind,
    PlanningSettings,
    Provenance,
    ResultStatus,
    RouteSnow,
    TimelineEvent,
    TimeWindow,
    TransportMode,
    TreatmentRequest,
)

ZERO = timedelta()
FIXTURE_KINDS = (EvidenceKind.SYNTHETIC, EvidenceKind.REPLAY)


def load_settings(path: str | Path) -> PlanningSettings:
    """Load hour-valued domain configuration without depending on the cwd."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    settings = PlanningSettings(
        **{name: timedelta(hours=value) for name, value in data["hours"].items()},
        bicycle_temperature_limit_c=data["bicycle_temperature_limit_c"],
    )
    _validate_settings(settings)
    return settings


def _validate_settings(settings):
    for field in fields(settings):
        value = getattr(settings, field.name)
        if isinstance(value, timedelta):
            allow_zero = field.name in {
                "river_delay",
                "collection_shift_limit",
                "route_status_freshness",
            }
            if value < ZERO or (value == ZERO and not allow_zero):
                raise ValueError(f"Invalid duration: {field.name}")
    if not isfinite(settings.bicycle_temperature_limit_c):
        raise ValueError("Temperature limit must be finite.")


def _check(name, status, reason):
    return ConstraintResult(name, status, reason)


def _deadline(name, actual, deadline):
    margin = deadline - actual
    return ConstraintResult(
        name,
        CheckStatus.PASS if margin >= ZERO else CheckStatus.FAIL,
        "Deadline minus actual time; zero passes.",
        margin,
        deadline,
        actual,
    )


def _weather_check(report, location, journey, limit, *, check_temperature=True):
    windows = [
        w
        for w in report.windows
        if w.location == location
        and w.interval.start < journey.end
        and w.interval.end > journey.start
    ]
    if any(
        w.snowfall is True
        or (
            check_temperature
            and (
                w.maximum_temperature_c is not None
                and isfinite(w.maximum_temperature_c)
                and w.maximum_temperature_c > limit
            )
        )
        for w in windows
    ):
        return _check(
            "Weather",
            CheckStatus.FAIL,
            "Journey overlaps snowfall or temperature above the bicycle limit.",
        )
    covered_until = journey.start
    unknown_values = False
    for window in sorted(windows, key=lambda w: w.interval.start):
        if window.snowfall is None or (
            check_temperature
            and (window.maximum_temperature_c is None or not isfinite(window.maximum_temperature_c))
        ):
            unknown_values = True
            continue
        if window.interval.start <= covered_until:
            covered_until = max(covered_until, window.interval.end)
    issues = tuple(
        issue for issue in report.issues if check_temperature or "temperature" not in issue.lower()
    )
    if issues or unknown_values or covered_until < journey.end:
        return _check(
            "Weather",
            CheckStatus.UNKNOWN,
            "Incomplete, unavailable or stale journey evidence. " + "; ".join(issues),
        )
    return _check(
        "Weather", CheckStatus.PASS, "Entire journey covered; no configured weather block."
    )


class PlanningComparator:
    """Shared PlanComparator implementation; t4_replay is only for labelled fixtures.

    weather_location must match the adapter's location label. Separate reports
    for each leg can use that leg's CourierLeg.value as their location instead.
    No provider freshness threshold is invented here: adapter issues propagate.
    """

    def __init__(
        self,
        weather_location: str = "Invented Basel route",
        *,
        t4_replay: bool = False,
        check_temperature: bool = True,
        require_dispatch_route_check: bool = True,
    ):
        self.weather_location = weather_location
        self.t4_replay = t4_replay
        self.check_temperature = check_temperature
        self.require_dispatch_route_check = require_dispatch_route_check

    def compare(
        self,
        request: TreatmentRequest,
        environment: EnvironmentInputs,
        settings: PlanningSettings,
    ) -> tuple[CandidatePlan, ...]:
        """Enumerate shipment, per-leg modes and critical legal collection times."""
        _validate_settings(settings)
        modes = (TransportMode.BICYCLE, TransportMode.CAR)
        shipments = [TransportMode.SHIP]
        if request.decision_time < request.nominal_departure:
            shipments.append(TransportMode.TRUCK)
        plans = []
        for shipment, outbound, returning in product(shipments, modes, modes):
            arrival = self._ingredient_arrival(request, settings, shipment)
            travel = (
                settings.car_travel if outbound == TransportMode.CAR else settings.bicycle_travel
            )
            # Critical shifts cover original, ingredient alignment, first deadline
            # recovery and the legal maximum; no arbitrary hourly search grid.
            shifts = {ZERO, settings.collection_shift_limit}
            for shift in (
                settings.river_delay,
                request.decision_time
                + (settings.car_preparation if outbound == TransportMode.CAR else ZERO)
                - request.original_collection,
                arrival - request.original_collection,
                arrival
                + settings.production_processing
                - settings.production_limit
                - request.original_collection
                - travel,
            ):
                if ZERO <= shift <= settings.collection_shift_limit:
                    shifts.add(shift)
            for shift in sorted(shifts):
                plans.append(
                    self.evaluate(
                        request, environment, settings, shipment, outbound, returning, shift
                    )
                )
        return tuple(plans)

    @staticmethod
    def _ingredient_arrival(request, settings, mode):
        if mode == TransportMode.SHIP:
            return request.order_time + settings.river_order_to_arrival + settings.river_delay
        return (
            max(request.nominal_departure, request.decision_time + settings.truck_preparation)
            + settings.truck_travel
        )

    def _eligibility(self, request, environment, settings, leg, mode, journey):
        route = next(r for r in request.routes if r.leg == leg)
        prefix = leg.name.title()
        if mode == TransportMode.CAR:
            status = {
                Availability.AVAILABLE: CheckStatus.PASS,
                Availability.UNAVAILABLE: CheckStatus.FAIL,
                Availability.UNKNOWN: CheckStatus.UNKNOWN,
            }[route.car_availability]
            return [_check(f"{prefix} car availability", status, route.car_availability.value)]
        location = (
            leg.value
            if any(w.location == leg.value for w in environment.weather.windows)
            else self.weather_location
        )
        weather = _weather_check(
            environment.weather,
            location,
            journey,
            settings.bicycle_temperature_limit_c,
            check_temperature=self.check_temperature,
        )
        weather = ConstraintResult(f"{prefix} weather", weather.status, weather.reason)
        age = (request.decision_time - route.checked_at) if route.checked_at else None
        current = age is not None and ZERO <= age <= settings.route_status_freshness
        renewed = self.t4_replay and route.provenance.kind in FIXTURE_KINDS
        if not current or route.snow == RouteSnow.UNKNOWN:
            status, reason = (
                CheckStatus.UNKNOWN,
                "Missing, stale or future-dated manual route check.",
            )
        elif route.snow == RouteSnow.PRESENT:
            status, reason = CheckStatus.FAIL, "Existing route snow blocks the bicycle."
        elif (
            self.require_dispatch_route_check
            and journey.start > request.decision_time
            and not renewed
        ):
            status, reason = CheckStatus.UNKNOWN, "Future dispatch needs a renewed route check."
        else:
            status, reason = (
                CheckStatus.PASS,
                "Current clear route; replay renewal if dispatch is future.",
            )
        return [weather, _check(f"{prefix} route snow", status, reason)]

    def _ingredients(
        self, request, environment, settings, ingredient_mode, ingredient_arrival, event, checks
    ):
        if ingredient_mode == TransportMode.TRUCK:
            prep_end = request.decision_time + settings.truck_preparation
            checks.append(
                _check(
                    "Shipment switch",
                    CheckStatus.PASS
                    if request.decision_time < request.nominal_departure
                    and prep_end <= request.nominal_departure
                    else CheckStatus.FAIL,
                    "Switch requires future departure and completed truck preparation.",
                )
            )
            event(
                "truck-prep",
                "Ingredients",
                "Truck approval / preparation",
                request.decision_time,
                prep_end,
            )
            departure = max(request.nominal_departure, prep_end)
        else:
            departure = request.nominal_departure
            replay = self.t4_replay
            river = environment.river
            usable = bool(river.observations) and not river.issues
            usable = usable and all(
                observation.observed_at <= request.decision_time
                and any(
                    value is not None and isfinite(value)
                    for value in (observation.water_level_m, observation.discharge_m3_s)
                )
                for observation in river.observations
            )
            checks.append(
                _check(
                    "Rhine evidence",
                    CheckStatus.PASS if replay or usable else CheckStatus.UNKNOWN,
                    (
                        "Labelled T4 replay."
                        if replay
                        else "Fresh Basel gauge observation; route delay follows the configured "
                        "simplified model. It is not a provider ETA."
                    )
                    + (" " + "; ".join(river.issues) if river.issues else ""),
                )
            )
        checks.append(
            _check(
                "Ingredient journey timing",
                CheckStatus.PASS
                if departure >= request.order_time and ingredient_arrival > departure
                else CheckStatus.FAIL,
                "Arrival must follow departure and order.",
            )
        )
        event("ingredients", "Ingredients", ingredient_mode.value, departure, ingredient_arrival)
        checks.append(
            _deadline(
                "Ingredient arrival",
                ingredient_arrival,
                request.order_time + settings.ingredient_limit,
            )
        )

    def _outbound(self, request, environment, settings, outbound_mode, collection, event, checks):
        dispatch = collection
        if outbound_mode == TransportMode.CAR:
            prep_start = max(request.decision_time, collection - settings.car_preparation)
            prep_end = prep_start + settings.car_preparation
            event("outbound-prep", "Outbound car", "Outbound car preparation", prep_start, prep_end)
            checks.append(_deadline("Outbound preparation", prep_end, collection))
            dispatch = max(collection, prep_end)
        sample_arrival = dispatch + (
            settings.car_travel if outbound_mode == TransportMode.CAR else settings.bicycle_travel
        )
        event("sample-waiting", "Sample", "Waiting for outbound car", collection, dispatch)
        event("sample", "Sample", f"Outbound {outbound_mode.value}", dispatch, sample_arrival)
        checks.extend(
            self._eligibility(
                request,
                environment,
                settings,
                CourierLeg.OUTBOUND,
                outbound_mode,
                TimeWindow(dispatch, sample_arrival),
            )
        )
        checks.append(
            _deadline("Sample arrival", sample_arrival, collection + settings.sample_limit)
        )
        return sample_arrival

    def _return(
        self,
        request,
        environment,
        settings,
        return_mode,
        completion,
        prepare_return_at_completion,
        event,
        checks,
    ):
        return_dispatch = completion
        if return_mode == TransportMode.CAR:
            target = (
                completion
                if prepare_return_at_completion
                else completion - settings.car_preparation
            )
            prep_start = max(request.decision_time, target)
            prep_end = prep_start + settings.car_preparation
            event("return-prep", "Return car", "Return car preparation", prep_start, prep_end)
            checks.append(_deadline("Return preparation", prep_end, completion))
            return_dispatch = max(completion, prep_end)
            event(
                "return-waiting", "Hospital", "Waiting for return car", completion, return_dispatch
            )
        delivery = return_dispatch + (
            settings.car_travel if return_mode == TransportMode.CAR else settings.bicycle_travel
        )
        event("return", "Hospital", f"Return {return_mode.value}", return_dispatch, delivery)
        checks.extend(
            self._eligibility(
                request,
                environment,
                settings,
                CourierLeg.RETURN,
                return_mode,
                TimeWindow(return_dispatch, delivery),
            )
        )
        injection = delivery + settings.hospital_handling
        event("handling", "Hospital", "Hospital handling", delivery, injection)
        checks.append(_deadline("Injection", injection, completion + settings.injection_limit))

    def _candidate(
        self,
        ingredient_mode,
        outbound_mode,
        return_mode,
        collection_shift,
        prepare_return_at_completion,
        events,
        checks,
    ):
        status = (
            ResultStatus.INFEASIBLE
            if any(c.status == CheckStatus.FAIL for c in checks)
            else ResultStatus.UNCONFIRMED
            if any(c.status == CheckStatus.UNKNOWN for c in checks)
            else ResultStatus.CONFIRMED
        )
        assumptions = [
            "Configured synthetic durations from docs/scenarios.md; "
            "no booking or clinical decision.",
            "Rhine delay is a supplied scenario value, not whole-route navigability evidence.",
        ]
        if self.t4_replay:
            assumptions.append(
                "T4 replay: synthetic Rhine delay supported; "
                "synthetic clear routes renewed at dispatch."
            )
        identity = (
            f"{ingredient_mode.name}-{outbound_mode.name}-{return_mode.name}-"
            f"{collection_shift.total_seconds():g}"
        )
        if prepare_return_at_completion:
            identity += "-late-return-prep"
        return CandidatePlan(
            identity,
            f"{ingredient_mode.value}; {outbound_mode.value} / {return_mode.value}; "
            f"collection +{collection_shift.total_seconds() / 3600:g}h",
            status,
            ingredient_mode,
            outbound_mode,
            return_mode,
            collection_shift,
            tuple(sorted(events, key=lambda e: (e.interval.start, e.event_id))),
            tuple(checks),
            tuple(assumptions),
        )

    def evaluate(
        self,
        request: TreatmentRequest,
        environment: EnvironmentInputs,
        settings: PlanningSettings,
        ingredient_mode: TransportMode,
        outbound_mode: TransportMode,
        return_mode: TransportMode,
        collection_shift: timedelta = ZERO,
        *,
        prepare_return_at_completion: bool = False,
    ) -> CandidatePlan:
        """Evaluate one alternative; late-return-preparation exposes the T4 counterexample."""
        _validate_settings(settings)
        if ingredient_mode not in (TransportMode.SHIP, TransportMode.TRUCK):
            raise ValueError("Ingredients require ship or truck.")
        if any(
            mode not in (TransportMode.BICYCLE, TransportMode.CAR)
            for mode in (outbound_mode, return_mode)
        ):
            raise ValueError("Couriers require bicycle or car.")
        collection = request.original_collection + collection_shift
        ingredient_arrival = self._ingredient_arrival(request, settings, ingredient_mode)
        evidence = Provenance(
            "T4 configured synthetic schedule",
            EvidenceKind.SYNTHETIC,
            request.decision_time,
            request.decision_time,
        )
        events, checks = [], []

        def event(name, lane, label, start, end):
            if end > start:
                events.append(TimelineEvent(name, lane, label, TimeWindow(start, end), evidence))

        checks.append(
            _deadline(
                "Collection shift",
                collection,
                request.original_collection + settings.collection_shift_limit,
            )
        )
        checks.append(
            _check(
                "Collection timing",
                CheckStatus.PASS
                if collection_shift >= ZERO and collection >= request.decision_time
                else CheckStatus.FAIL,
                "Collection cannot advance or precede the planning decision.",
            )
        )
        self._ingredients(
            request, environment, settings, ingredient_mode, ingredient_arrival, event, checks
        )
        sample_arrival = self._outbound(
            request, environment, settings, outbound_mode, collection, event, checks
        )
        processing_start = max(ingredient_arrival, sample_arrival)
        completion = processing_start + settings.production_processing
        event("waiting", "Sample", "Waiting for ingredients", sample_arrival, processing_start)
        event("processing", "Production", "Processing", processing_start, completion)
        checks.append(
            _deadline(
                "Production completion", completion, sample_arrival + settings.production_limit
            )
        )
        self._return(
            request,
            environment,
            settings,
            return_mode,
            completion,
            prepare_return_at_completion,
            event,
            checks,
        )
        return self._candidate(
            ingredient_mode,
            outbound_mode,
            return_mode,
            collection_shift,
            prepare_return_at_completion,
            events,
            checks,
        )
