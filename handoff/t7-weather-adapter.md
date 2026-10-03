# Handoff: T7 Weather adapter and courier eligibility inputs

Status: done · Updated: 2026-10-03 · Branch: feat/t7-weather-adapter · Last owner: @janaaaaaaaa

## Goal
Adapt the investigated Basel forecast or labelled replay to the shared weather contract, preserving journey intervals and uncertainty.

## State
`WeatherReplayProvider` loads a saved T3 capture offline and clips it to requested journey intervals. It preserves hourly mean temperature separately from maximum temperature, maps documented snowfall states, and reports missing, stale and outside-horizon coverage explicitly. Its maximum forecast age is required at construction because T3 records that the team has not agreed a freshness policy.

## Done
- Added optional hourly-mean temperature evidence to the shared `WeatherWindow` contract, with the required decision line.
- Added an offline provider for saved forecast and synthetic capture directories.
- Added adapter checks for provenance, journey windows, snowfall aggregation, unknown/outside-horizon coverage, stale evidence and temperature semantics.
- `compileall`, real-capture and synthetic-replay smoke checks passed; `doc-check`, `hack-guard --staged` and `git diff --check` passed. Pytest and Ruff could not run because this checkout has no `.venv` and those tools are not installed system-wide.

## Next
- T9 must pass the team's chosen positive maximum forecast age when constructing the provider.
- The planning team must decide whether hourly mean is sufficient for the 30°C rule or provide a source with hourly maxima; until then MeteoSwiss evidence cannot confirm maximum-temperature eligibility.
- Request teammate review and prepare a PR; do not merge without explicit approval.
