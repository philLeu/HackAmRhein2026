"""Live retrieval uses one cycle with actual issue time and explicit limitations."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from treatment_planner.data.weather import WeatherLiveProvider
from treatment_planner.data.weather_live import (
    BASE_URL,
    COLLECTION_URL,
    PARAMETERS_URL,
    POINTS_URL,
)
from treatment_planner.interfaces import EvidenceKind, TimeWindow, WeatherProvider

EXAMPLE = Path(__file__).parents[1] / "data/replay/weather/example-input"
NOW = datetime(2026, 10, 3, 6, 5, tzinfo=UTC)
JOURNEY = TimeWindow(NOW.replace(hour=7, minute=0), NOW.replace(hour=8, minute=0))


@pytest.fixture
def source():
    assets = {}
    payloads = {
        POINTS_URL: (EXAMPLE / "points.csv").read_bytes(),
        PARAMETERS_URL: (EXAMPLE / "parameters.csv").read_bytes(),
    }
    for parameter in ("tre200h0", "jww003i0"):
        name = f"vnut12.lssw.202610030600.{parameter}.csv"
        url = f"{BASE_URL}/{name}"
        assets[name] = {"href": url}
        # Git may check CSV fixtures out with CRLF on Windows. Normalize only
        # these test payloads so byte edits below remove the intended records.
        payloads[url] = (EXAMPLE / f"{parameter}.csv").read_bytes().replace(b"\r\n", b"\n")
    # A newer incomplete cycle must not mix with the complete 06:00 forecast.
    assets["vnut12.lssw.202610030700.tre200h0.csv"] = {"href": f"{BASE_URL}/unused.csv"}
    item_url = f"{COLLECTION_URL}/items/20261003-ch"
    payloads[item_url] = json.dumps({"assets": assets}).encode()
    calls = []

    def fetch(url, timeout):
        calls.append(url)
        value = payloads[url]
        if isinstance(value, Exception):
            raise value
        return value

    return payloads, calls, fetch


def test_latest_complete_cycle_preserves_means_intervals_and_real_provenance(source):
    _, calls, fetch = source
    provider = WeatherLiveProvider(timedelta(hours=2), clock=lambda: NOW, fetch=fetch)

    report = provider.load("sample", JOURNEY)

    assert isinstance(provider, WeatherProvider)
    assert report.windows
    assert all(w.location == "sample" and w.interval == JOURNEY for w in report.windows)
    assert report.windows[0].hourly_mean_temperature_c == 18.5
    assert report.windows[0].maximum_temperature_c is None
    assert report.windows[0].snowfall is True  # 09:00 snow applies from 06:00.
    provenance = report.windows[0].provenance
    assert provenance.kind == EvidenceKind.FORECAST
    assert provenance.source_time == NOW.replace(minute=0)
    assert provenance.retrieved_at == NOW
    assert "Source: MeteoSwiss" in provenance.source and "4056" in provenance.source
    assert any("hourly means" in issue for issue in report.issues)
    assert not any("unused.csv" in url for url in calls)


def test_snapshot_is_shared_by_legs_and_refresh_is_explicit(source):
    _, calls, fetch = source
    now = [NOW]
    provider = WeatherLiveProvider(timedelta(hours=2), clock=lambda: now[0], fetch=fetch)
    sample = provider.load("sample", JOURNEY)
    first_count = len(calls)
    now[0] += timedelta(minutes=5)
    returning = provider.load("treatment", JOURNEY)
    assert len(calls) == first_count
    assert sample.windows[0].provenance == returning.windows[0].provenance
    provider.refresh()
    refreshed = provider.load("sample", JOURNEY)
    assert len(calls) == 2 * first_count
    assert refreshed.windows[0].provenance.retrieved_at == now[0]


def test_live_age_is_planning_age_not_time_until_future_journey(source):
    _, _, fetch = source
    now = [NOW]
    provider = WeatherLiveProvider(timedelta(minutes=30), clock=lambda: now[0], fetch=fetch)
    assert not any("Stale" in i for i in provider.load("sample", JOURNEY).issues)
    now[0] += timedelta(hours=1)
    assert any("Stale" in i for i in provider.load("sample", JOURNEY).issues)


def test_outside_horizon_does_not_carry_live_conditions(source):
    _, _, fetch = source
    provider = WeatherLiveProvider(timedelta(hours=2), clock=lambda: NOW, fetch=fetch)
    window = TimeWindow(NOW + timedelta(days=10), NOW + timedelta(days=10, hours=1))
    report = provider.load("treatment", window)
    assert all(w.hourly_mean_temperature_c is None and w.snowfall is None for w in report.windows)
    assert any("outside forecast horizon" in i for i in report.issues)


def test_gaps_and_ambiguous_snow_codes_stay_unknown(source):
    payloads, _, fetch = source
    for url in tuple(payloads):
        if url.endswith(".tre200h0.csv"):
            payloads[url] = payloads[url].replace(b"2;synthetic-4056;202610030900;30.0\n", b"")
        if url.endswith(".jww003i0.csv"):
            payloads[url] = payloads[url].replace(b";16\n", b";133\n").replace(b";107\n", b";133\n")
    window = TimeWindow(NOW.replace(hour=8, minute=0), NOW.replace(hour=9, minute=0))
    report = WeatherLiveProvider(timedelta(hours=2), clock=lambda: NOW, fetch=fetch).load(
        "sample", window
    )
    assert report.windows[0].hourly_mean_temperature_c is None
    assert report.windows[0].snowfall is None
    assert any("unknown within forecast coverage" in i for i in report.issues)


def test_source_failure_has_no_replay_or_simulated_fallback(source):
    payloads, calls, fetch = source
    payloads[POINTS_URL] = URLError("provider unavailable")
    provider = WeatherLiveProvider(timedelta(hours=2), clock=lambda: NOW, fetch=fetch)
    report = provider.load("sample", JOURNEY)
    assert not report.windows
    assert "Live weather unavailable" in report.issues[0]
    assert "No simulated fallback" in report.issues[0]
    provider.load("treatment", JOURNEY)
    assert len(calls) == 1


@pytest.mark.parametrize("status", [404, 403])
def test_yesterday_is_used_only_for_missing_daily_item(source, status):
    payloads, calls, fetch = source
    today = f"{COLLECTION_URL}/items/20261003-ch"
    yesterday = f"{COLLECTION_URL}/items/20261002-ch"
    payloads[yesterday] = payloads[today]
    payloads[today] = HTTPError(today, status, "not accessible", {}, None)
    report = WeatherLiveProvider(timedelta(hours=2), clock=lambda: NOW, fetch=fetch).load(
        "sample", JOURNEY
    )
    assert (yesterday in calls) == (status == 404)
    assert bool(report.windows) == (status == 404)


def test_changed_units_and_unofficial_assets_are_rejected(source):
    payloads, _, fetch = source
    payloads[PARAMETERS_URL] = payloads[PARAMETERS_URL].replace(b"\xb0C", b"\xb0F")
    provider = WeatherLiveProvider(timedelta(hours=2), clock=lambda: NOW, fetch=fetch)
    assert "Temperature metadata" in provider.load("sample", JOURNEY).issues[0]
    payloads[PARAMETERS_URL] = (EXAMPLE / "parameters.csv").read_bytes()
    item_url = f"{COLLECTION_URL}/items/20261003-ch"
    payloads[item_url] = json.dumps(
        {
            "assets": {
                f"vnut12.lssw.202610030600.{p}.csv": {"href": "https://other.example/forecast.csv"}
                for p in ("tre200h0", "jww003i0")
            }
        }
    ).encode()
    provider.refresh()
    assert "official HTTPS" in provider.load("sample", JOURNEY).issues[0]


def test_future_issue_timestamp_is_not_accepted_as_fresh_evidence(source):
    _, _, fetch = source
    provider = WeatherLiveProvider(
        timedelta(hours=2), clock=lambda: NOW - timedelta(minutes=10), fetch=fetch
    )
    report = provider.load("sample", JOURNEY)
    assert not report.windows
    assert "issue time is in the future" in report.issues[0]
