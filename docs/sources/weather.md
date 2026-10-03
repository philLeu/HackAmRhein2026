# Basel weather: T3 investigation

Status: downloader, documented snow-code mapping, synthetic offline example and
permitted real capture verified. The historical capture at
`data/replay/weather/capture-20261003T112609Z/` is for inspection and replay; it
is not a current forecast. This is T3 source research, with the T7 adapter
documented below.

## Source and fields

Candidate: [MeteoSwiss local forecasts](https://opendatadocs.meteoswiss.ch/e-forecast-data/e4-local-forecast-data).
The documented horizon is nine complete days including today, with hourly updates.
Actual available intervals must be inspected in each capture.

| Parameter | Meaning | Unit | Validity interval |
|---|---|---|---|
| `tre200h0` | Air temperature at 2 m, hourly mean | °C, checked against metadata | Preceding hour |
| `tre200px` | Daily maximum air temperature | °C, checked against metadata | Local calendar day |
| `jww003i0` | Numeric MeteoSwiss weather type | Provider code | Preceding three hours |

The timestamp is the **end** of each interval, in UTC. A shared timestamp does not
mean the two measurements have identical validity intervals. CSVs use semicolons,
Latin-1 encoding and `YYYYMMDDHHMM` times. Local display uses `Europe/Zurich` with
the applicable UTC offset. Hourly mean temperature is not an hourly maximum.
[Provider specification](https://opendatadocs.meteoswiss.ch/e-forecast-data/e4-local-forecast-data).
The official notebook shows the timestamp header as `Date`. The parser matches
headers without case sensitivity and trims surrounding spaces. Selected-input
CSV headers are normalized to lowercase; original-download hashes are retained. `tre200px`
is optional: when present, its daily value applies across the local calendar day
for the trip-day reminder. It is not an hourly measurement.

## Location and retrieval

The model calls postcode 4056 the **PulseShift production site**. Its MeteoSwiss
physical reference is the [Novartis Campus](https://www.campus.novartis.com/en/inside-our-campus/getting-here);
the demo assumes PulseShift is located there. The other endpoint is postcode
4031, the [University Hospital Basel](https://wwwprod.usb.ch/en/kontakt). Both
points are used for each local courier journey. They are endpoint forecasts, not
evidence of weather at every point along a route or along the Rotterdam–Basel shipment.

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

`WeatherReplayProvider` reads one capture directory offline. Its constructor
requires a positive maximum forecast age; compare issue time to each requested
journey interval and treat older evidence as stale. This parameter is deliberately
required because the team has not approved a shared age limit. The adapter emits
separate journey windows, and reports missing intervals, unknown values, stale
forecasts and requests outside the capture horizon as issues. For the source's
`tre200h0` hourly mean it fills `hourly_mean_temperature_c`; it leaves
`maximum_temperature_c` unknown when the optional daily maximum is absent. Live
planning uses snowfall for bicycle eligibility and shows a separate recheck
reminder when the daily maximum forecast is at least 28°C. Current overview
temperatures are MeteoSwiss hourly means, not live thermometer readings. Weather
symbols are derived from MeteoSwiss weather codes; proprietary artwork is not used.

Existing snow on the actual route remains the separate coordinator input defined
in [the team's decisions](../decisions.md). This helper does not choose transport,
change preparation times, define harbour storage or resolve the shipment clock.

## Licence and acceptance

MeteoSwiss data are distributed under CC BY 4.0. Use **Source: MeteoSwiss**, retain
the licence link and indicate filtering or other transformations; do not imply
endorsement. Icon artwork is excluded from this investigation.
[Official terms](https://opendatadocs.meteoswiss.ch/general/terms-of-use).

T3's real capture is saved at
`data/replay/weather/capture-20261003T112609Z/`. It records the selected point,
real forecast rows, parameter metadata, issue and retrieval times, coverage,
hashes and licence attribution. Re-run the capture utility for current data; do
not treat this historical snapshot as fresh. The outcome is summarized in
[the task handoff](../../handoff/t3-weather-research.md).

## V2 live provider and independent demo routes

`WeatherLiveProvider`, exported from `src/treatment_planner/data/weather.py`,
loads the latest complete MeteoSwiss cycle automatically on its first `load`.
The required positive `maximum_forecast_age` is a caller-supplied inspection
limit, not an approved operational policy. Postcode 4056 is the default forecast
point; `postal_code` can be supplied explicitly. Point metadata is resolved by
both type and ID, and the selected point is identified in source provenance.

The provider reuses that cycle across sample and treatment journey requests;
`refresh()` discards it and the next load retrieves new provider evidence.
This avoids repeated country-wide downloads on every UI rerun. The integration
layer should retain the provider instance until an explicit refresh, display
issue/retrieval times and invalidate confirmation when material evidence changes.
Cached forecast age is reassessed on every load at the actual evaluation clock,
not at the future journey time. Validity coverage is assessed separately for
each requested journey. Replay retains its existing journey-relative age check.

Live network/metadata failures produce an empty report with an explicit issue.
Only a daily-item HTTP 404 permits yesterday's item; no saved or synthetic data
is substituted. Unknown snowfall, internal gaps and time outside the forecast
horizon remain unknown. The live provider always explicitly reports that hourly
mean temperature cannot establish the maximum-temperature check.

Live access was verified on 2026-10-03 at 18:45 UTC: postcode 4056 resolved to
point type 2, ID 405600; cycle 18:00 UTC covered the sample interval at 19:00–20:00
UTC and a separate interval two days later. A request twelve days later remained
outside coverage. This verification is historical evidence of access, not a
forecast to use for current planning. The provider specification and CC BY 4.0
terms linked above were checked again for this task.

The parser now lives in `src/treatment_planner/data/weather_csv.py`, shared by
live retrieval and the existing standalone capture utility. Its compatibility
entry point keeps the documented T3 commands working without installation.
The existing documented snow-code mapping remains the single source of rules.

`src/treatment_planner/weather_demo.py` consumes V2-3's `LocalRouteOverride`:

- Construct one `DemoWeatherProvider` per sample/treatment override and load it
  using that override's `CourierLeg.value` and the candidate journey interval.
  Temperature is explicitly a simulated maximum; forecast snowfall stays separate
  from snow already on the route. None values remain unknown.
- `demo_route_input` supplies that leg's route snow and independent car availability
  without changing its simulated source/check timestamp.
- `demo_carry_over` returns the originally entered interval when the candidate
  journey moves. Pass it to the route summary's `carried_from` field and show the
  approved carry-over note; it is not a data-quality failure in `WeatherReport.issues`.

Adapters accept explicitly synthetic overrides only. Their source interval,
values and provenance remain unchanged when conditions carry over. Real/live
evidence is never extended this way. An absent override retains the route's
baseline fixture; the V2-8 integration layer owns that selection, combining
reports, Live/Demo switching and reset. V2-8 wires the live/demo providers into
the guided application.

### Trip-day temperature reminder

The team-requested advisory threshold is inclusive at 28°C, configured in
`config/weather.json`. In Live mode, MeteoSwiss `tre200px` supplies the daily
maximum when available; it displays a reminder to refresh weather on the trip
day and recheck the plan before departure. The overview labels hourly mean
temperature separately. Unknown or nonfinite temperatures do not become known
heat warnings.

The comparison screen shows this reminder beside the inspected current plan.
The logic is in `src/treatment_planner/weather_advisories.py`.

This is an advisory only: it is separate from `WeatherReport.issues`, does not
change the Live snowfall-based bicycle eligibility rule or recommendation
scores. A displayed reminder can mark the route summary At risk for coordinator
review, but does not block the bicycle.
It does not schedule a future refresh. Unsupported maxima and stale/missing
coverage remain unknown independently of whether a reminder is shown.
