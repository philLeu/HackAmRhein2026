# V2 release planning handoff

Status: done

## Goal
Save the agreed V2 planning proposal on feat/v2-treatment-planner, leaving main unchanged and pushing only the V2 branch.

## Done
- Added docs/v2/design.md with guided recommendations, live default, three route demo controls and graphical route summaries.
- Added docs/v2/plan.md with proposed owners, acceptance checks, dependencies and the exclusive V2 push workflow.
- Recorded the V2 direction in docs/decisions.md. No implementation code changed.

## Next
- Confirm proposed owners and start V2-1 and V2-2 in parallel.
- Agree ranking definitions and screen behaviour before changing shared contracts.
- Use per-task handoff files for implementation progress.

## Open questions
Default goal, target injection-time penalties, delivery goal definition, risk score and tie-breaks remain for V2-1. Demo snow semantics, validity windows and reset behaviour remain for V2-2.

## Resume prompt
Continue V2-1 from docs/v2/plan.md on feat/v2-treatment-planner. Read docs/v2/design.md and the branch restrictions. Do not change main or push any other branch.
