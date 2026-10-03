# Handoff: T8 timeline and comparison screen

Status: done · Updated: 2026-10-03 · Branch: feat/t8-comparison-screen · Last owner: @fhuelin

## Goal
Render shared sample candidate plans, preparation/travel/production/handling, reasons, margins, manual route inputs and explicit selection.

## State
T1 and T4 are merged into main. Reusable Streamlit components are implemented and checked against their contracts. Implementation is done; PR review and merge remain. app.py and shared contracts remain owned by T9/T1; the foundation app remains read-only until T9 integrates this component.

## Done
- Confirmed prerequisites and created a separate branch from origin/main.
- Implemented route input collection, comparison, evidence, timelines and selection invalidation.
- Preserved explicit unknowns and supplied plan results; no scheduling rules calculated in the UI.
- All 18 tests passed, including selection persistence/invalidation, negative/zero margins, unknown inputs and deadline-marker rendering. Formatter and linter passed.
- Browser preview verified authored baseline and hot-return alternatives, explicit selection and return-car preparation overlapping production. Local preview is at http://127.0.0.1:8502 while its server runs.

## Next
1. Open the checked branch's PR and obtain teammate review; merge only after explicit approval for that PR.
2. T9 integrates the component using the instructions below, after its dependencies merge.

## Integration for T9
1. Call render_route_inputs(request) to obtain a TreatmentRequest with per-leg manual inputs.
2. Compute alternatives in the engine outside the UI component. Retain that request and environment as comparison snapshots.
3. Call render_comparison(plans, request=current_request, environment=current_environment, compared_request=snapshot_request, compared_environment=snapshot_environment). Its return is the selected CandidatePlan or None.
4. Changes invalidate selection; recompute before presenting results as current. T1's comparator rejects edited inputs, so it cannot recalculate route edits.

## Files
- src/treatment_planner/ui/comparison.py: reusable components and display helpers.
- src/treatment_planner/ui/route_inputs.py: independent manual fields and stable entry provenance.
- src/treatment_planner/ui/timeline.py: supplied UTC intervals and deadline markers.
- config/theme.toml: existing neutral colours plus deadline-marker colour.
- tests/test_comparison.py: coordinator interaction and rendering checks.
- handoff/t8-comparison.md: status and integration instructions.

## Open questions / limitations
- T1 examples supply margins without exact deadline timestamps; markers render only when checks supply timestamps.
- No app.py wiring in T8. A local ignored harness will preview the component.

## Resume prompt
> Continue T8 review from handoff/t8-comparison.md on feat/t8-comparison-screen. Implementation and tests are done. Start with Next step 1; keep app.py and interfaces.py unchanged.
