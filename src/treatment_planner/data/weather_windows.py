"""Clip normalized forecast rows while preserving gaps and measurement meaning."""

from datetime import datetime, timedelta

from treatment_planner.interfaces import Provenance, TimeWindow, WeatherReport, WeatherWindow


def parse_iso_time(value: str) -> datetime:
    """Read a provider timestamp without guessing a missing timezone."""
    if not isinstance(value, str):
        raise ValueError("timestamps must be ISO 8601 strings.")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamps must include a timezone.")
    return parsed


def journey_weather(
    rows: list[dict],
    location: str,
    provenance: Provenance,
    window: TimeWindow,
    maximum_forecast_age: timedelta,
    *,
    evaluated_at: datetime | None = None,
) -> WeatherReport:
    """Separate validity coverage from issue age at the supplied live clock.

    Replay preserves its existing journey-relative inspection policy when no
    evaluation clock is supplied. Live age is assessed at planning time, so a
    valid future forecast does not become stale simply because the trip is later.
    """
    records = _read_records(rows)
    boundaries = {window.start, window.end}
    fresh_until = provenance.source_time + maximum_forecast_age
    if evaluated_at is None and window.start < fresh_until < window.end:
        boundaries.add(fresh_until)
    for record in records:
        for parameter in ("temperature", "snow"):
            start, end = record[f"{parameter}_start"], record[f"{parameter}_end"]
            if end > window.start and start < window.end:
                boundaries.update((max(start, window.start), min(end, window.end)))
    points = sorted(boundaries)
    result, issues = [], set()
    for start, end in zip(points, points[1:]):
        temperature = _covering(records, "temperature_start", "temperature_end", start, end)
        mean = temperature["temperature"] if temperature else None
        snowfall = _snowfall_for(records, start, end)
        if mean is None:
            issues.add(_coverage_issue("temperature", start, records))
        if snowfall is None:
            issues.add(_coverage_issue("snowfall", start, records))
        if (evaluated_at or end) > fresh_until:
            issues.add(f"Stale weather forecast for journey interval starting {start.isoformat()}.")
        result.append(
            WeatherWindow(location, TimeWindow(start, end), None, snowfall, provenance, mean)
        )
    return WeatherReport(tuple(result), tuple(sorted(issues)))


def _read_records(rows):
    records = []
    for row in rows:
        end = parse_iso_time(row["valid_end_utc"])
        temperature_start = parse_iso_time(row["temperature_valid_start_utc"])
        snow_start = parse_iso_time(row["weather_valid_start_utc"])
        if temperature_start >= end or snow_start >= end:
            raise ValueError("Forecast interval must end after its start.")
        try:
            temperature = (
                float(row["temperature_c"]) if row["temperature_status"] == "available" else None
            )
        except (TypeError, ValueError):
            temperature = None
        if temperature is not None and not (-float("inf") < temperature < float("inf")):
            temperature = None
        status = row["snow_forecast_status"]
        records.append(
            {
                "temperature_start": temperature_start,
                "temperature_end": end,
                "temperature": temperature,
                "snow_start": snow_start,
                "snow_end": end,
                "snowfall": True
                if status == "present"
                else False
                if status == "not_indicated"
                else None,
            }
        )
    return records


def _covering(records, start_key, end_key, start, end):
    return next(
        (record for record in records if record[start_key] <= start and record[end_key] >= end),
        None,
    )


def _snowfall_for(records, start, end):
    covering = [
        record for record in records if record["snow_start"] <= start and record["snow_end"] >= end
    ]
    if any(record["snowfall"] is True for record in covering):
        return True
    if covering and all(record["snowfall"] is False for record in covering):
        return False
    return None


def _coverage_issue(parameter, start, records):
    prefix = "snow" if parameter == "snowfall" else "temperature"
    starts = [record[f"{prefix}_start"] for record in records]
    ends = [record[f"{prefix}_end"] for record in records]
    within_horizon = bool(records) and min(starts) <= start < max(ends)
    label = "unknown within forecast coverage" if within_horizon else "outside forecast horizon"
    return f"Weather {parameter} {label} at {start.isoformat()}."
