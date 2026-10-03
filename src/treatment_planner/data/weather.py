"""Public live and replay weather providers for the shared contract."""

from __future__ import annotations

import csv
import json
from datetime import timedelta
from pathlib import Path

from treatment_planner.data.weather_live import WeatherLiveProvider as WeatherLiveProvider
from treatment_planner.data.weather_windows import journey_weather, parse_iso_time
from treatment_planner.interfaces import (
    EvidenceKind,
    Provenance,
    TimeWindow,
    WeatherReport,
)


class WeatherReplayProvider:
    """Adapt one saved forecast capture without network access or scheduling rules.

    ``maximum_forecast_age`` is required because the team has not approved a
    default freshness policy. Hourly means and the daily maximum are preserved
    as separate statistics with their distinct validity intervals.
    """

    def __init__(self, capture_directory: Path | str, maximum_forecast_age: timedelta):
        if maximum_forecast_age <= timedelta(0):
            raise ValueError("maximum_forecast_age must be positive.")
        self.capture_directory = Path(capture_directory)
        self.maximum_forecast_age = maximum_forecast_age

    def load(self, location: str, window: TimeWindow) -> WeatherReport:
        """Return clipped weather facts and explicit freshness/coverage issues."""
        if not location.strip():
            raise ValueError("A weather location label is required.")

        forecast_path = self.capture_directory / "forecast.csv"
        provenance_path = self.capture_directory / "provenance.json"
        try:
            with forecast_path.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            metadata = json.loads(provenance_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, csv.Error) as error:
            return WeatherReport((), (f"Weather replay unavailable: {error}",))
        if not rows:
            return WeatherReport((), ("Weather replay contains no forecast rows.",))

        try:
            issued_at = parse_iso_time(metadata["forecast_issued_at_utc"])
            retrieved_time = metadata.get("retrieved_at_utc") or metadata.get("generated_at_utc")
            retrieved_at = parse_iso_time(retrieved_time)
            kind = EvidenceKind.SYNTHETIC if metadata.get("synthetic") else EvidenceKind.REPLAY
            source = (
                "Synthetic MeteoSwiss-format example"
                if metadata.get("synthetic")
                else "MeteoSwiss replay"
            )
            provenance = Provenance(source, kind, issued_at, retrieved_at)
            return journey_weather(rows, location, provenance, window, self.maximum_forecast_age)
        except (KeyError, TypeError, ValueError) as error:
            return WeatherReport((), (f"Weather replay metadata or rows are invalid: {error}",))
