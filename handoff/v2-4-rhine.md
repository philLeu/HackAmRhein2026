# Handoff: V2-4 live Rhine and ingredient override

Status: implementation ready for review · Branch: `feat/v2-4-rhine` · Base:
`feat/v2-treatment-planner` at `65a2a19`

## Delivered

- Added a Rhine component adapter that fetches live observations and the current
  BAFU forecast by default. It does not fall back to saved replay or simulation.
- Added explicit `available`, `missing`, `stale`, and `outside forecast horizon`
  states for the requested ingredient journey. The requested interval is never
  extended beyond forecast coverage.
- Added a typed, synthetic-provenance Basel gauge override for Demo mode.
- Applied the agreed T4 12-hour low-water delay through an explicitly
  documented demo-only threshold mapping. Missing simulated gauge input keeps
  delay unknown; this mapping is not a real delivery prediction.
- Documented source limits, attribution, freshness policies and the simulated
  delay in `docs/sources/rhine.md`.
- Live smoke check: 573 observations and 118 forecast points retrieved; the
  five-day sample interval was correctly marked outside the returned horizon.

## Review and next integration

V2-8 should pass the current ingredient journey window to
`load_live_rhine_evidence()` in Live mode. In Demo mode it should use
`build_demo_rhine_override()` and `apply_demo_rhine_delay()`, preserving the
synthetic provenance and interval. Keep the UI distinction between gauge
assessment and simulated delivery delay. No shared interface or `app.py`
changes were made here.

Verification: all 180 tests pass; Ruff lint and format checks and the strict
documentation check pass. The live endpoint smoke check was also successful.
Local fixtures cover offline and source-failure states.
