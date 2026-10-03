# Handoff: T4 domain scenarios and screen sketch

Status: in progress · Updated: 2026-10-03 · Branch: docs/t4-scenarios · Last owner: @fhuelin

## Goal
Provide baseline, low-water, hot return, snow and no-feasible-plan examples with expected outcomes and a simple screen sketch, reviewed by the team.

## State
@fhuelin approved the scenario conventions and layout on 2026-10-03. The design and decision log reflect that approval. [PR #2](https://github.com/philLeu/HackAmRhein2026/pull/2) is open for teammate review. That review remains before T4 is done and merge needs explicit approval for this PR. A fresh fetch confirmed T1 is absent from origin/main; T8 cannot yet use a shared interface. T11 depends on T9.

## Done
- Read task ownership, agreed design and decisions.
- Drafted five scenarios with explicit timelines, failure reasons and deadline margins.
- Included strict temperature, collection shift, timing and uncertainty boundaries.
- Drafted comparison layout, manual route/car inputs and selection behaviour.
- Recorded owner approval and reconciled design and decision log.
- Verified fixture arithmetic, whitespace and strict documentation paths; commit and push privacy checks passed for the approved documents.
- Pushed the work branch and opened PR #2 for teammate review.

## Next
1. Obtain a teammate review on PR #2 of S1–S5 and the screen sketch.
2. Address teammate feedback; mark T4 done once the teammate confirms the walkthrough and layout.
3. Merge only after explicit approval for PR #2; owner approval of the proposal is not merge approval.
4. After T1 and T4 merge, start T8 in a fresh task branch using the actual shared interface. T11 waits for T9.

## Files
- docs/scenarios.md: owner-approved domain fixtures and acceptance cases.
- docs/ui-sketch.md: comparison layout and coordinator flow.
- docs/design.md, docs/decisions.md: reconciled scope and accepted conventions.
- handoff/t4-scenarios.md: task state; docs/plan.md remains unchanged.

## Decisions made
Owner-approved domain conventions and screen layout are linked in docs/decisions.md. Teammate review remains; no shared interface changed.

## Open questions / problems
- Teammate confirmation of the scenario walkthrough and layout is still required.
- T1 is not on origin/main; T8 waits for T1 and T4. T11 waits for T9.

## Resume prompt
> Continue T4 from handoff/t4-scenarios.md on docs/t4-scenarios, starting with Next step 1. @fhuelin approved the proposal; teammate review and PR-specific merge approval remain. Do not start T8 until T1 and T4 are merged or explicit permission to use sample contracts is given.
