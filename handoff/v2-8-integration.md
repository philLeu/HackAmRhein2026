# V2-8 integration handoff

Status: implementation in review · Branch: `feat/v2-8-integration` · Base: shared V2 commit `3458688`

## Done

- Connected the V2 navigation, Live/Demo switch, independent Demo route controls, planner, goal ranking, route summaries and explicit confirmation in `app.py`.
- Added `v2_flow.py` to build consistent evidence, plan and summary snapshots. Live mode uses current Rhine and MeteoSwiss providers without a simulated fallback. Demo uses the fixed fixture clock and applies Rhine, outbound and return conditions to actual planner checks.
- Unknown simulated Rhine height leaves ship alternatives unconfirmed. Material input, goal and mode changes invalidate confirmation. Navigation alone preserves it; Reset demo restores baseline.
- Updated end-to-end tests, README, source index, style guide and release checklist.
- Local verification: 210 tests passed; Ruff formatting and lint passed; strict documentation check and staged privacy guard passed.

## Next

1. Save the verified integration checkpoint.
2. Have one teammate check navigation, icons and narrow-screen layout in the running app.
3. Push this task branch and open a PR targeting `feat/v2-treatment-planner` for teammate review. Merge only after explicit approval for that PR.

Resume: Continue V2-8 from `handoff/v2-8-integration.md` on `feat/v2-8-integration`; finish checks and prepare the V2 task PR.
