"""Rhine station observations, with explicit replay and coverage limitations."""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from treatment_planner.interfaces import (
    EvidenceKind,
    Provenance,
    RiverObservation,
    RiverReport,
    TimeWindow,
)

RECORDS_ENDPOINT = "https://data.bs.ch/api/explore/v2.1/catalog/datasets/100089/records"
STATION = "Rhein - Basel, Rheinhalle (2289)"
GAUGE_DATUM_M = 240.0
OBSERVATION_INTERVAL = timedelta(minutes=5)
PAGE_SIZE = 100


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO 8601 string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamps must include a timezone")
    return parsed.astimezone(UTC)


def _number(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("expected a numeric measurement")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("measurements must be finite")
    return result


def _reading(timestamp, height, elevation, discharge, kind, retrieved_at, source):
    observed_at = _time(timestamp)
    height, elevation, discharge = map(_number, (height, elevation, discharge))
    if height is not None and elevation is not None:
        if not math.isclose(height / 100, elevation - GAUGE_DATUM_M, abs_tol=0.001):
            raise ValueError("gauge height and elevation disagree with the 240 m datum")
    level = (
        height / 100
        if height is not None
        else (elevation - GAUGE_DATUM_M if elevation is not None else None)
    )
    if discharge is not None and discharge < 0:
        raise ValueError("discharge must not be negative")
    return RiverObservation(
        STATION,
        observed_at,
        Provenance(source, kind, observed_at, retrieved_at),
        water_level_m=level,
        discharge_m3_s=discharge,
    )


def _report(readings, issues, window, now, maximum_observation_age):
    """Keep valid readings, flag gaps, and never extend evidence into the future."""
    by_time = {}
    for reading in readings:
        if reading.observed_at > now:
            issues.append("Rhine source contains a future observation timestamp.")
            continue
        if reading.observed_at in by_time:
            issues.append("Duplicate Rhine observation timestamp.")
            continue
        by_time[reading.observed_at] = reading
    selected = sorted(
        (r for r in by_time.values() if window.start <= r.observed_at < window.end),
        key=lambda r: r.observed_at,
    )
    if not selected:
        issues.append(
            "No Rhine observations in the requested window; outside saved/source coverage."
        )
    else:
        if selected[0].observed_at - window.start >= OBSERVATION_INTERVAL:
            issues.append("Missing Rhine observations at the start of the requested window.")
        if window.end - selected[-1].observed_at > OBSERVATION_INTERVAL:
            issues.append("Requested window extends beyond Rhine observation coverage.")
        if any(
            b.observed_at - a.observed_at > OBSERVATION_INTERVAL
            for a, b in zip(selected, selected[1:])
        ):
            issues.append("Missing readings within Rhine observation coverage.")
        if now - selected[-1].observed_at > maximum_observation_age:
            issues.append("Stale Rhine observations relative to the evaluation time.")
        if any(r.water_level_m is None or r.discharge_m3_s is None for r in selected):
            issues.append("Missing Rhine water level or discharge measurement.")
    if window.end > now:
        issues.append("Future Rhine conditions are unknown; observations are not forecasts.")
    return RiverReport(tuple(selected), tuple(dict.fromkeys(issues)))


class RhineReplayProvider:
    """Read T2's permitted sample. Replay retrieval time is the local load time.

    The unknown original retrieval time is reported separately. Freshness is
    checked against ``clock`` (inject a historical evaluation time for replay).
    The caller supplies its freshness policy; no domain threshold is invented.
    """

    def __init__(
        self,
        capture_directory: Path | str,
        maximum_observation_age: timedelta,
        *,
        clock: Callable[[], datetime] = _utc_now,
    ):
        if maximum_observation_age <= timedelta(0):
            raise ValueError("maximum_observation_age must be positive")
        self.capture_directory = Path(capture_directory)
        self.maximum_observation_age = maximum_observation_age
        self.clock = clock

    def load(self, window: TimeWindow) -> RiverReport:
        """Load readings inside [start, end), keeping data problems explicit."""
        now = _time(self.clock().isoformat())
        issues, readings = [], []
        try:
            metadata = json.loads((self.capture_directory / "manifest.json").read_text("utf-8"))
            if metadata["kind"] != "observed_replay" or metadata["station"]["id"] != "2289":
                raise ValueError("expected an observed replay for station 2289")
            if metadata["station"]["gauge_datum_m_asl"] != GAUGE_DATUM_M:
                raise ValueError("unexpected gauge datum")
            expected_units = {
                "timestamp_utc": "ISO 8601 UTC",
                "abfluss_m3_s": "m3/s",
                "pegelhoehe_cm": "cm above 240 m gauge datum",
                "pegel_m_asl": "m above sea level (LN02)",
            }
            if metadata["units"] != expected_units:
                raise ValueError("unexpected replay units")
            original = metadata.get("original_retrieved_at_utc")
            if original is None:
                issues.append(
                    "Replay original retrieval time is unknown; retrieved_at is local load time."
                )
            else:
                _time(original)
            source = f"FOEN via Open Data Basel-Stadt replay: {metadata['source_dataset']}"
            with (self.capture_directory / "observations.csv").open(
                encoding="utf-8", newline=""
            ) as stream:
                for index, row in enumerate(csv.DictReader(stream), start=2):
                    try:
                        if row["station_id"] != "2289":
                            raise ValueError("unexpected station")
                        readings.append(
                            _reading(
                                row["timestamp_utc"],
                                row["pegelhoehe_cm"],
                                row["pegel_m_asl"],
                                row["abfluss_m3_s"],
                                EvidenceKind.REPLAY,
                                now,
                                source,
                            )
                        )
                    except (KeyError, TypeError, ValueError) as error:
                        issues.append(f"Invalid Rhine replay row {index}: {error}.")
        except (OSError, csv.Error, KeyError, TypeError, ValueError) as error:
            return RiverReport((), (f"Rhine replay unavailable or invalid: {error}.",))
        return _report(readings, issues, window, now, self.maximum_observation_age)


def _fetch_json(url: str, timeout: float) -> dict:
    with urlopen(url, timeout=timeout) as response:
        return json.load(response)


class RhineObservationProvider:
    """Retrieve station 2289 observations from T2's fixed public endpoint.

    Queries are bounded by ``maximum_pages`` and a per-request timeout. A
    failed page is explicit; partial results never become complete coverage.
    No automatic replay fallback or navigation/delivery inference is performed.
    """

    def __init__(
        self,
        maximum_observation_age: timedelta,
        *,
        timeout: float = 30,
        maximum_pages: int = 20,
        clock: Callable[[], datetime] = _utc_now,
        fetch_json: Callable[[str, float], dict] = _fetch_json,
    ):
        if maximum_observation_age <= timedelta(0):
            raise ValueError("maximum_observation_age must be positive")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be positive and finite")
        if (
            isinstance(maximum_pages, bool)
            or not isinstance(maximum_pages, int)
            or maximum_pages < 1
        ):
            raise ValueError("maximum_pages must be a positive integer")
        self.maximum_observation_age = maximum_observation_age
        self.timeout = timeout
        self.maximum_pages = maximum_pages
        self.clock = clock
        self.fetch_json = fetch_json

    def load(self, window: TimeWindow) -> RiverReport:
        """Fetch ordered readings with failures, gaps and stale data reported."""
        readings, issues = [], []
        for page in range(self.maximum_pages):
            query = urlencode(
                {
                    "where": (
                        f"timestamp >= date'{window.start.astimezone(UTC).isoformat()}' "
                        f"AND timestamp < date'{window.end.astimezone(UTC).isoformat()}'"
                    ),
                    "order_by": "timestamp asc",
                    "limit": PAGE_SIZE,
                    "offset": page * PAGE_SIZE,
                }
            )
            try:
                payload = self.fetch_json(f"{RECORDS_ENDPOINT}?{query}", self.timeout)
                retrieved_at = _time(self.clock().isoformat())
                rows = payload["results"]
                total = payload["total_count"]
                if not isinstance(rows, list) or len(rows) > PAGE_SIZE:
                    raise ValueError("invalid results list")
                if isinstance(total, bool) or not isinstance(total, int) or total < 0:
                    raise ValueError("invalid total_count")
                for index, row in enumerate(rows):
                    try:
                        readings.append(
                            _reading(
                                row["timestamp"],
                                row.get("pegelhoehe"),
                                row.get("pegel"),
                                row.get("abfluss"),
                                EvidenceKind.OBSERVATION,
                                retrieved_at,
                                f"FOEN via Open Data Basel-Stadt: {RECORDS_ENDPOINT}",
                            )
                        )
                    except (AttributeError, KeyError, TypeError, ValueError) as error:
                        issues.append(
                            f"Invalid Rhine source row {page * PAGE_SIZE + index}: {error}."
                        )
                if page * PAGE_SIZE + len(rows) >= total:
                    break
                if len(rows) < PAGE_SIZE:
                    issues.append("Rhine source returned an incomplete page.")
                    break
            except (OSError, URLError, KeyError, TypeError, ValueError) as error:
                issues.append(f"Rhine retrieval failed: {error}.")
                break
        else:
            issues.append("Rhine retrieval page limit reached; coverage is incomplete.")
        now = _time(self.clock().isoformat())
        return _report(readings, issues, window, now, self.maximum_observation_age)
