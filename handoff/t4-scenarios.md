# Handoff: T4 domain scenarios and screen sketch

Status: in progress · Updated: 2026-10-03 · Branch: docs/t4-scenarios · Last owner: @fhuelin

## Goal
Provide baseline, low-water, hot return, snow and no-feasible-plan examples with expected outcomes and a simple screen sketch, reviewed by the team.

## State
Scenario and layout proposals are written. Proposed durations and unresolved domain conventions need @Fhuelin and team agreement before T4 is done. T1 is absent from the local main checkout; T8 cannot yet use a shared interface. T11 depends on T9.

## Done
- Read task ownership, agreed design and decisions.
- Drafted five scenarios with explicit timelines, failure reasons and deadline margins.
- Included strict temperature, collection shift, timing and uncertainty boundaries.
- Drafted comparison layout, manual route/car inputs and selection behaviour.

## Next
1. Review proposed conventions in docs/scenarios.md and screen sketch with @Fhuelin.
2. Confirm with a teammate; record accepted rules in docs/decisions.md and reconcile docs/design.md. Do not mark draft proposals as agreed defaults.
3. Run privacy and documentation checks; share a PR for teammate review. Merge only after explicit approval for that PR.
4. After T1 and T4 merge, start T8 in a fresh task branch using the actual shared interface. T11 waits for T9.

## Files
- docs/scenarios.md: proposed domain fixtures and acceptance cases.
- docs/ui-sketch.md: comparison layout and coordinator flow.
- handoff/t4-scenarios.md: task state; docs/plan.md remains unchanged.

## Decisions made
No new domain or visual decision accepted. Draft values are labelled proposals.

## Open questions / problems
- Approve or amend clock origin, readiness, earliest preparation, snow freshness, car availability and synthetic durations.
- Approve the layout; teammate confirmation is still required.

## Resume prompt
> Continue T4 from handoff/t4-scenarios.md on docs/t4-scenarios. Review the proposal with @Fhuelin, starting with Next step 1. Do not start T8 until T1 and T4 are merged or explicit permission to use sample contracts is given.
