# T2: Rhine source investigation

Converted from @luapreta-cloud's `Rhein_water_first_try.ipynb` on 2026-10-03.
The notebook was read as JSON, never executed or edited. This is research for
T6; it does not implement an adapter or a transport decision.

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

Its saved output reports **573 rows**, from 2026-10-01 09:10 UTC to
2026-10-03 08:50 UTC. Only the last five rows are present as saved tabular
output; the full dataframe is not embedded. Those five displayed rows are
preserved in `data/replay/rhine/observations.csv`, at their displayed precision.
The notebook's original request time is unknown. The manifest records that
explicitly; conversion and metadata verification times are not measurement
or original retrieval times. Do not claim the saved output is a complete
two-day series or silently fill its gaps.

## Forecast investigation (separate from observations)

The notebook supplies a candidate reader for official FOEN Plotly JSON:

- [Level forecast](https://www.hydrodaten.admin.ch/plots/p_forecast/2289_p_forecast_en.json), in m above sea level.
- [Discharge forecast](https://www.hydrodaten.admin.ch/plots/q_forecast/2289_q_forecast_en.json), notebook candidate in m³/s; not independently fetched in this conversion.

The level endpoint was checked on 2026-10-03. Its median has 118 hourly points
from **2026-10-03 11:00+02:00 to 2026-10-08 08:00+02:00**, with the issue
annotation “Forecast as of 03.10.26 11:00”. It also contains two min/max traces,
a closed 25th–75th percentile polygon and a measured trace. This is one
verified run's coverage, not a guaranteed API horizon. No forecast output is
saved in the original notebook and no forecast replay is included here.
FOEN's FAQ permits free use with recommended source citation; do not assume
the Basel dataset's CC0 label applies to the separate forecast service.

T6 should validate trace names, aligned times/lengths, finite values, bounds
and issue time; normalize source offsets to UTC. Convert levels using the
verified 240 m datum. Keep median and uncertainty separate from observations.
The notebook chooses the nearest forecast point and, when the requested
horizon exceeds coverage, reports the last point. Production integration must
instead return explicit outside-horizon/unknown coverage for that request.
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
inside its 5 cm band. Its saved latest assessment is warning at 480.9 cm,
with a derived draft of 234.9 cm. Preserve this as the notebook's calculation,
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
complete. T6 remains responsible for the adapter, missing/stale-data handling,
forecast integration and contract tests. T9 should link these notes from
`docs/SOURCES.md` when integrating Rhine data.
