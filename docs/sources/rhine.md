# T2: Rhine source investigation

Converted from @luapreta-cloud's `Rhein_water_first_try.ipynb` on 2026-10-03.
The notebook was read as JSON without executing or editing it. The dashboard now reuses its classifications and BAFU ensemble forecast through dedicated modules; the evidence does not establish a transport decision.

## Selected observation source

- Dataset: [Rhein Wasserstand, Pegel und Abfluss, 100089](https://data.bs.ch/explore/dataset/100089/).
- Provider: FOEN/BAFU hydrological measurements, distributed by Open Data
  Basel-Stadt. Station: Rhein – Basel, Rheinhalle, FOEN **2289**, on the
  Kleinbasel bank near the Birs inflow.
- [Metadata API](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100089)
  verified on 2026-10-03. Selected evidence is saved in
  `data/replay/rhine/source-metadata.json`.
- Licence: **CC0 1.0**; metadata also permits commercial and noncommercial use
  without mandatory reference. Redistribution of the observation sample is
  permitted. Retain attribution: Bundesamt für Umwelt, Hydrologische Daten und
  Vorhersagen, via Open Data Basel-Stadt, reference date 2026-10-03.

| API field | Meaning | Unit |
|---|---|---|
| `timestamp` | Measurement timestamp | ISO 8601 with offset; normalize to UTC |
| `abfluss` | Discharge | m³/s |
| `pegelhoehe` | Gauge height above the station's 240 m datum | cm |
| `pegel` | Water surface elevation | m above sea level |

The datum relation is `pegelhoehe = (pegel - 240.00) * 100`.
Gauge height is not channel depth or a vessel's permissible draft. Metadata
states five-minute updates. The [FOEN FAQ](https://www.hydrodaten.admin.ch/en/questions)
describes current measurements as unverified raw data and heights as LN02.

### Retrieval and preserved sample

The notebook calls the public
`https://data.bs.ch/api/explore/v2.1/catalog/datasets/100089/records`
endpoint with `where=timestamp >= date'<UTC cutoff>'`, `order_by=timestamp asc`,
`limit=100`, and successive offsets of 100. It uses a 30-second timeout and
optional environment-based authentication. No credential is needed in the
sample or documentation. Confirm HTTP status, response shape, numeric values,
offset-aware timestamps and duplicate/missing records in T6.

The original T2 capture preserves only five displayed observations in
`data/replay/rhine/observations.csv`; its original retrieval time is unknown.
That limited sample remains the planning engine's historical observation evidence.
The updated notebook contains a newer saved two-day result and chart; it is not
itself a complete, reusable observation archive.

The new chart replay in `data/replay/rhine/forecast-capture/` was fetched directly
from the public sources. `observations.json` contains 576 five-minute records
from 2026-10-01 11:30 UTC through 2026-10-03 11:25 UTC, ending before the existing
11:30 UTC demo evaluation clock. `manifest.json` records actual retrieval times,
source URLs and the historical evaluation window. These downloads happened after
the evaluation instant; replay means historical source evidence inspected later,
not proof of the exact API response available at that historical instant.

## Forecast investigation (separate from observations)

The notebook supplies a candidate reader for official FOEN Plotly JSON:

- [Level forecast](https://www.hydrodaten.admin.ch/plots/p_forecast/2289_p_forecast_en.json), in m above sea level.
- [Discharge forecast](https://www.hydrodaten.admin.ch/plots/q_forecast/2289_q_forecast_en.json), notebook candidate in m³/s; not independently fetched in this conversion.

The level endpoint was checked on 2026-10-03. Its median has 118 hourly points
from **2026-10-03 11:00+02:00 to 2026-10-08 08:00+02:00**, with the issue
annotation “Forecast as of 03.10.26 11:00”. It also contains two min/max traces,
a closed 25th–75th percentile polygon and a measured trace. This is one
verified run's coverage, not a guaranteed API horizon. The updated notebook saves a forecast summary and chart. The full source Plotly JSON is now preserved in `data/replay/rhine/forecast-capture/forecast.json`.
FOEN's FAQ permits free use with recommended source citation; do not assume
the Basel dataset's CC0 label applies to the separate forecast service.

The forecast adapter validates trace names, aligned hourly times/lengths, finite values, ordered bounds, a closed percentile polygon and issue time; it normalizes source offsets to UTC. Convert levels using the
verified 240 m datum. Keep median and uncertainty separate from observations.
The notebook chooses the nearest forecast point and, when the requested
horizon exceeds coverage, reports the last point. Dashboard integration instead returns explicit outside-horizon/unknown coverage for that request.
Missing issue times, missing measured traces, stale data, HTTP failures or a
changed JSON shape must not become a normal river condition.

## Threshold findings: evidence versus notebook assumptions

| Notebook rule | Verification / interpretation |
|---|---|
| High water above 700 cm: limited navigation | Port authority identifies 700 cm as high-water mark I / pre-alert; this alone is not a general navigation prohibition. |
| High water above 790 cm: no navigation | Mark IIb closes specified Basel–Birsfelden large-shipping and Basel–Rheinfelden small-shipping/ferry stretches. Not a whole-route closure. |
| Above 620 / 670 cm: vessel length limited to 125 / 135 m | Preserved research claims; not verified against a current authoritative regulation here. |
| Available draft = gauge height minus 246 cm | Notebook assumption; not established as a general permissible-draft rule. |
| Draft below 350 cm: reduced load; below 230 cm: less than 50% / uneconomical | Unverified reference-vessel assumptions; no validated load/economic relation. The notebook comment's “350m draft” is inconsistent with its code, which uses 350 cm. |
| 5 cm threshold margin | Research heuristic, not an official restriction or uncertainty estimate. |

Verified high-water descriptions and the datum example come from
[Port of Switzerland](https://port-of-switzerland.ch/hafenservice/pegel/),
checked 2026-10-03. That page also distinguishes mark IIa at 820 cm. The
notebook uses strict `>` / `<` comparisons; equality yields a watch state
inside its 5 cm band. The new chart replay assesses warning at 479.7 cm, with a derived draft of 233.7 cm. The saved forecast median first becomes critical after the evaluation clock at 2026-10-03 22:00 UTC. Preserve this as the notebook's calculation,
not an official navigation assessment.

## Route usefulness and proposed synthetic disruption mapping

Rheinhalle is useful as a local Basel environmental signal near the shipment
destination. One gauge cannot establish Rotterdam–Basel navigability,
conditions at other bottlenecks, vessel loading, shipping availability or
arrival time. Its roughly five-day forecast also cannot confirm conditions
through every possible 5–10 day shipment. Future unsupported intervals stay
unconfirmed.

**Proposal only, explicitly synthetic:** use a coordinator-selected low-water
scenario to add 24 hours to an otherwise synthetic shipping duration; the
baseline adds zero. This is an illustrative mapping for team review, not a
delay inferred from these five rows or the notebook's draft thresholds. T5's
planning configuration owns any adopted delay rule. T6 supplies environmental
facts and coverage, never a shipment-delay recommendation. T4's agreed
scenarios remain authoritative; this proposal does not change them.

T2's inspectable, permitted observation sample and source documentation are
complete. T6 supplies the original observation adapter. T12/T13 add validated forecast loading, shared station assessments and the expandable chart; tests cover boundaries, missing/stale data, malformed traces and offline replay. `docs/SOURCES.md` links these notes.


## Dashboard forecast integration

The Rhine panel defaults to saved forecast replay and offers an explicit live
mode with a five-minute cache. It remains separate from the selected synthetic
planning scenario and does not change delivery delays or plan feasibility.
Live mode fetches the last two days of observations and the latest BAFU level
forecast. Network failures never trigger an implicit replay fallback.

The summary uses the latest nonfuture observation and the worst future median
class in the requested window. Missing/stale observations or missing/stale/future-
issued forecasts give unknown assessments. Forecast freshness is inspected with
a 24-hour maximum age; observation freshness uses six hours. These are demo
inspection policies, not validated operational recommendations. Partial coverage
shows the worst class within coverage and explicitly labels the remainder unknown.

Classification thresholds and the independent 5 cm margin are sourced from the
notebook and stored in `config/rhine.json`. Chart bands and written findings use
the same assessment function. The chart preserves measured/forecast line styles,
ensemble bands, near-limit texture and a full-scale restriction reference.

## V2 live ingredient evidence and demo override

V2 opens the ingredient evidence adapter in Live mode: it requests recent
Rheinhalle observations from the Basel-Stadt dataset and the BAFU level
forecast. The current reading must be no older than six hours and the forecast
run no older than 24 hours; these are demo freshness limits, not operational
recommendations. A missing value, stale source or future issue time remains
explicit. Forecast coverage is checked against the requested ingredient
journey interval. The adapter reports **outside forecast horizon** if the whole
future interval is not covered; it never extends the final forecast point.

The observations are normally reported at five-minute intervals. FOEN says
current hydrological values are unverified raw data and forecast values are
model output; source attribution is recommended and use is free. The Basel
dataset identifies station 2289 at Rheinhalle, near the Birs inflow. A fresh,
covered station report still does not establish navigability for the
Rotterdam–Basel route. [FOEN data FAQ](https://www.hydrodaten.admin.ch/en/questions),
[Basel dataset](https://data.bs.ch/explore/dataset/100089/).

The Demo control creates a typed `IngredientRouteOverride` with synthetic
provenance, a displayed gauge height in centimetres, and an explicit validity
interval. Its level is a simulated station value. For the demo only, crossing
the notebook's critical low-water draft threshold applies the approved T4
**simulated 12-hour** shipping delay; the baseline delay is zero. This is an
illustrative level-to-delay mapping, not an observed or calibrated delivery
prediction. Missing gauge input produces unknown delay, not zero. The adapter
exposes missing, stale and outside-horizon live evidence as states for the
integration/UI layers. Live provider failure never falls back to saved or
synthetic evidence automatically.

The V2 live smoke check on 2026-10-03 retrieved 573 observations and 118 hourly
forecast points. That run was issued at 15:00 UTC and covered through
2026-10-08 12:00 UTC. A five-day journey evaluated during that check extended
beyond the returned forecast and was labelled **outside forecast horizon**;
the adapter did not extrapolate it.
