"""Trip-day temperature reminders kept separate from feasibility and evidence issues."""

import json
from datetime import UTC, timedelta
from math import isfinite
from pathlib import Path

from treatment_planner.interfaces import EvidenceKind, TimeWindow, WeatherReport

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config/weather.json"


def weather_recheck_warnings(
    report: WeatherReport,
    journey: TimeWindow,
    *,
    location: str,
    trip_label: str,
) -> tuple[str, ...]:
    """Warn at the configured temperature threshold for this trip's actual coverage.

    This advisory does not infer a maximum from an hourly mean, alter the plan
    status or schedule an automatic refresh. Unknown temperatures remain unknown.
    """
    threshold = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))[
        "temperature_recheck_threshold_c"
    ]
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise ValueError("Temperature warning threshold must be numeric.")
    if not isfinite(threshold):
        raise ValueError("Temperature warning threshold must be finite.")
    peaks = {}
    for window in report.windows:
        if (
            window.location != location
            or window.interval.start >= journey.end
            or window.interval.end <= journey.start
        ):
            continue
        origin = "simulated" if window.provenance.kind == EvidenceKind.SYNTHETIC else "forecast"
        for statistic, temperature in (
            ("maximum", window.maximum_temperature_c),
            ("hourly mean", window.hourly_mean_temperature_c),
        ):
            if (
                temperature is not None
                and not isinstance(temperature, bool)
                and isfinite(temperature)
                and temperature >= threshold
            ):
                key = (origin, statistic)
                peaks[key] = max(peaks.get(key, temperature), temperature)
    start_date = journey.start.astimezone(UTC).date()
    end_date = (journey.end - timedelta(microseconds=1)).astimezone(UTC).date()
    dates = str(start_date) if start_date == end_date else f"{start_date}–{end_date}"
    return tuple(
        f"{trip_label}: {origin} {statistic} temperature reaches {temperature:g} °C "
        f"(warning threshold: {threshold:g} °C). "
        f"{'In live operation, refresh' if origin == 'simulated' else 'Refresh'} weather "
        f"on the day of this trip ({dates} UTC) and recheck whether the plan is still "
        "feasible before departure."
        for (origin, statistic), temperature in peaks.items()
    )
