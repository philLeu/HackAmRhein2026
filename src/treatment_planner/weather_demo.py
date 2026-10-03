"""Adapt one independent simulated courier override without renewing real evidence."""

from math import isfinite

from treatment_planner.interfaces import (
    EvidenceKind,
    LocalRouteInput,
    LocalRouteOverride,
    TimeWindow,
    WeatherReport,
    WeatherWindow,
)


def _validate_override(override: LocalRouteOverride) -> None:
    if override.provenance.kind != EvidenceKind.SYNTHETIC:
        raise ValueError("Demo route conditions require explicitly synthetic provenance.")
    temperature = override.maximum_temperature_c
    if temperature is not None and (isinstance(temperature, bool) or not isfinite(temperature)):
        raise ValueError("Simulated maximum temperature must be finite or unknown.")
    if override.forecast_snowfall is not None and not isinstance(override.forecast_snowfall, bool):
        raise ValueError("Simulated snowfall must be Yes, No or Unknown.")


class DemoWeatherProvider:
    """Carry this route's simulated values to a supplied candidate journey.

    Call with the courier leg's location label. The original entered interval,
    source timestamp and simulated provenance remain unchanged; the integration
    layer can display carry-over using demo_carry_over.
    """

    def __init__(self, override: LocalRouteOverride):
        _validate_override(override)
        self.override = override

    def load(self, location: str, window: TimeWindow) -> WeatherReport:
        """Cover this journey with simulated maxima and forecast snowfall only."""
        if location != self.override.leg.value:
            raise ValueError("Demo weather must use its own courier leg's location label.")
        return WeatherReport(
            (
                WeatherWindow(
                    location,
                    window,
                    self.override.maximum_temperature_c,
                    self.override.forecast_snowfall,
                    self.override.provenance,
                ),
            )
        )


def demo_route_input(override: LocalRouteOverride) -> LocalRouteInput:
    """Preserve independent route snow and car availability at the fixture clock."""
    _validate_override(override)
    return LocalRouteInput(
        override.leg,
        override.route_snow,
        override.provenance.source_time,
        override.car_availability,
        override.provenance,
    )


def demo_carry_over(override: LocalRouteOverride, journey: TimeWindow) -> TimeWindow | None:
    """Return the originally entered interval for a moved simulated journey."""
    _validate_override(override)
    return override.interval if journey != override.interval else None
