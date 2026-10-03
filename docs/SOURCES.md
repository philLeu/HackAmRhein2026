# Sources

This index links provider-owned notes; field meanings, licences, retrieval methods and coverage belong in those notes.

## Environmental evidence

- [Rhine source notes](sources/rhine.md): FOEN/BAFU hydrological observations via Open Data Basel-Stadt, CC0 1.0. The T6 adapter reads the permitted five-row replay at `data/replay/rhine/observations.csv`. The original retrieval time is unknown. The chart also uses a separate two-day observation and BAFU ensemble forecast capture in `data/replay/rhine/forecast-capture/`, with optional live retrieval. BAFU permits free forecast-data use with recommended source attribution; the separate forecast is not labelled CC0. A Basel gauge observation is not proof of future or whole-route navigability.
- [Weather source notes](sources/weather.md): Source: MeteoSwiss, CC BY 4.0. The model labels postcode 4056 as the PulseShift production site; the provider's physical reference point is Novartis Campus Basel. Postcode 4031 is University Hospital Basel. The adapter uses hourly mean temperature, daily maximum temperature when available, weather symbols and snowfall codes; source coverage limits remain explicit.
- [Approved synthetic scenarios](scenarios.md): invented treatment, transport/process durations, Rhine delays and weather disruptions. The integrated walkthrough uses these inputs with the planning engine; it does not reuse authored feasibility results. Synthetic evidence and provider replay are separate screen modes.

## Integration limits

The application opens in Live mode and requests public weather and Rhine evidence. Live evidence refresh is explicit; navigation does not refresh it. Network, stale-data and forecast-coverage issues remain visible and are never filled with demo or replay data. Weather at both endpoint postcodes is used for courier legs; current road clearance remains a coordinator input. Snowfall blocks bicycles, cars are always available with one hour of preparation, and the 28°C reminder is advisory. For shipping, the current Basel gauge is used as a route-wide proxy under the team's simplifying assumption; the low-water delay mapping remains illustrative and is not a delivery-time forecast.

Demo mode is offline and uses the fixed synthetic treatment fixture. Its Rhine, outbound and return controls are independent. The Rhine low-water-to-delay mapping, local journey conditions, vehicle availability and travel times are labelled synthetic assumptions. Demo results are calculated by the same planning and recommendation engines as Live results, but they are not operational evidence. A material input change clears any prior confirmation; only an explicit user action confirms a plan.

## Tools and libraries

| What | Source | Licence / use |
|---|---|---|
| Codex (OpenAI) | https://chatgpt.com/codex | AI-assisted development tool |
| Streamlit | https://docs.streamlit.io/ | Apache-2.0; screen and interaction checks |
| Altair | https://altair-viz.github.io/ | BSD-3-Clause; timelines |
| pytest | https://docs.pytest.org/ | MIT; tests |
| Ruff | https://docs.astral.sh/ruff/ | MIT; formatting and lint |
| setuptools / wheel | https://setuptools.pypa.io/ / https://wheel.readthedocs.io/ | MIT; packaging |
