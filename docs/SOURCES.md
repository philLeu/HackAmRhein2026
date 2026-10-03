# Sources

This index links provider-owned notes; field meanings, licences, retrieval methods and coverage belong in those notes.

## Environmental evidence

- [Rhine source notes](sources/rhine.md): FOEN/BAFU hydrological observations via Open Data Basel-Stadt, CC0 1.0. The T6 adapter reads the permitted five-row replay at `data/replay/rhine/observations.csv`. The original retrieval time is unknown. The chart also uses a separate two-day observation and BAFU ensemble forecast capture in `data/replay/rhine/forecast-capture/`, with optional live retrieval. BAFU permits free forecast-data use with recommended source attribution; the separate forecast is not labelled CC0. A Basel gauge observation is not proof of future or whole-route navigability.
- [Weather source notes](sources/weather.md): Source: MeteoSwiss, CC BY 4.0. The T7 adapter reads `data/replay/weather/capture-20261003T112609Z/forecast.csv` with its provenance. Temperature is hourly mean, not maximum; snowfall codes and coverage retain the documented limitations. Proprietary weather artwork is not used.
- [Approved synthetic scenarios](scenarios.md): invented treatment, transport/process durations, Rhine delays and weather disruptions. The integrated walkthrough uses these inputs with the planning engine; it does not reuse authored feasibility results. Synthetic evidence and provider replay are separate screen modes.

## Integration limits

Both planning screen modes and the default Rhine chart replay work without network access. Only explicitly selecting live Rhine chart evidence makes public network requests. Saved-provider replay uses a historical evaluation clock at 2026-10-03 11:30 UTC; the captures are not current data. Positive freshness values are adjustable inspection controls, not approved operational policy. The provider mode does not enable synthetic future-route renewal. Missing maximum temperature, original retrieval time, stale forecasts and coverage issues remain visible. Weather is requested across each leg's candidate journey envelope; issues conservatively affect bicycle alternatives across that envelope. Source notes remain the authority for location suitability and data limitations.

## Tools and libraries

| What | Source | Licence / use |
|---|---|---|
| Codex (OpenAI) | https://chatgpt.com/codex | AI-assisted development tool |
| Streamlit | https://docs.streamlit.io/ | Apache-2.0; screen and interaction checks |
| Altair | https://altair-viz.github.io/ | BSD-3-Clause; timelines |
| pytest | https://docs.pytest.org/ | MIT; tests |
| Ruff | https://docs.astral.sh/ruff/ | MIT; formatting and lint |
| setuptools / wheel | https://setuptools.pypa.io/ / https://wheel.readthedocs.io/ | MIT; packaging |
