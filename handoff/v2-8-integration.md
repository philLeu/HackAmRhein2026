# V2-8 integration

Status: implemented locally; automated verification passed; visual review pending
Branch: `feat/v2-8-integration`
Base: latest `feat/v2-treatment-planner` at `3c61251` (V2-7 merge)

## State

- Connected V2-4/5 evidence adapters, V2-6 recommendations and V2-7 guided UI through `app.py`.
- Kept Streamlit composition in `app.py`; plan/evidence wiring lives in
  `src/treatment_planner/v2_flow.py` and per-route summaries in
  `src/treatment_planner/route_summaries.py`.
- Live mode is the initial mode and refresh is explicit. Demo mode is offline and has independent synthetic Rhine, outbound and return controls.
- Live now checks MeteoSwiss forecasts at Novartis Campus Basel (4056) and University Hospital Basel (4031), asks for each road's cleared status, uses snowfall as the bicycle weather block, and assumes cars are available with one-hour preparation.
- The Live overview shows endpoint forecast temperature and condition symbols plus a Basel water-level bar on a 0–10 m scale. Ship delay uses the agreed uniform-Basel-level assumption and the illustrative 0/12-hour rule.
- Added application-flow regression checks in `tests/test_v2_flow.py`.
- Updated run instructions, sources and the V2 release checklist.

## Verification

Passed after the final refactor: 215 tests, Ruff lint and Ruff format check,
18 standalone weather-research tests, strict documentation check, and
`git diff --check`.
The Streamlit server is running at `http://127.0.0.1:8501`. Automated AppTest
checks cover all three chapters and the offline Demo. Interactive browser review
is still pending because the computer-use browser surface is unavailable here.

## Next

Visually inspect all three chapters in the opened browser, then prepare a
reviewable PR targeting `feat/v2-treatment-planner`; do not merge without
explicit approval.
