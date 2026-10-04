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
        for parameter in ("temperature", "snow", "maximum_temperature"):
            start, end = record[f"{parameter}_start"], record[f"{parameter}_end"]
            if start is not None and end is not None and end > window.start and start < window.end:
                boundaries.update((max(start, window.start), min(end, window.end)))
    points = sorted(boundaries)
    result, issues = [], set()
    for start, end in zip(points, points[1:]):
        temperature = _covering(records, "temperature_start", "temperature_end", start, end)
        mean = temperature["temperature"] if temperature else None
        maximum = _covering(
            records, "maximum_temperature_start", "maximum_temperature_end", start, end
        )
        maximum_c = maximum["maximum_temperature"] if maximum else None
        snowfall = _snowfall_for(records, start, end)
        condition = _covering(records, "snow_start", "snow_end", start, end)
        if mean is None and maximum_c is None:
            issues.add(_coverage_issue("temperature", start, records))
        if snowfall is None:
            issues.add(_coverage_issue("snowfall", start, records))
        if (evaluated_at or end) > fresh_until:
            issues.add(f"Stale weather forecast for journey interval starting {start.isoformat()}.")
        result.append(
            WeatherWindow(
                location,
                TimeWindow(start, end),
                maximum_c,
                snowfall,
                provenance,
                mean,
                condition["weather_code"] if condition else None,
            )
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
        try:
            maximum_temperature = (
                float(row["maximum_temperature_c"])
                if row.get("maximum_temperature_status") == "available"
                else None
            )
        except (TypeError, ValueError):
            maximum_temperature = None
        if maximum_temperature is not None and not (
            -float("inf") < maximum_temperature < float("inf")
        ):
            maximum_temperature = None
        maximum_start = (
            parse_iso_time(row["maximum_temperature_valid_start_utc"])
            if row.get("maximum_temperature_valid_start_utc")
            else None
        )
        maximum_end = (
            parse_iso_time(row["maximum_temperature_valid_end_utc"])
            if row.get("maximum_temperature_valid_end_utc")
            else None
        )
        if (maximum_start is None) != (maximum_end is None) or (
            maximum_start is not None and maximum_start >= maximum_end
        ):
            raise ValueError("Daily maximum validity interval must have positive duration.")
        status = row["snow_forecast_status"]
        records.append(
            {
                "temperature_start": temperature_start,
                "temperature_end": end,
                "temperature": temperature,
                "maximum_temperature_start": maximum_start,
                "maximum_temperature_end": maximum_end,
                "maximum_temperature": maximum_temperature,
                "snow_start": snow_start,
                "snow_end": end,
                "weather_code": (
                    int(row["weather_code"]) if row.get("weather_code") not in (None, "") else None
                ),
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
        (
            record
            for record in records
            if record[start_key] is not None
            and record[end_key] is not None
            and record[start_key] <= start
            and record[end_key] >= end
        ),
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
    prefix = {
        "snowfall": "snow",
        "maximum temperature": "maximum_temperature",
    }.get(parameter, "temperature")
    starts = [record[f"{prefix}_start"] for record in records if record[f"{prefix}_start"]]
    ends = [record[f"{prefix}_end"] for record in records if record[f"{prefix}_end"]]
    within_horizon = bool(starts) and min(starts) <= start < max(ends)
    label = "unknown within forecast coverage" if within_horizon else "outside forecast horizon"
    return f"Weather {parameter} {label} at {start.isoformat()}."
