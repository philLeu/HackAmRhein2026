# Handoff: T6 Rhine adapter and replay

Status: done · Updated: 2026-10-03 · Branch: feat/t6-rhine-adapter · Owner: @philLeu

## Goal
Return contract-compatible Rhine observations from T2 replay and the selected
Basel source, with explicit validation, provenance and unavailable-data issues.

## State
Replay and live station observations implement RiverProvider.load(window).
T1 and T2 are merged. No shared interface or dependency changes are needed.

## Done
- Confirmed T2's five saved rows, units and unknown original retrieval time.
- Added RhineReplayProvider(capture_directory, maximum_observation_age).
- Added RhineObservationProvider(maximum_observation_age), with bounded pages,
  request timeout and injectable clock/transport for deterministic checks.
- Tested the real live endpoint: three readings returned with an explicit
  incomplete-window coverage issue. No live response was saved to the repo.
- Added tests for units/datum, timezone conversion, half-open windows,
  provenance, invalid/missing values, stale/future readings, gaps, duplicates,
  pagination limits, malformed JSON and partial retrieval failures.

## Next
1. One teammate reviews the PR; merge requires explicit approval.
2. T9 wires the provider into the app and links T2's source notes.
3. T9 supplies the observation freshness policy and replay evaluation clock.

## Decisions and limits
Water level is gauge height in metres above the documented 240 m datum.
Observations never establish future or whole-route navigation conditions.
No forecast parser, scheduling rule, source-file edit or app wiring is included.
T2's unknown original retrieval time remains an issue. Replay retrieved_at is
the local load time, not an invented original request or conversion time.
Report issues must remain visible to callers; T5 treats these as unconfirmed
evidence. No automatic replay fallback hides a live retrieval failure.

## Checks
The complete test suite passes (95 tests, including 26 T6 tests).
T6's formatting and lint checks pass.
Full-repo formatting/lint also detect existing weather.py formatting and
test_weather.py import ordering issues on main; those files belong to T7.

## Resume prompt
Review T6 on feat/t6-rhine-adapter. Read this handoff and tests/test_rhine.py;
for integration use the providers in src/treatment_planner/data/rhine.py.
