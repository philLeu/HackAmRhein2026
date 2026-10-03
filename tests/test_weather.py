"""Weather replay adaptation preserves validity, uncertainty and source meaning."""

import csv
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from treatment_planner.data.weather import WeatherReplayProvider
from treatment_planner.interfaces import EvidenceKind, TimeWindow, WeatherProvider


CAPTURE = Path(__file__).parents[1] / "data/replay/weather/capture-20261003T112609Z"
SYNTHETIC = Path(__file__).parents[1] / "data/replay/weather/synthetic-example"
UTC_NOW = datetime(2026, 10, 3, 11, tzinfo=UTC)


def test_saved_weather_capture_implements_contract_and_keeps_interval_meaning():
    provider = WeatherReplayProvider(CAPTURE, timedelta(days=30))
    assert isinstance(provider, WeatherProvider)
    report = provider.load(
        "hospital to factory",
        TimeWindow(datetime(2026, 10, 3, 8, tzinfo=UTC), datetime(2026, 10, 3, 10, tzinfo=UTC)),
    )
    assert report.windows
    assert all(item.location == "hospital to factory" for item in report.windows)
    assert all(item.provenance.kind is EvidenceKind.REPLAY for item in report.windows)
    assert all(item.maximum_temperature_c is None for item in report.windows)
    assert all(item.hourly_mean_temperature_c is not None for item in report.windows)
    assert all(item.interval.start < item.interval.end for item in report.windows)


def test_snow_intervals_expand_across_three_hour_validity_window():
    provider = WeatherReplayProvider(SYNTHETIC, timedelta(days=30))
    report = provider.load(
        "return",
        TimeWindow(datetime(2026, 10, 3, 7, tzinfo=UTC), datetime(2026, 10, 3, 9, tzinfo=UTC)),
    )
    assert any(item.snowfall is True for item in report.windows)
    assert all(item.provenance.kind is EvidenceKind.SYNTHETIC for item in report.windows)


def test_outside_horizon_and_unknown_values_are_reported():
    provider = WeatherReplayProvider(SYNTHETIC, timedelta(days=30))
    report = provider.load(
        "return",
        TimeWindow(datetime(2026, 10, 3, 10, tzinfo=UTC), datetime(2026, 10, 3, 12, tzinfo=UTC)),
    )
    assert any("outside forecast horizon" in issue for issue in report.issues)
    assert any(item.maximum_temperature_c is None for item in report.windows)


def test_old_forecast_is_explicitly_stale():
    provider = WeatherReplayProvider(CAPTURE, timedelta(minutes=1))
    report = provider.load(
        "return",
        TimeWindow(datetime(2026, 10, 5, 8, tzinfo=UTC), datetime(2026, 10, 5, 9, tzinfo=UTC)),
    )
    assert any("Stale weather forecast" in issue for issue in report.issues)


def test_freshness_policy_must_be_positive():
    with pytest.raises(ValueError, match="must be positive"):
        WeatherReplayProvider(CAPTURE, timedelta(0))


def test_missing_capture_reports_unavailable_data(tmp_path):
    report = WeatherReplayProvider(tmp_path, timedelta(days=1)).load(
        "return", TimeWindow(UTC_NOW, UTC_NOW + timedelta(hours=1))
    )
    assert not report.windows
    assert "unavailable" in report.issues[0]


def test_hourly_mean_column_is_kept_distinct_from_maximum(tmp_path):
    capture = tmp_path / "capture"
    capture.mkdir()
    row = {
        "valid_end_utc": "2026-10-03T12:00:00Z",
        "temperature_valid_start_utc": "2026-10-03T11:00:00Z",
        "temperature_c": "30.1",
        "temperature_status": "available",
        "weather_valid_start_utc": "2026-10-03T09:00:00Z",
        "snow_forecast_status": "not_indicated",
    }
    with (capture / "forecast.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=row)
        writer.writeheader()
        writer.writerow(row)
    (capture / "provenance.json").write_text(
        json.dumps(
            {
                "synthetic": False,
                "forecast_issued_at_utc": "2026-10-03T11:00:00Z",
                "retrieved_at_utc": "2026-10-03T11:05:00Z",
            }
        ),
        encoding="utf-8",
    )
    report = WeatherReplayProvider(capture, timedelta(hours=2)).load(
        "return",
        TimeWindow(datetime(2026, 10, 3, 11, tzinfo=UTC), datetime(2026, 10, 3, 12, tzinfo=UTC)),
    )
    assert report.windows[0].hourly_mean_temperature_c == 30.1
    assert report.windows[0].maximum_temperature_c is None
