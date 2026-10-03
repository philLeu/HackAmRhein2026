# Basel weather: T3 investigation

Status: downloader, documented snow-code mapping and synthetic offline example
verified; real capture still pending. This is T3 support, not the T7 application adapter.

## Source and fields

Candidate: [MeteoSwiss local forecasts](https://opendatadocs.meteoswiss.ch/e-forecast-data/e4-local-forecast-data).
The documented horizon is nine complete days including today, with hourly updates.
Actual available intervals must be inspected in each capture.

| Parameter | Meaning | Unit | Validity interval |
|---|---|---|---|
| `tre200h0` | Air temperature at 2 m, hourly mean | °C, checked against metadata | Preceding hour |
| `jww003i0` | Numeric MeteoSwiss weather type | Provider code | Preceding three hours |

The timestamp is the **end** of each interval, in UTC. A shared timestamp does not
mean the two measurements have identical validity intervals. CSVs use semicolons,
Latin-1 encoding and `YYYYMMDDHHMM` times. Local display uses `Europe/Zurich` with
the applicable UTC offset. Hourly mean temperature is not an hourly maximum.
[Provider specification](https://opendatadocs.meteoswiss.ch/e-forecast-data/e4-local-forecast-data).
The official notebook shows the timestamp header as `Date`. The parser matches
headers without case sensitivity and trims surrounding spaces. Selected-input
CSV headers are normalized to lowercase; original-download hashes are retained.

## Location and retrieval

The default postcode is 4056, matching the
[campus address](https://www.campus.novartis.com/en/inside-our-campus/getting-here).
This is a candidate forecast point for local courier journeys, not evidence of
weather everywhere on a route or along the Rotterdam–Basel shipment.

The utility looks up the real `point_id` in location metadata; it never assumes
that the ID equals a postcode. It selects postcode type `point_type_id=2` and
requires one match. Measurements are filtered by both point type and point ID.
Full selected location metadata is saved for the team to check before accepting
the capture as suitable for both courier routes.

Retrieval follows the
[official MeteoSwiss notebook](https://github.com/MeteoSwiss/opendata-localforecast-demos/blob/main/notebooks/Meteogram.ipynb):
read today's Swiss-date STAC item (`YYYYMMDD-ch`), then select the newest run
containing both required parameters. Assets use
`vnut12.lssw.YYYYMMDDHHmm.<parameter>.csv`; the run timestamp is retained separately
from retrieval time. Only a missing item (HTTP 404) permits looking at yesterday's
item; the resulting issue time remains visible. Parameters from different runs
are never mixed.

## Run and inspect

Python 3.9+ and the standard library are sufficient for this standalone helper on
a system with the Europe/Zurich timezone database. No package installation or
change to T1's application setup is needed. Run from the repository root:

```bash
python3 data/replay/weather/fetch_basel_weather.py
```

This downloads metadata and two country-wide parameter files, then saves a small
point-only capture in a new timestamped directory. Avoid repeated downloads while
testing the parser. An optional `--postal-code` selects another postcode;
`--output` specifies a new directory. Existing output directories are rejected.

For a clearly labelled example that works without internet:

```bash
python3 data/replay/weather/fetch_basel_weather.py --example
```

Each output directory contains:

- `forecast.csv`: temperature, raw code, German code description, statuses and
  separate interval starts; `valid_end_utc` is the shared end of those intervals.
- `preview.html`: readable table, issue time, coverage and source details.
- `provenance.json`: selected location, URLs, issue and retrieval times, input
  hashes, per-parameter coverage, gaps, snow mapping and its hash, attribution
  and transformation notes.
- `selected-input/`: point-only provider-format CSVs plus parameter metadata;
  headers are normalized to lowercase. Live captures also include the retrieved
  STAC item. Full-country forecast
  files are not retained. Downloaded and saved-input hashes distinguish filtering.

The committed `example-input/` rows, point ID, forecast timestamp and values are
**synthetic**, including the choice of weather codes. They exercise parsing and
the documented mapping rather than describe a realistic weather sequence. They
are not a MeteoSwiss forecast or T3's required real sample. Example output has no
provider or retrieval timestamp.

Offline verification:

```bash
python3 -m unittest discover -s data/replay/weather -p 'test_*.py' -v
```

## Snow and unsupported data

The mapping in `data/replay/weather/snow_codes.json` was checked against the
[official symbol-description PDF](https://www.meteoschweiz.admin.ch/dam/jcr:7ef804b7-3ebf-4056-b743-44346da7ac75/2022-02-14-Wetter-Icons-inkl-beschreibung-v1.pdf),
version 14 February 2022 / 2024, on 2026-10-03. Codes cover daytime 1–42 and
nighttime 101–142. Both snowfall and mixed rain/snow descriptions produce
`present`; other unambiguous documented codes produce `not_indicated`.
Missing, invalid or unfamiliar codes produce `unknown`. These are MeteoSwiss
codes; do not substitute the WMO/Open-Meteo mapping. No artwork is included.

`weather_description_de` provides a short German summary: snow, mixed rain/snow,
rain, thunderstorm, fog/high fog, or sunshine/clouds without coded precipitation.
Missing, invalid, ambiguous and unfamiliar codes get explicit labels. The raw
numeric code remains in the adjacent `weather_code` column.

Code 133 has inconsistent descriptions: German, French and Italian indicate
rain, while English indicates snow. It remains `unknown` pending clarification.
This exception is recorded in the mapping. Code 33 consistently indicates rain.
`present` refers to the forecast's three-hour aggregation interval;
`not_indicated` is not proof of a snow-free route or bicycle eligibility.

Missing or nonfinite values remain missing/invalid. Network failure produces an
error, never a synthetic replacement. A capture is a historical snapshot and
does not become fresh merely because it is opened again. Freshness is explicitly
`not_assessed`; the team must agree an acceptable age before T7 calls it usable.
Journey times outside available intervals, or across uncovered intervals, must
remain unconfirmed in T7. Unknown snowfall cannot establish bicycle eligibility.

Existing snow on the actual route remains the separate coordinator input defined
in [the team's decisions](../decisions.md). This helper does not choose transport,
change preparation times, define harbour storage or resolve the shipment clock.

## Licence and acceptance

MeteoSwiss data are distributed under CC BY 4.0. Use **Source: MeteoSwiss**, retain
the licence link and indicate filtering or other transformations; do not imply
endorsement. Icon artwork is excluded from this investigation.
[Official terms](https://opendatadocs.meteoswiss.ch/general/terms-of-use).

Before completing T3, run a real capture with network access, inspect the selected
location and actual rows, verify temperature metadata and observed code coverage, and
record the outcome in [the task handoff](../../handoff/t3-weather-research.md).
