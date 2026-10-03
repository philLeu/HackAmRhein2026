"""Shared MeteoSwiss parsing for live evidence and the capture utility."""

import csv
import io
import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

UTC = timezone.utc
LOCAL_TIMEZONE = ZoneInfo("Europe/Zurich")
# Provider aggregation intervals; see docs/sources/weather.md.
PARAMETERS = {"tre200h0": timedelta(hours=1), "jww003i0": timedelta(hours=3)}
TEMPERATURE_UNIT = "°C"
ASSET_NAME = re.compile(r"^vnut12\.lssw\.(\d{12})\.(tre200h0|jww003i0)\.csv$")
SNOW_CODE_MAPPING = json.loads(
    (Path(__file__).resolve().parents[3] / "data/replay/weather/snow_codes.json").read_text(
        encoding="utf-8"
    )
)


def read_csv(content):
    """Decode provider CSV and recognize headers regardless of their case."""
    return list(iter_csv(content))


def iter_csv(content):
    """Stream normalized CSV rows so national files need not become dict lists."""
    reader = csv.DictReader(io.StringIO(content.decode("latin-1")), delimiter=";")
    if not reader.fieldnames:
        raise ValueError("CSV has no header.")
    headers = [name.strip().lower() for name in reader.fieldnames]
    if len(headers) != len(set(headers)):
        raise ValueError("CSV has duplicate column names after header normalization.")
    reader.fieldnames = headers
    return reader


def select_location(rows, postal_code):
    """Select one postcode point, retaining its full provider metadata."""
    matches = [
        row
        for row in rows
        if row.get("postal_code") == str(postal_code) and row.get("point_type_id") == "2"
    ]
    if len(matches) != 1 or not matches[0].get("point_id"):
        raise ValueError(f"Expected one postcode point for {postal_code}; found {len(matches)}.")
    return matches[0]


def selected_point_csv(content, location):
    """Save a small point-only input instead of a whole-country forecast file."""
    rows = read_csv(content)
    if not rows:
        raise ValueError("Cannot filter an empty point CSV.")
    selected = [
        row
        for row in rows
        if row.get("point_id") == location["point_id"]
        and row.get("point_type_id") == location["point_type_id"]
    ]
    if not selected:
        raise ValueError("No selected point in input CSV.")
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter=";", lineterminator="\n")
    writer.writeheader()
    writer.writerows(selected)
    return stream.getvalue().encode("latin-1")


def check_temperature_unit(rows):
    """Reject a changed/missing unit rather than mislabelling a temperature."""
    matches = [row for row in rows if row.get("parameter_shortname") == "tre200h0"]
    if len(matches) != 1 or matches[0].get("parameter_unit") != TEMPERATURE_UNIT:
        raise ValueError("Temperature metadata must specify tre200h0 in °C.")


def select_run(assets):
    """Choose the newest run containing both parameters, never mixing cycles."""
    runs = {}
    for name, asset in assets.items():
        match = ASSET_NAME.fullmatch(name)
        if match and asset.get("href"):
            run, parameter = match.groups()
            runs.setdefault(run, {})[parameter] = asset["href"]
    complete = [run for run, files in runs.items() if set(files) == set(PARAMETERS)]
    if not complete:
        raise ValueError("No forecast run contains both temperature and weather type.")
    run = max(complete)
    return parse_time(run), runs[run]


def parse_time(value):
    """Read the provider's YYYYMMDDHHMM timestamp as UTC, not local time."""
    if not re.fullmatch(r"\d{12}", value):
        raise ValueError(f"Expected YYYYMMDDHHMM, received {value!r}.")
    return datetime.strptime(value, "%Y%m%d%H%M").replace(tzinfo=UTC)


def iso_time(value):
    """Format an aware UTC timestamp consistently for CSV and provenance."""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def numeric_value(value, parameter):
    """Retain missing and invalid values explicitly; never invent safe weather."""
    if value is None or not value.strip():
        return "", "missing"
    try:
        number = float(value)
    except ValueError:
        return "", "invalid"
    if not math.isfinite(number):
        return "", "invalid"
    if parameter == "jww003i0":
        if not number.is_integer() or number < 0:
            return "", "invalid"
        return int(number), "available"
    return number, "available"


def snow_forecast_status(code, code_status):
    """Interpret documented forecast codes, preserving missing/ambiguous cases."""
    mapping = SNOW_CODE_MAPPING
    if code_status != "available" or code in mapping["ambiguous_codes"]:
        return "unknown"
    if code in mapping["snowfall_codes"] or code in mapping["mixed_rain_snow_codes"]:
        return "present"
    if any(lower <= code <= upper for lower, upper in mapping["known_code_ranges"]):
        return "not_indicated"
    return "unknown"


def weather_description_de(code, code_status):
    """Give the forecast code a short German description without guessing."""
    if code_status == "missing":
        return "Kein Wettercode verfügbar"
    if code_status != "available":
        return "Ungültiger Wettercode"
    mapping = SNOW_CODE_MAPPING
    if code in mapping["ambiguous_codes"]:
        return "Unklare Beschreibung (MeteoSwiss-Code 133)"
    if code in mapping["snowfall_codes"]:
        return "Schneefall oder Schneeschauer"
    if code in mapping["mixed_rain_snow_codes"]:
        return "Regen und Schnee gemischt"
    if code in mapping["rain_codes"]:
        return "Regen oder Regenschauer"
    if code in mapping["storm_codes"]:
        return "Gewitter"
    if code in mapping["fog_codes"]:
        return "Nebel oder Hochnebel"
    if any(lower <= code <= upper for lower, upper in mapping["known_code_ranges"]):
        return "Sonne oder Wolken; kein Niederschlag im Symbol"
    return f"Unbekannter MeteoSwiss-Code ({code})"


def measurements(rows, location, parameter):
    """Extract interval ends and values for the exact (type, id) point pair."""
    selected = [
        row
        for row in rows
        if row.get("point_id") == location["point_id"]
        and row.get("point_type_id") == location["point_type_id"]
    ]
    if not selected:
        raise ValueError(f"No {parameter} rows for the selected point.")
    result = {}
    for row in selected:
        if parameter not in row:
            raise ValueError(f"CSV has no {parameter} column.")
        if "date" not in row and "time" not in row:
            raise ValueError(f"{parameter} CSV has no Date/time column; found: {', '.join(row)}.")
        time_value = (row.get("date") or row.get("time") or "").strip()
        if not time_value:
            raise ValueError(f"{parameter} has an empty timestamp for the selected point.")
        timestamp = parse_time(time_value)
        if timestamp in result:
            raise ValueError(f"Duplicate {parameter} timestamp: {iso_time(timestamp)}.")
        result[timestamp] = numeric_value(row[parameter], parameter)
    return result


def normalized_rows(values, sample_kind):
    """Keep the two aggregation intervals separate in the inspection table."""
    timestamps = sorted(set().union(*(series.keys() for series in values.values())))
    result = []
    for end in timestamps:
        temperature, temperature_status = values["tre200h0"].get(end, ("", "missing"))
        code, code_status = values["jww003i0"].get(end, ("", "missing"))
        result.append(
            {
                "sample_kind": sample_kind,
                "valid_end_utc": iso_time(end),
                "valid_end_local": end.astimezone(LOCAL_TIMEZONE).isoformat(),
                "temperature_c": temperature,
                "temperature_status": temperature_status,
                "temperature_valid_start_utc": iso_time(end - PARAMETERS["tre200h0"]),
                "temperature_valid_start_local": (end - PARAMETERS["tre200h0"])
                .astimezone(LOCAL_TIMEZONE)
                .isoformat(),
                "weather_code": code,
                "weather_description_de": weather_description_de(code, code_status),
                "weather_code_status": code_status,
                "weather_valid_start_utc": iso_time(end - PARAMETERS["jww003i0"]),
                "weather_valid_start_local": (end - PARAMETERS["jww003i0"])
                .astimezone(LOCAL_TIMEZONE)
                .isoformat(),
                "snow_forecast_status": snow_forecast_status(code, code_status),
            }
        )
    return result


def coverage(values):
    """Describe actual nonempty intervals and gaps, rather than promised horizon."""
    result = {}
    for parameter, series in values.items():
        ends = sorted(end for end, (_, status) in series.items() if status == "available")
        gaps = []
        for previous, current in zip(ends, ends[1:]):
            start = current - PARAMETERS[parameter]
            if start > previous:
                gaps.append({"start_utc": iso_time(previous), "end_utc": iso_time(start)})
        result[parameter] = {
            "available_records": len(ends),
            "start_utc": iso_time(ends[0] - PARAMETERS[parameter]) if ends else None,
            "end_utc": iso_time(ends[-1]) if ends else None,
            "gaps": gaps,
            "aggregation_seconds": int(PARAMETERS[parameter].total_seconds()),
        }
    return result
