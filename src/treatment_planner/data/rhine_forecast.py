"""Validated BAFU Plotly forecast reader and offline capture loader."""

import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import URLError
from zoneinfo import ZoneInfo

from treatment_planner.data.rhine import (
    GAUGE_DATUM_M,
    STATION,
    _fetch_json,
    _reading,
    _report,
    _time,
)
from treatment_planner.interfaces import (
    EvidenceKind,
    Provenance,
    RiverForecastPoint,
    RiverForecastReport,
    RiverReport,
    TimeWindow,
)

FORECAST_URL = "https://www.hydrodaten.admin.ch/plots/p_forecast/2289_p_forecast_en.json"


def _values(trace):
    times = tuple(_time(v) for v in trace["x"])
    if len(times) != len(trace["y"]):
        raise ValueError("misaligned trace timestamps and levels")
    values = []
    for value in trace["y"]:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError("forecast values must be finite numbers")
        values.append(round((value - GAUGE_DATUM_M) * 100, 6))
    return times, tuple(values)


def _issue_time(layout):
    annotations = [
        a for a in layout.get("annotations", []) if "forecast as of" in a.get("text", "").lower()
    ]
    if len(annotations) != 1:
        raise ValueError("missing or ambiguous forecast issue time")
    annotation = annotations[0]
    issued = _time(annotation["x"])
    displayed = datetime.strptime(
        annotation["text"].removeprefix("Forecast as of "), "%d.%m.%y %H:%M"
    )
    if issued.astimezone(ZoneInfo("Europe/Zurich")).replace(tzinfo=None) != displayed:
        raise ValueError("forecast issue annotation disagrees with its timestamp")
    return issued


def parse_forecast(
    payload: dict, retrieved_at: datetime, kind: EvidenceKind = EvidenceKind.FORECAST
) -> RiverForecastReport:
    """Require aligned hourly traces and ordered bounds; optional bands stay optional."""
    try:
        plot = payload["plot"]
        traces = plot["data"]
        median_traces = [t for t in traces if (t.get("name") or "").lower() == "median"]
        if len(median_traces) != 1:
            raise ValueError("expected one median trace")
        times, median = _values(median_traces[0])
        if not times or any((b - a).total_seconds() != 3600 for a, b in zip(times, times[1:])):
            raise ValueError("median must have contiguous hourly timestamps")
        issued = _issue_time(plot["layout"])
        bounds = [
            t for t in traces if (t.get("name") or "").lower() in ("min. / max.", "min - max")
        ]
        issues = []
        minimum = maximum = p25 = p75 = (None,) * len(times)
        if bounds:
            if len(bounds) != 2:
                raise ValueError("expected two min-max bounds")
            parsed = [_values(t) for t in bounds]
            if any(t != times for t, _ in parsed):
                raise ValueError("min-max timestamps do not match median")
            minimum = tuple(min(a, b) for a, b in zip(parsed[0][1], parsed[1][1]))
            maximum = tuple(max(a, b) for a, b in zip(parsed[0][1], parsed[1][1]))
        else:
            issues.append("Forecast min-max uncertainty band unavailable.")
        bands = [t for t in traces if "percentile" in (t.get("name") or "").lower()]
        if bands:
            if len(bands) != 1:
                raise ValueError("ambiguous percentile band")
            bt, bv = _values(bands[0])
            n = len(times)
            if bt != times + times[::-1] + (times[0],) or bv[-1] != bv[0]:
                raise ValueError("percentile polygon is not aligned and closed")
            p25 = tuple(min(a, b) for a, b in zip(bv[:n], bv[n : 2 * n][::-1]))
            p75 = tuple(max(a, b) for a, b in zip(bv[:n], bv[n : 2 * n][::-1]))
        else:
            issues.append("Forecast 25-75% uncertainty band unavailable.")
        points = tuple(
            RiverForecastPoint(*v) for v in zip(times, median, minimum, p25, p75, maximum)
        )
        for p in points:
            values = [
                v
                for v in (p.minimum_cm, p.p25_cm, p.median_cm, p.p75_cm, p.maximum_cm)
                if v is not None
            ]
            if values != sorted(values):
                raise ValueError("ensemble bounds must contain the median in order")
        return RiverForecastReport(
            points, Provenance(FORECAST_URL, kind, issued, retrieved_at), tuple(issues)
        )
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        return RiverForecastReport(issues=(f"BAFU forecast unavailable or invalid: {error}.",))


def load_live_forecast() -> RiverForecastReport:
    """Fetch the public run; report retrieval failures without automatic fallback."""
    try:
        payload = _fetch_json(FORECAST_URL, 30)
        return parse_forecast(payload, datetime.now(UTC))
    except (OSError, URLError, ValueError) as error:
        return RiverForecastReport(issues=(f"BAFU forecast retrieval failed: {error}.",))


def load_forecast_replay(directory: Path) -> tuple[RiverReport, RiverForecastReport, datetime]:
    """Use original capture times and declared historical evaluation time offline."""
    try:
        manifest = json.loads((directory / "manifest.json").read_text("utf-8"))
        if (
            manifest["station"] != "2289"
            or manifest["kind"] != "forecast_replay"
            or manifest["source"] != FORECAST_URL
        ):
            raise ValueError("unexpected replay station, source or kind")
        now = _time(manifest["evaluation_time"])
        report = parse_forecast(
            json.loads((directory / "forecast.json").read_text("utf-8")),
            _time(manifest["retrieved_at"]),
            EvidenceKind.REPLAY,
        )
        payload = json.loads((directory / "observations.json").read_text("utf-8"))
        readings = tuple(
            _reading(
                r["timestamp"],
                r.get("pegelhoehe"),
                r.get("pegel"),
                r.get("abfluss"),
                EvidenceKind.REPLAY,
                _time(manifest["observation_retrieved_at"]),
                manifest["observation_source"],
            )
            for r in payload["results"]
        )
        if any(r.station != STATION or r.observed_at >= now for r in readings):
            raise ValueError("replay observations extend beyond evaluation time")
        if len({r.observed_at for r in readings}) != len(readings):
            raise ValueError("duplicate replay observations")
        history = _report(
            readings,
            [],
            TimeWindow(_time(manifest["history_start"]), _time(manifest["history_end"])),
            now,
            timedelta(hours=6),
        )
        return history, report, now
    except (OSError, KeyError, TypeError, ValueError) as error:
        issue = f"Rhine forecast replay unavailable or invalid: {error}."
        return (
            RiverReport((), (issue,)),
            RiverForecastReport(issues=(issue,)),
            datetime(2026, 10, 3, 11, 30, tzinfo=UTC),
        )
