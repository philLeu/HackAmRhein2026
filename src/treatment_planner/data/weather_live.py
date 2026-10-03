"""Retrieve one MeteoSwiss forecast cycle for independently requested journeys."""

import csv
import json
import math
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from treatment_planner.data.weather_csv import (
    LOCAL_TIMEZONE,
    OPTIONAL_PARAMETERS,
    PARAMETERS,
    check_temperature_unit,
    iter_csv,
    measurements,
    normalized_rows,
    read_csv,
    select_location,
    select_run,
)
from treatment_planner.data.weather_windows import journey_weather, parse_iso_time
from treatment_planner.interfaces import EvidenceKind, Provenance, TimeWindow, WeatherReport

BASE_URL = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-local-forecasting"
COLLECTION_URL = (
    "https://data.geo.admin.ch/api/stac/v1/collections/ch.meteoschweiz.ogd-local-forecasting"
)
POINTS_URL = f"{BASE_URL}/ogd-local-forecasting_meta_point.csv"
PARAMETERS_URL = f"{BASE_URL}/ogd-local-forecasting_meta_parameters.csv"
MAXIMUM_UNAVAILABLE = "Daily maximum temperature unavailable in this MeteoSwiss forecast cycle."


def _official_url(url: str) -> None:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "data.geo.admin.ch"
        or parsed.port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("Expected an official HTTPS data.geo.admin.ch weather asset.")


def _download(url: str, timeout: float) -> bytes:
    _official_url(url)
    request = Request(url, headers={"User-Agent": "HackAmRhein-treatment-planner/2.0"})
    with urlopen(request, timeout=timeout) as response:
        _official_url(response.geturl())
        return response.read()


def _utc_now() -> datetime:
    return datetime.now(UTC)


class WeatherLiveProvider:
    """Load latest public weather once; refresh explicitly to replace the snapshot.

    Forecast age is assessed at the actual evaluation clock, independently of
    future validity coverage. No fallback to saved or synthetic data is made.
    The caller chooses a positive inspection age; no operational policy is assumed.
    """

    def __init__(
        self,
        maximum_forecast_age: timedelta,
        *,
        postal_code: str = "4056",
        timeout: float = 30,
        clock: Callable[[], datetime] = _utc_now,
        fetch: Callable[[str, float], bytes] = _download,
    ):
        if maximum_forecast_age <= timedelta(0):
            raise ValueError("maximum_forecast_age must be positive.")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be positive and finite.")
        if not postal_code.strip():
            raise ValueError("A postcode is required.")
        self.maximum_forecast_age = maximum_forecast_age
        self.postal_code = postal_code
        self.timeout, self.clock, self.fetch = timeout, clock, fetch
        self.refresh()

    def refresh(self) -> None:
        """Discard the snapshot; the next load retrieves actual provider evidence."""
        self._rows = None
        self._provenance = None
        self._failure = None

    def load(self, location: str, window: TimeWindow) -> WeatherReport:
        """Return this journey's evidence with gaps, stale age and means explicit."""
        if not location.strip():
            raise ValueError("A weather location label is required.")
        try:
            if self._rows is None and self._failure is None:
                self._retrieve()
            if self._failure is not None:
                return WeatherReport((), (self._failure,))
            now = parse_iso_time(self.clock().isoformat())
            report = journey_weather(
                self._rows,
                location,
                self._provenance,
                window,
                self.maximum_forecast_age,
                evaluated_at=now,
            )
            issues = report.issues
            if not any(window.maximum_temperature_c is not None for window in report.windows):
                issues += (MAXIMUM_UNAVAILABLE,)
            return WeatherReport(report.windows, issues)
        except (OSError, KeyError, TypeError, ValueError, AttributeError, csv.Error) as error:
            self._failure = f"Live weather unavailable: {error}. No simulated fallback was used."
            return WeatherReport((), (self._failure,))

    def _read(self, url: str) -> bytes:
        _official_url(url)
        return self.fetch(url, self.timeout)

    def _latest_item(self, now):
        today = now.astimezone(LOCAL_TIMEZONE).date()
        for offset in (0, 1):
            day = today - timedelta(days=offset)
            try:
                return json.loads(self._read(f"{COLLECTION_URL}/items/{day:%Y%m%d}-ch"))
            except HTTPError as error:
                if error.code != 404 or offset == 1:
                    raise

    def _retrieve(self):
        now = parse_iso_time(self.clock().isoformat())
        location = select_location(read_csv(self._read(POINTS_URL)), self.postal_code)
        parameter_metadata = read_csv(self._read(PARAMETERS_URL))
        item = self._latest_item(now)
        issued_at, urls = select_run(item["assets"])
        check_temperature_unit(
            parameter_metadata,
            optional_parameters=OPTIONAL_PARAMETERS & urls.keys(),
        )
        values = {
            parameter: measurements(iter_csv(self._read(urls[parameter])), location, parameter)
            for parameter in PARAMETERS
            if parameter in urls
        }
        for parameter in OPTIONAL_PARAMETERS & urls.keys():
            values[parameter] = measurements(
                iter_csv(self._read(urls[parameter])), location, parameter
            )
        retrieved_at = parse_iso_time(self.clock().isoformat())
        if issued_at > retrieved_at:
            raise ValueError("Forecast issue time is in the future relative to retrieval.")
        self._rows = normalized_rows(values, "live_capture")
        self._provenance = Provenance(
            f"Source: MeteoSwiss · postcode {self.postal_code} · "
            f"point type {location['point_type_id']}, ID {location['point_id']}",
            EvidenceKind.FORECAST,
            issued_at,
            retrieved_at,
        )
