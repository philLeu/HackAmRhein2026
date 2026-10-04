# Live weather recovery

Status: fixed on `feat/demo-polish` · Updated: 2026-10-04

## Goal
Restore live Basel weather when today's MeteoSwiss item contains only a forecast cycle timestamped in the future.

## State
The current item returned a complete cycle at 12:00 UTC while retrieval was at 11:38 UTC. The provider correctly refused to treat future-dated evidence as current. It now tries yesterday's latest complete cycle if the current cycle is future-dated, and retains the real issue timestamp so the 24-hour freshness rule still applies.

The comparison queries a broad weather envelope spanning all candidate plans. A coverage note for the envelope's latest out-of-horizon intervals used to mark every bicycle journey unknown, including earlier fully covered rides. Bicycle checks now rely on the selected candidate's own weather windows; source failures and stale evidence remain blocking.

## Verification
Direct live retrieval from MeteoSwiss returned weather windows with source time `2026-10-03T23:00:00+00:00` and no issues.
After the candidate-window fix, a full live planning reproduction with both roads set to clear produced 12 confirmed bicycle plans and two recommended winners.

## Files
- `src/treatment_planner/data/weather_live.py`: fallback to the previous daily item only when the selected cycle is future-dated.
- `src/treatment_planner/planning.py`: evaluate forecast coverage per candidate journey.
- `docs/sources/weather.md`: documents cycle selection and journey-specific coverage.

## Follow-up: recommendation selector refresh
The Plan-to-confirm selector must reset its keyed Streamlit widget state to the first winner whenever the recommendation signature changes. Implemented in `src/treatment_planner/ui/recommendation.py`; specified in `docs/v2/ui-sketch.md`.
