# Handoff: T7 Weather adapter and courier eligibility inputs

Status: in progress · Updated: 2026-10-03 · Branch: feat/t7-weather-adapter · Last owner: @janaaaaaaaa

## Goal
Adapt the investigated Basel forecast or labelled replay to the shared weather contract, preserving journey intervals and uncertainty.

## State
`WeatherReplayProvider` loads a saved T3 capture offline and clips it to requested journey intervals. It preserves hourly mean temperature separately from maximum temperature, maps documented snowfall states, and reports missing, stale and outside-horizon coverage explicitly. Its maximum forecast age is required at construction because T3 records that the team has not agreed a freshness policy.

## Done
- Added optional hourly-mean temperature evidence to the shared `WeatherWindow` contract, with the required decision line.
- Added an offline provider for saved forecast and synthetic capture directories.
- Added adapter checks for provenance, journey windows, snowfall aggregation, unknown/outside-horizon coverage, stale evidence and temperature semantics.

## Next
- Run focused tests, formatter, full test suite and privacy/doc checks.
- Review whether the planning team accepts maximum temperature as the eligibility measure or wants a source/rule adjustment; hourly means cannot establish maxima.
- Ask for review and prepare a PR; do not merge without explicit approval.
