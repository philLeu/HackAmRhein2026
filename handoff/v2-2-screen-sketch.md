# V2-2 screen sketch handoff

Status: ready for screen review · Owner: @fhuelin · Updated: 2026-10-03

## State
Local branch feat/v2-2-screen-sketch starts from latest shared V2 commit c77c0bf.
V2-0 and V2-1 are integrated. No implementation or shared contract changes.

## Done
- Read the adopted comparison, route inputs, V2 design and existing theme.
- Drafted docs/v2/ui-sketch.md and docs/v2/style-guide.md around the agreed
  dark control-room direction and V2-1 recommendation/tie rules.
- Built a local clickable preview under .hack/v2-2-preview (unpublished).
- Reset restores full baseline, goal/target and clock; clears confirmation.
- Forecast snowfall and existing route snow have separate controls.
- When journeys move, simulated conditions carry over with a small note and
  old/new intervals in details. Live/manual evidence keeps its own coverage.
- Demo clock stays fixed at the existing baseline fixture until reset.
- Added a review walkthrough and acceptance examples for V2-3/V2-7.

## Remaining
- Screen walkthrough review with the team, then integration approval.
- The clickable preview illustrates layout/transitions rather than computing
  recommendations; it is local and needs the preview server to be running.

## Next
Review the sketch, integrate approved documents, then start V2-3 contracts.
Keep this local task branch unpublished; push only the shared V2 release branch
after explicit integration approval.

## Decision entry queued for integration
- 2026-10-03 · Agree V2 guided screen, independent route controls, full-baseline
  reset, fixed fixture clock and labelled carry-over of simulated conditions
  when journeys move; details live in docs/v2/ui-sketch.md · @fhuelin · Affects:
  V2-2, V2-3, V2-7, V2-8 · Why: make the demo repeatable while preserving live
  evidence coverage, separate snowfall/route-snow meanings and confirmation.

## Resume prompt
Continue V2-2 on feat/v2-2-screen-sketch. Read this handoff and the two design
documents. All demo-control choices are settled; review the layout and prepare
integration into the V2 branch without pushing this local task branch.
