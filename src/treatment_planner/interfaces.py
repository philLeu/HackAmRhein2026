"""Shared data and component contracts for the treatment planner.

Times are timezone-aware; durations use timedelta; temperature is Celsius,
water level is metres and discharge is cubic metres per second. Environmental
coverage is explicit and must not be confused with retrieval/issue time.
An unconfirmed result is distinct from demonstrated infeasibility. All changes
to this file require a decision line in docs/decisions.md in the same commit.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol, runtime_checkable


class ResultStatus(StrEnum):
    CONFIRMED = "confirmed"
    INFEASIBLE = "infeasible"
    UNCONFIRMED = "unconfirmed"


class CheckStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


class EvidenceKind(StrEnum):
    OBSERVATION = "observation"
    FORECAST = "forecast"
    MANUAL = "manual"
    SYNTHETIC = "synthetic"
    REPLAY = "replay"


class CourierLeg(StrEnum):
    OUTBOUND = "hospital to factory"
    RETURN = "factory to hospital"


class RouteSnow(StrEnum):
    CLEAR = "clear"
    PRESENT = "snow present"
    UNKNOWN = "unknown"


class Availability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class TransportMode(StrEnum):
    SHIP = "Rhine ship"
    TRUCK = "refrigerated truck"
    BICYCLE = "bicycle"
    CAR = "car"


def _aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Use a timezone-aware timestamp.")


@dataclass(frozen=True)
class TimeWindow:
    """An interval [start, end); no implicit coverage beyond its end."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        _aware(self.start)
        _aware(self.end)
        if self.end <= self.start:
            raise ValueError("The interval must end after it starts.")


@dataclass(frozen=True)
class Provenance:
    """Where evidence came from; source_time is issue/observation/entry time."""

    source: str
    kind: EvidenceKind
    source_time: datetime
    retrieved_at: datetime

    def __post_init__(self) -> None:
        _aware(self.source_time)
        _aware(self.retrieved_at)


@dataclass(frozen=True)
class RiverObservation:
    """A station reading, not a whole-route navigability or delay estimate."""

    station: str
    observed_at: datetime
    provenance: Provenance
    water_level_m: float | None = None
    discharge_m3_s: float | None = None

    def __post_init__(self) -> None:
        _aware(self.observed_at)


@dataclass(frozen=True)
class WeatherWindow:
    """Journey-check evidence; None means unknown, not zero/no snowfall."""

    location: str
    interval: TimeWindow
    maximum_temperature_c: float | None
    snowfall: bool | None
    provenance: Provenance
    hourly_mean_temperature_c: float | None = None


@dataclass(frozen=True)
class RiverReport:
    observations: tuple[RiverObservation, ...]
    issues: tuple[str, ...] = ()


class RiverStatus(StrEnum):
    NORMAL = "normal"
    WATCH = "watch"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RiverFinding:
    """One crossed threshold or proximity finding under the notebook rules."""

    state: str
    severity: RiverStatus
    quantity: str
    limit_cm: float
    distance_cm: float
    consequence: str
    message: str


@dataclass(frozen=True)
class RiverAssessment:
    """Notebook station classification, never a whole-route safety verdict."""

    status: RiverStatus
    gauge_height_cm: float | None
    draft_cm: float | None
    findings: tuple[RiverFinding, ...] = ()


@dataclass(frozen=True)
class RiverForecastPoint:
    """An hourly gauge-height forecast in cm above the station datum.

    Optional ensemble bounds are not probabilities of a navigation class.
    """

    timestamp: datetime
    median_cm: float
    minimum_cm: float | None = None
    p25_cm: float | None = None
    p75_cm: float | None = None
    maximum_cm: float | None = None

    def __post_init__(self) -> None:
        _aware(self.timestamp)


@dataclass(frozen=True)
class RiverForecastReport:
    """Forecast provenance source_time is issue time, not download time."""

    points: tuple[RiverForecastPoint, ...] = ()
    provenance: Provenance | None = None
    issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class RiverSummary:
    """Current and worst future median class, with explicit horizon coverage."""

    current: RiverAssessment
    forecast: RiverAssessment
    first_at: datetime | None
    covered_until: datetime | None
    complete: bool
    issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class WeatherReport:
    windows: tuple[WeatherWindow, ...]
    issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class LocalRouteInput:
    """Independent manual route status and car availability for one leg.

    Freshness and required renewed checks belong to the engine; an entry at
    decision time does not establish future route-clear conditions.
    """

    leg: CourierLeg
    snow: RouteSnow
    checked_at: datetime | None
    car_availability: Availability
    provenance: Provenance

    def __post_init__(self) -> None:
        if self.checked_at is not None:
            _aware(self.checked_at)


@dataclass(frozen=True)
class TreatmentRequest:
    """One non-personal scenario with original clocks preserved across plans."""

    treatment_id: str
    order_time: datetime
    original_collection: datetime
    nominal_departure: datetime
    decision_time: datetime
    routes: tuple[LocalRouteInput, ...]

    def __post_init__(self) -> None:
        for value in (
            self.order_time,
            self.original_collection,
            self.nominal_departure,
            self.decision_time,
        ):
            _aware(value)
        if sorted(route.leg for route in self.routes) != sorted(CourierLeg):
            raise ValueError("Supply exactly one route input for each courier leg.")


@dataclass(frozen=True)
class EnvironmentInputs:
    river: RiverReport
    weather: WeatherReport


@dataclass(frozen=True)
class PlanningSettings:
    """Config-owned limits and synthetic durations; no defaults in the contract.

    Rhine duration includes initial waiting from order to departure, unlike
    truck travel which starts after its separate preparation. Delay is a
    labelled scenario assumption, not a measured river-level conversion.
    """

    ingredient_limit: timedelta
    collection_shift_limit: timedelta
    sample_limit: timedelta
    production_limit: timedelta
    injection_limit: timedelta
    river_order_to_arrival: timedelta
    river_delay: timedelta
    truck_travel: timedelta
    truck_preparation: timedelta
    bicycle_travel: timedelta
    car_travel: timedelta
    car_preparation: timedelta
    production_processing: timedelta
    hospital_handling: timedelta
    route_status_freshness: timedelta
    bicycle_temperature_limit_c: float


@dataclass(frozen=True)
class TimelineEvent:
    """Preparation, journey, waiting, processing or handling on a shared axis."""

    event_id: str
    lane: str
    label: str
    interval: TimeWindow
    provenance: Provenance


@dataclass(frozen=True)
class ConstraintResult:
    """A named check and reason. Unknown evidence has no confirmed margin."""

    constraint: str
    status: CheckStatus
    reason: str
    margin: timedelta | None = None
    deadline: datetime | None = None
    actual_time: datetime | None = None

    def __post_init__(self) -> None:
        for value in (self.deadline, self.actual_time):
            if value is not None:
                _aware(value)


@dataclass(frozen=True)
class CandidatePlan:
    """An inspectable result; selection is a coordinator choice, not booking."""

    plan_id: str
    title: str
    status: ResultStatus
    ingredient_mode: TransportMode
    outbound_mode: TransportMode
    return_mode: TransportMode
    collection_shift: timedelta
    events: tuple[TimelineEvent, ...]
    checks: tuple[ConstraintResult, ...]
    assumptions: tuple[str, ...]


@runtime_checkable
class RiverProvider(Protocol):
    def load(self, window: TimeWindow) -> RiverReport:
        """Return readings and explicit coverage/retrieval issues."""
        ...


@runtime_checkable
class WeatherProvider(Protocol):
    def load(self, location: str, window: TimeWindow) -> WeatherReport:
        """Return interval evidence; missing coverage must remain explicit."""
        ...


@runtime_checkable
class PlanComparator(Protocol):
    def compare(
        self,
        request: TreatmentRequest,
        environment: EnvironmentInputs,
        settings: PlanningSettings,
    ) -> tuple[CandidatePlan, ...]:
        """Evaluate alternatives without modifying inputs or booking transport."""
        ...
