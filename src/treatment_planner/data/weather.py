"""Load an offline MeteoSwiss capture into the shared weather contract."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

from treatment_planner.interfaces import (
    EvidenceKind,
    Provenance,
    TimeWindow,
    WeatherReport,
    WeatherWindow,
)


class WeatherReplayProvider:
    """Adapt one saved forecast capture without network access or scheduling rules.

    ``maximum_forecast_age`` is required because the team has not approved a
    default freshness policy. Temperature is preserved as hourly mean evidence;
    maximum temperature stays unknown because the source does not provide it.
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
            issued_at = _parse_time(metadata["forecast_issued_at_utc"])
            retrieved_time = metadata.get("retrieved_at_utc") or metadata.get("generated_at_utc")
            retrieved_at = _parse_time(retrieved_time)
            kind = EvidenceKind.SYNTHETIC if metadata.get("synthetic") else EvidenceKind.REPLAY
            source = (
                "Synthetic MeteoSwiss-format example"
                if metadata.get("synthetic")
                else "MeteoSwiss replay"
            )
            provenance = Provenance(source, kind, issued_at, retrieved_at)
            records = _read_records(rows)
        except (KeyError, TypeError, ValueError) as error:
            return WeatherReport((), (f"Weather replay metadata or rows are invalid: {error}",))

        boundaries = {window.start, window.end}
        for record in records:
            if record["end"] > window.start and record["start"] < window.end:
                for interval_start, interval_end in (
                    (record["temperature_start"], record["temperature_end"]),
                    (record["snow_start"], record["snow_end"]),
                ):
                    if interval_end > window.start and interval_start < window.end:
                        boundaries.add(max(interval_start, window.start))
                        boundaries.add(min(interval_end, window.end))
        points = sorted(boundaries)
        result: list[WeatherWindow] = []
        issues: set[str] = set()
        for start, end in zip(points, points[1:]):
            if end <= start:
                continue
            temperature = _covering(records, "temperature_start", "temperature_end", start, end)
            snow = _snowfall_for(records, start, end)
            mean = temperature["temperature"] if temperature else None
            snowfall = snow

            if mean is None:
                issues.add(
                    _coverage_issue(
                        "temperature", start, records, "temperature_start", "temperature_end"
                    )
                )
            if snowfall is None:
                issues.add(_coverage_issue("snowfall", start, records, "snow_start", "snow_end"))
            if start - issued_at > self.maximum_forecast_age:
                issues.add(
                    f"Stale weather forecast for journey interval starting {start.isoformat()}."
                )

            result.append(
                WeatherWindow(
                    location=location,
                    interval=TimeWindow(start, end),
                    maximum_temperature_c=None,
                    snowfall=snowfall,
                    provenance=provenance,
                    hourly_mean_temperature_c=mean,
                )
            )
        return WeatherReport(tuple(result), tuple(sorted(issues)))


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamps must include a timezone.")
    return parsed


def _read_records(rows: list[dict[str, str | None]]) -> list[dict[str, object]]:
    records = []
    for row in rows:
        end = _parse_time(row["valid_end_utc"] or "")
        temperature_start = _parse_time(row["temperature_valid_start_utc"] or "")
        snow_start = _parse_time(row["weather_valid_start_utc"] or "")
        try:
            temperature = (
                float(row["temperature_c"])
                if row["temperature_status"] == "available"
                else None
            )
        except (TypeError, ValueError):
            temperature = None
        if temperature is not None and not (-float("inf") < temperature < float("inf")):
            temperature = None
        status = row["snow_forecast_status"]
        snowfall = True if status == "present" else False if status == "not_indicated" else None
        records.append(
            {
                "start": min(temperature_start, snow_start),
                "end": end,
                "temperature_start": temperature_start,
                "temperature_end": end,
                "temperature": temperature,
                "snow_start": snow_start,
                "snow_end": end,
                "snowfall": snowfall,
            }
        )
    return records


def _covering(records, start_key: str, end_key: str, start: datetime, end: datetime):
    return next(
        (
            record
            for record in records
            if record[start_key] <= start and record[end_key] >= end
        ),
        None,
    )


def _snowfall_for(records, start: datetime, end: datetime) -> bool | None:
    """Treat any overlapping documented snow signal as present."""
    covering = [
        record
        for record in records
        if record["snow_start"] <= start and record["snow_end"] >= end
    ]
    if any(record["snowfall"] is True for record in covering):
        return True
    if covering and all(record["snowfall"] is False for record in covering):
        return False
    return None


def _coverage_issue(
    parameter: str, start: datetime, records, start_key: str, end_key: str
) -> str:
    covered = [record for record in records if record[start_key] <= start < record[end_key]]
    label = "outside forecast horizon" if not covered else "unknown within forecast coverage"
    return f"Weather {parameter} {label} at {start.isoformat()}."
