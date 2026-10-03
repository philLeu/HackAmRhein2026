"""Download an inspectable Basel forecast; use --example for synthetic offline data."""

import argparse
import csv
import hashlib
import html
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from weather_csv import (
    LOCAL_TIMEZONE,
    OPTIONAL_PARAMETERS,
    PARAMETERS,
    SNOW_CODE_MAPPING,
    UTC,
    check_temperature_unit,
    coverage,
    iso_time,
    measurements,
    normalized_rows,
    read_csv,
    select_location,
    select_run,
    selected_point_csv,
)

BASE_URL = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-local-forecasting"
COLLECTION_URL = (
    "https://data.geo.admin.ch/api/stac/v1/collections/ch.meteoschweiz.ogd-local-forecasting"
)
METADATA_URLS = {
    "points": f"{BASE_URL}/ogd-local-forecasting_meta_point.csv",
    "parameters": f"{BASE_URL}/ogd-local-forecasting_meta_parameters.csv",
}
# Verified campus postcode; the provider point ID is looked up, not guessed.
DEFAULT_POSTAL_CODE = "4056"
REQUEST_TIMEOUT_SECONDS = 30


def download(url):
    """Read official HTTPS assets, raising network errors without fake fallback."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "data.geo.admin.ch":
        raise ValueError("Expected an official HTTPS data.geo.admin.ch asset.")
    request = Request(url, headers={"User-Agent": "HackAmRhein-weather-research/1.0"})
    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return response.read()


def latest_item(now):
    """Use today's Swiss-date item, or yesterday only when today's item is absent."""
    today = now.astimezone(LOCAL_TIMEZONE).date()
    for offset in (0, 1):
        day = today - timedelta(days=offset)
        url = f"{COLLECTION_URL}/items/{day:%Y%m%d}-ch"
        try:
            return json.loads(download(url)), url
        except HTTPError as error:
            if error.code != 404 or offset == 1:
                raise
    raise ValueError("No forecast item found.")


def live_inputs(postal_code):
    """Capture both parameters from one forecast cycle plus location metadata."""
    raw = {f"{name}.csv": download(url) for name, url in METADATA_URLS.items()}
    location = select_location(read_csv(raw["points.csv"]), postal_code)
    item, item_url = latest_item(datetime.now(UTC))
    issued_at, urls = select_run(item["assets"])
    check_temperature_unit(
        read_csv(raw["parameters.csv"]),
        optional_parameters=OPTIONAL_PARAMETERS & urls.keys(),
    )
    raw["stac-item.json"] = json.dumps(item, indent=2).encode("utf-8")
    for parameter, url in urls.items():
        raw[f"{parameter}.csv"] = download(url)
    return raw, location, issued_at, {**METADATA_URLS, "stac_item": item_url, **urls}


def example_inputs(postal_code):
    """Read the explicitly synthetic fixture; this never contacts the provider."""
    directory = Path(__file__).parent / "example-input"
    raw = {path.name: path.read_bytes() for path in sorted(directory.glob("*.csv"))}
    location = select_location(read_csv(raw["points.csv"]), postal_code)
    check_temperature_unit(
        read_csv(raw["parameters.csv"]),
        optional_parameters=OPTIONAL_PARAMETERS
        & {name[:-4] for name in raw if name.endswith(".csv")},
    )
    issued_at = datetime(2026, 10, 3, 6, tzinfo=UTC)
    return raw, location, issued_at, {"fixture": "example-input; synthetic, not MeteoSwiss data"}


def preview(rows, provenance):
    """Make a plain inspection table, with provenance and unknown snow visible."""
    columns = {
        "valid_end_local": "Intervallende (Schweizer Zeit)",
        "temperature_valid_start_local": "Temperaturintervall ab (Schweizer Zeit)",
        "temperature_c": "Hourly mean temperature (°C)",
        "temperature_status": "Temperature status",
        "maximum_temperature_c": "Daily maximum temperature (°C)",
        "maximum_temperature_status": "Daily maximum status",
        "weather_valid_start_local": "Wetterintervall ab (Schweizer Zeit)",
        "weather_code": "Raw weather code",
        "weather_description_de": "Wetterbeschreibung (DE)",
        "weather_code_status": "Code status",
        "snow_forecast_status": "Snow forecast status",
    }
    heading = (
        "SYNTHETIC EXAMPLE — not a real forecast"
        if provenance["synthetic"]
        else "Basel forecast capture"
    )
    table = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(row[key]))}</td>" for key in columns) + "</tr>"
        for row in rows
    )
    headers = "".join(f"<th>{title}</th>" for title in columns.values())
    metadata = html.escape(json.dumps(provenance, ensure_ascii=False, indent=2))
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f"<title>{heading}</title></head><body><h1>{heading}</h1>"
        "<p>Snow status follows the documented MeteoSwiss codes. Missing, unfamiliar "
        "or ambiguous codes remain unknown. This forecast does not establish snow "
        "already on the route. Forecast freshness has not been assessed. "
        "Hourly means and daily maximum forecasts are separate values; the daily maximum "
        "applies to the local calendar day.</p>"
        f'<table border="1"><thead><tr>{headers}</tr></thead><tbody>{table}</tbody></table>'
        f"<h2>Provenance</h2><pre>{metadata}</pre></body></html>"
    )


def save_capture(output, raw, location, issued_at, urls, synthetic):
    """Validate before saving CSV, raw inputs, provenance and a readable table."""
    parameters = set(PARAMETERS) | (
        OPTIONAL_PARAMETERS & {name[:-4] for name in raw if name.endswith(".csv")}
    )
    values = {
        parameter: measurements(read_csv(raw[f"{parameter}.csv"]), location, parameter)
        for parameter in parameters
    }
    rows = normalized_rows(values, "synthetic" if synthetic else "live_capture")
    selected = {
        name: selected_point_csv(content, location)
        if name in {"points.csv", "tre200h0.csv", "jww003i0.csv", "tre200px.csv"}
        else content
        for name, content in raw.items()
    }
    provenance = {
        "synthetic": synthetic,
        "provider": None if synthetic else "MeteoSwiss",
        "attribution": "Synthetic example" if synthetic else "Source: MeteoSwiss",
        "licence": None if synthetic else "CC BY 4.0",
        "terms_url": "https://opendatadocs.meteoswiss.ch/general/terms-of-use",
        "location": location,
        "forecast_issued_at_utc": iso_time(issued_at),
        "retrieved_at_utc": None if synthetic else iso_time(datetime.now(UTC)),
        "generated_at_utc": iso_time(datetime.now(UTC)),
        "source_urls": urls,
        "downloaded_sha256": {
            name: hashlib.sha256(content).hexdigest() for name, content in raw.items()
        },
        "saved_input_sha256": {
            name: hashlib.sha256(content).hexdigest() for name, content in selected.items()
        },
        "coverage": coverage(values),
        "snow_code_mapping": SNOW_CODE_MAPPING,
        "snow_code_mapping_sha256": hashlib.sha256(
            Path(__file__).with_name("snow_codes.json").read_bytes()
        ).hexdigest(),
        "freshness_status": "not_assessed; team policy required",
        "transformations": (
            "Point-only input CSVs with trimmed lowercase headers, "
            "UTC interval starts, local display time; "
            "raw numeric codes retained with a short German description."
        ),
    }
    output.mkdir(parents=True, exist_ok=False)
    input_directory = output / "selected-input"
    input_directory.mkdir()
    for name, content in selected.items():
        (input_directory / name).write_bytes(content)
    with (output / "forecast.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (output / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "preview.html").write_text(preview(rows, provenance), encoding="utf-8")
    return len(rows)


def main(argv=None):
    """CLI entry point; live is the default, synthetic requires an explicit flag."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postal-code", default=DEFAULT_POSTAL_CODE)
    parser.add_argument(
        "--example", action="store_true", help="Use labelled synthetic offline data."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="New output directory; existing folders are never overwritten.",
    )
    arguments = parser.parse_args(argv)
    prefix = "synthetic" if arguments.example else "capture"
    output = arguments.output or (
        Path(__file__).parent / f"{prefix}-{datetime.now(UTC):%Y%m%dT%H%M%SZ}"
    )
    try:
        if output.exists():
            raise FileExistsError(f"Output already exists: {output}. Choose a new directory.")
        inputs = (
            example_inputs(arguments.postal_code)
            if arguments.example
            else live_inputs(arguments.postal_code)
        )
        count = save_capture(output, *inputs, synthetic=arguments.example)
    except (OSError, URLError, ValueError, KeyError, TypeError) as error:
        print(f"Weather capture failed: {error}. No synthetic fallback was used.", file=sys.stderr)
        return 1
    print(f"Saved {count} rows ({prefix}) to {output.resolve()}")
    print(f"Open {(output / 'preview.html').resolve()} to inspect the table.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
