"""Rhine adaptation preserves units, timestamps, provenance and uncertainty."""

import csv
import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

import pytest

from treatment_planner.data.rhine import RhineObservationProvider, RhineReplayProvider
from treatment_planner.interfaces import EvidenceKind, RiverProvider, TimeWindow

CAPTURE = Path(__file__).parents[1] / "data/replay/rhine"
NOW = datetime(2026, 10, 3, 9, tzinfo=UTC)
START = datetime(2026, 10, 3, 8, 30, tzinfo=UTC)
WINDOW = TimeWindow(START, START + timedelta(minutes=25))
AGE = timedelta(hours=1)


def replay(path=CAPTURE, now=NOW):
    return RhineReplayProvider(path, AGE, clock=lambda: now)


def capture(tmp_path, *, field=None, value=None):
    shutil.copytree(CAPTURE, tmp_path / "capture")
    directory = tmp_path / "capture"
    if field:
        with (directory / "observations.csv").open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            fields, rows = reader.fieldnames, list(reader)
        rows[0][field] = value
        with (directory / "observations.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fields)
            writer.writeheader()
            writer.writerows(rows)
    return directory


def source_row(time=START, **changes):
    return {
        "timestamp": time.isoformat(),
        "pegelhoehe": 468.1,
        "pegel": 244.681,
        "abfluss": 262.084,
        **changes,
    }


def live(payload, **kwargs):
    return RhineObservationProvider(
        AGE, clock=lambda: NOW, fetch_json=lambda url, timeout: payload, **kwargs
    )


def test_saved_replay_contract_units_and_unknown_original_retrieval():
    provider = replay()
    assert isinstance(provider, RiverProvider)
    report = provider.load(WINDOW)
    assert len(report.observations) == 5
    first, last = report.observations[0], report.observations[-1]
    assert first.water_level_m == pytest.approx(4.681)
    assert last.water_level_m == pytest.approx(4.809)
    assert first.discharge_m3_s == pytest.approx(262.084)
    assert first.station.endswith("(2289)")
    assert first.observed_at == START
    assert first.provenance.source_time == START
    assert first.provenance.retrieved_at == NOW
    assert first.provenance.kind is EvidenceKind.REPLAY
    assert "Basel-Stadt" in first.provenance.source
    assert len(report.issues) == 1
    assert "original retrieval time is unknown" in report.issues[0]


def test_window_is_half_open_and_replay_is_never_extrapolated():
    report = replay().load(TimeWindow(START, START + timedelta(minutes=5)))
    assert len(report.observations) == 1
    report = replay().load(TimeWindow(NOW, NOW + timedelta(days=5)))
    assert not report.observations
    assert any("outside" in issue for issue in report.issues)
    assert any("not forecasts" in issue for issue in report.issues)


def test_stale_replay_and_partial_coverage_are_explicit():
    report = replay(now=NOW + timedelta(days=1)).load(TimeWindow(START - timedelta(minutes=5), NOW))
    assert any("Stale" in issue for issue in report.issues)
    assert any("start" in issue for issue in report.issues)
    assert any("beyond" in issue for issue in report.issues)


@pytest.mark.parametrize(
    "field,value",
    [
        ("timestamp_utc", "2026-10-03T08:30:00"),
        ("station_id", "9999"),
        ("abfluss_m3_s", "nan"),
        ("abfluss_m3_s", "inf"),
        ("abfluss_m3_s", "-1"),
        ("pegel_m_asl", "250"),
        ("pegelhoehe_cm", "wrong"),
    ],
)
def test_invalid_replay_rows_are_flagged_not_silently_normalised(tmp_path, field, value):
    report = replay(capture(tmp_path, field=field, value=value)).load(WINDOW)
    assert len(report.observations) == 4
    assert any("Invalid Rhine replay row" in issue for issue in report.issues)


def test_missing_parameter_stays_unknown(tmp_path):
    report = replay(capture(tmp_path, field="abfluss_m3_s", value="")).load(WINDOW)
    assert report.observations[0].discharge_m3_s is None
    assert any("Missing Rhine water level or discharge" in issue for issue in report.issues)


def test_duplicate_and_internal_gap_are_explicit(tmp_path):
    report = replay(capture(tmp_path, field="timestamp_utc", value="2026-10-03T08:35:00Z")).load(
        WINDOW
    )
    assert len(report.observations) == 4
    assert any("Duplicate" in issue for issue in report.issues)
    directory = tmp_path / "capture"
    path = directory / "observations.csv"
    lines = path.read_text().splitlines()
    path.write_text("\n".join(lines[:3] + lines[4:]) + "\n")
    assert any("within" in issue for issue in replay(directory).load(WINDOW).issues)


def test_wrong_units_and_missing_files_return_empty_report(tmp_path):
    assert not replay(tmp_path).load(WINDOW).observations
    directory = capture(tmp_path)
    path = directory / "manifest.json"
    metadata = json.loads(path.read_text())
    metadata["units"]["pegelhoehe_cm"] = "m"
    path.write_text(json.dumps(metadata))
    report = replay(directory).load(WINDOW)
    assert not report.observations
    assert "units" in report.issues[0]


def test_live_offset_normalisation_and_elevation_fallback():
    row = source_row(timestamp="2026-10-03T10:30:00+02:00", pegelhoehe=None)
    provider = live({"results": [row], "total_count": 1})
    assert isinstance(provider, RiverProvider)
    report = provider.load(TimeWindow(START, START + timedelta(minutes=5)))
    assert not report.issues
    observation = report.observations[0]
    assert observation.observed_at == START
    assert observation.water_level_m == pytest.approx(4.681)
    assert observation.provenance.kind is EvidenceKind.OBSERVATION
    assert observation.provenance.retrieved_at == NOW


def test_live_pagination_query_and_timeout():
    calls = []
    rows = [source_row(START + timedelta(minutes=5 * i)) for i in range(101)]
    end = START + timedelta(minutes=505)

    def fetch(url, timeout):
        query = parse_qs(urlparse(url).query)
        calls.append((query, timeout))
        offset = int(query["offset"][0])
        return {"results": rows[offset : offset + 100], "total_count": 101}

    provider = RhineObservationProvider(
        timedelta(days=1), clock=lambda: end, fetch_json=fetch, timeout=7
    )
    report = provider.load(TimeWindow(START, end))
    assert len(report.observations) == 101
    assert not report.issues
    assert [call[0]["offset"] for call in calls] == [["0"], ["100"]]
    assert all(call[1] == 7 for call in calls)
    assert "timestamp < date'" in calls[0][0]["where"][0]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [],
        {"results": {}, "total_count": 1},
        {"results": [], "total_count": "wrong"},
    ],
)
def test_bad_response_shape_reports_failure(payload):
    report = live(payload).load(WINDOW)
    assert not report.observations
    assert any("retrieval failed" in issue for issue in report.issues)


@pytest.mark.parametrize(
    "error",
    [URLError("offline"), TimeoutError("timed out"), json.JSONDecodeError("bad JSON", "", 0)],
)
def test_network_and_json_failure_are_explicit(error):
    def fetch(url, timeout):
        raise error

    report = RhineObservationProvider(AGE, fetch_json=fetch, clock=lambda: NOW).load(WINDOW)
    assert not report.observations
    assert any("retrieval failed" in issue for issue in report.issues)


def test_pagination_limit_preserves_partial_data_with_issue():
    rows = [source_row(START + timedelta(seconds=i)) for i in range(100)]
    report = live({"results": rows, "total_count": 101}, maximum_pages=1).load(WINDOW)
    assert len(report.observations) == 100
    assert any("page limit" in issue for issue in report.issues)


def test_future_measurements_and_non_numeric_values_are_rejected():
    rows = [
        source_row(NOW + timedelta(minutes=5)),
        source_row(abfluss=True),
        source_row(timestamp=None),
        source_row(abfluss={}),
    ]
    report = live({"results": rows, "total_count": 4}).load(WINDOW)
    assert not report.observations
    assert any("future observation" in issue for issue in report.issues)
    assert any("Invalid Rhine source row" in issue for issue in report.issues)


def test_freshness_policy_must_be_explicit_and_positive():
    with pytest.raises(ValueError):
        RhineReplayProvider(CAPTURE, timedelta(0))
    with pytest.raises(ValueError):
        RhineObservationProvider(timedelta(seconds=-1))


def test_later_page_failure_preserves_readings_without_claiming_complete_coverage():
    rows = [source_row(START + timedelta(seconds=i)) for i in range(100)]

    def fetch(url, timeout):
        offset = int(parse_qs(urlparse(url).query)["offset"][0])
        if offset:
            raise URLError("offline")
        return {"results": rows, "total_count": 101}

    provider = RhineObservationProvider(AGE, clock=lambda: NOW, fetch_json=fetch)
    report = provider.load(WINDOW)
    assert len(report.observations) == 100
    assert any("retrieval failed" in issue for issue in report.issues)
