"""Fixed, labelled T4 examples; no production engine or live adapters here.

Every comparison is an authored fixture from docs/scenarios.md. The comparator
rejects changed inputs instead of pretending to recompute their feasibility.
T5 replaces it with a real engine; T6/T7 replace the synthetic providers.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from treatment_planner.interfaces import (
    Availability,
    CandidatePlan,
    CheckStatus,
    ConstraintResult,
    CourierLeg,
    EnvironmentInputs,
    EvidenceKind,
    LocalRouteInput,
    PlanningSettings,
    Provenance,
    ResultStatus,
    RiverReport,
    RouteSnow,
    TimelineEvent,
    TimeWindow,
    TransportMode,
    TreatmentRequest,
    WeatherReport,
    WeatherWindow,
)

ORDER = datetime(2026, 11, 1, 8, tzinfo=UTC)
EVIDENCE = Provenance("T4 authored synthetic fixture", EvidenceKind.SYNTHETIC, ORDER, ORDER)
ASSUMPTIONS = (
    "Authored T4 example: fixed outcomes, not engine-generated recommendations.",
    "Invented treatment, locations and journey/process durations; all times UTC.",
    "Synthetic weather covers both journeys; route checks are renewed at dispatch.",
    "Cars are explicitly available; no booking or clinical decision is performed.",
    "Low-water delay is a scenario input, not a conversion from a river measurement.",
)


def _time(hours: float) -> datetime:
    return ORDER + timedelta(hours=hours)


def _event(event_id: str, lane: str, label: str, start: float, end: float) -> TimelineEvent:
    return TimelineEvent(event_id, lane, label, TimeWindow(_time(start), _time(end)), EVIDENCE)


def fixture_settings() -> PlanningSettings:
    """Accepted synthetic conventions from T4, not operational configuration."""
    return PlanningSettings(
        ingredient_limit=timedelta(hours=240),
        collection_shift_limit=timedelta(hours=24),
        sample_limit=timedelta(hours=12),
        production_limit=timedelta(hours=24),
        injection_limit=timedelta(hours=8),
        river_order_to_arrival=timedelta(hours=144),
        river_delay=timedelta(hours=12),
        truck_travel=timedelta(hours=48),
        truck_preparation=timedelta(hours=6),
        bicycle_travel=timedelta(hours=1),
        car_travel=timedelta(hours=1),
        car_preparation=timedelta(hours=8),
        production_processing=timedelta(hours=18),
        hospital_handling=timedelta(hours=1),
        route_status_freshness=timedelta(hours=6),
        bicycle_temperature_limit_c=30,
    )


def fixture_request() -> TreatmentRequest:
    return TreatmentRequest(
        "SYNTHETIC-TREATMENT-01",
        ORDER,
        _time(144),
        _time(6),
        ORDER,
        tuple(
            LocalRouteInput(leg, RouteSnow.CLEAR, ORDER, Availability.AVAILABLE, EVIDENCE)
            for leg in CourierLeg
        ),
    )


@dataclass(frozen=True)
class SyntheticRiverProvider:
    """No fabricated gauge reading: the demo only has a synthetic delay input."""

    def load(self, window: TimeWindow) -> RiverReport:
        return RiverReport((), ("No measured Rhine data in T1; delay is an authored scenario.",))


@dataclass(frozen=True)
class SyntheticWeatherProvider:
    hot_return: bool = False

    def load(self, location: str, window: TimeWindow) -> WeatherReport:
        coverage = TimeWindow(ORDER, _time(200))
        if window.start < coverage.start or window.end > coverage.end:
            return WeatherReport((), ("Requested interval exceeds synthetic fixture coverage.",))
        windows = (
            WeatherWindow(location, TimeWindow(ORDER, _time(163)), 20, False, EVIDENCE),
            WeatherWindow(
                location,
                TimeWindow(_time(163), _time(164)),
                30.1 if self.hot_return else 20,
                False,
                EVIDENCE,
            ),
            WeatherWindow(location, TimeWindow(_time(164), _time(200)), 20, False, EVIDENCE),
        )
        return WeatherReport(windows)


def _checks(production_margin: float, ingredient_margin: float, hot: bool = False):
    checks = tuple(
        ConstraintResult(
            name,
            CheckStatus.FAIL if margin < 0 else CheckStatus.PASS,
            "Fixed T4 expected deadline margin; waiting and handling are included.",
            timedelta(hours=margin),
        )
        for name, margin in (
            ("Ingredient arrival", ingredient_margin),
            ("Sample arrival", 11),
            ("Production completion", production_margin),
            ("Injection", 6),
        )
    )
    return checks + (
        ConstraintResult(
            "Courier eligibility",
            CheckStatus.FAIL if hot else CheckStatus.PASS,
            "Return bicycle blocked by 30.1°C fixture forecast."
            if hot
            else "Synthetic full-journey weather and renewed route evidence; cars available.",
        ),
    )


def _plan(
    plan_id: str,
    title: str,
    collection: float = 144,
    ingredient_arrival: float = 144,
    truck: bool = False,
    return_car: bool = False,
    hot_bicycle: bool = False,
) -> CandidatePlan:
    """Assemble fixed timeline events; no search or domain-rule evaluation."""
    sample_arrival = collection + 1
    processing_start = max(sample_arrival, ingredient_arrival)
    completion = processing_start + 18
    events = [
        _event("ingredients", "Ingredients", "Ingredient travel", 6, ingredient_arrival),
        _event("sample", "Sample", "Outbound bicycle", collection, sample_arrival),
        _event("processing", "Production", "Processing", processing_start, completion),
        _event(
            "return",
            "Hospital",
            "Return car" if return_car else "Return bicycle",
            completion,
            completion + 1,
        ),
        _event("handling", "Hospital", "Hospital handling", completion + 1, completion + 2),
    ]
    if truck:
        events.append(_event("truck-prep", "Ingredients", "Truck approval / preparation", 0, 6))
    if processing_start > sample_arrival:
        events.append(_event("waiting", "Sample", "Waiting", sample_arrival, processing_start))
    if return_car:
        events.append(
            _event(
                "return-prep", "Return car", "Return car preparation", completion - 8, completion
            )
        )
    checks = _checks(24 - (completion - sample_arrival), 240 - ingredient_arrival, hot_bicycle)
    return CandidatePlan(
        plan_id,
        title,
        ResultStatus.INFEASIBLE
        if any(check.status == CheckStatus.FAIL for check in checks)
        else ResultStatus.CONFIRMED,
        TransportMode.TRUCK if truck else TransportMode.SHIP,
        TransportMode.BICYCLE,
        TransportMode.CAR if return_car else TransportMode.BICYCLE,
        timedelta(hours=collection - 144),
        tuple(events),
        checks,
        ASSUMPTIONS,
    )


@dataclass(frozen=True)
class FixtureComparator:
    """Contract-compatible authored output, deliberately not the T5 engine."""

    scenario: str

    def compare(
        self,
        request: TreatmentRequest,
        environment: EnvironmentInputs,
        settings: PlanningSettings,
    ) -> tuple[CandidatePlan, ...]:
        expected = fixture_environment(self.scenario)
        if (
            request != fixture_request()
            or settings != fixture_settings()
            or environment != expected
        ):
            raise ValueError(
                "T1 fixtures are fixed; changed inputs require the T5 planning engine."
            )
        if self.scenario == "Baseline":
            return (_plan("baseline", "Rhine + bicycles"),)
        if self.scenario == "Low water":
            return (
                _plan("keep", "Keep Rhine and collection", ingredient_arrival=156),
                _plan("postpone", "Rhine + collection 12h later", 156, 156),
                _plan("truck", "Truck + original collection", ingredient_arrival=54, truck=True),
            )
        if self.scenario == "Hot return":
            return (
                _plan("hot-bike", "Keep return bicycle", hot_bicycle=True),
                _plan("return-car", "Prepare return car in advance", return_car=True),
            )
        raise ValueError("Unknown authored scenario.")


SCENARIOS = ("Baseline", "Low water", "Hot return")


def fixture_environment(scenario: str) -> EnvironmentInputs:
    window = TimeWindow(ORDER, _time(200))
    return EnvironmentInputs(
        SyntheticRiverProvider().load(window),
        SyntheticWeatherProvider(scenario == "Hot return").load("Invented Basel route", window),
    )
