"""Keep the standalone capture CLI using the application's shared parser."""

import sys
from pathlib import Path

# The research CLI also works without installing the application package.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from treatment_planner.data.weather_csv import (  # noqa: E402
    LOCAL_TIMEZONE,
    PARAMETERS,
    SNOW_CODE_MAPPING,
    UTC,
    check_temperature_unit,
    coverage,
    iso_time,
    measurements,
    normalized_rows,
    numeric_value,
    parse_time,
    read_csv,
    select_location,
    select_run,
    selected_point_csv,
    snow_forecast_status,
    weather_description_de,
)

__all__ = [
    "LOCAL_TIMEZONE",
    "PARAMETERS",
    "SNOW_CODE_MAPPING",
    "UTC",
    "check_temperature_unit",
    "coverage",
    "iso_time",
    "measurements",
    "normalized_rows",
    "numeric_value",
    "parse_time",
    "read_csv",
    "select_location",
    "select_run",
    "selected_point_csv",
    "snow_forecast_status",
    "weather_description_de",
]
