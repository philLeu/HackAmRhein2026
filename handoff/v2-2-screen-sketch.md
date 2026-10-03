# V2-2 screen sketch handoff

Status: done · Owner: @fhuelin · Updated: 2026-10-03

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

## Review and integration
- @fhuelin approved the sketch and integration into the shared V2 branch.
- The shared decision entry is recorded in docs/decisions.md.
- Privacy and documentation hooks check the commit before integration.

## Limits
- The clickable preview illustrates layout/transitions rather than computing
  recommendations; it is local and needs the preview server to be running.

## Next
V2-3 can define shared contracts from the approved rules and screen sketch.
Keep this local task branch unpublished; push only the shared V2 release branch
after explicit integration approval.

## Resume prompt
Continue V2-3 from docs/v2/plan.md on the latest V2 release branch. V2-1 and
V2-2 are approved; read their rule/sketch documents and handoffs before defining
contracts. Keep task branches local and push only the shared V2 release branch.
