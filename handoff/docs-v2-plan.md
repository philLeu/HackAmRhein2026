# V2 release planning handoff

Status: done

## Goal
Save the agreed V2 planning proposal on feat/v2-treatment-planner, leaving main unchanged and pushing only the V2 branch.

## Done
- Added docs/v2/design.md with guided recommendations, live default, three route demo controls and graphical route summaries.
- Added docs/v2/plan.md with proposed owners, acceptance checks, dependencies and the exclusive V2 push workflow.
- Recorded the V2 direction in docs/decisions.md. No implementation code changed.
- Reviewed @janaaaaaaaa's origin/fix/readable-comparison-main at d5da04c: 139 tests, formatter, lint and documentation checks passed in an isolated snapshot. The screen was not visually verified.
- Updated the plan with V2-0 adoption, narrowed V2-7 scope, full-candidate ranking and regression checks. Existing presentation work is partial coverage, not completion of a V2 task.
- Reproduced a shortlist with zero confirmed choices despite four confirmed engine alternatives (outbound snow, return car unavailable), and weather failures described as deadline failures in Hot return and Snow. V2-0 addresses these before adoption; V2-6 replaces the heuristic.

## Next
- Confirm proposed owners and start V2-0, V2-1 and V2-2 in parallel with disjoint files.
- Carry out V2-0 review and fixes before adoption; this update only changes planning documents. Any PR merge requires explicit approval for that PR.
- Agree ranking definitions and screen behaviour before changing shared contracts.
- Use per-task handoff files for implementation progress.

## Open questions
Default goal, target injection-time penalties, delivery goal definition, risk score and tie-breaks remain for V2-1. Demo snow semantics, validity windows and reset behaviour remain for V2-2. Confirm comparison-screen ownership and the V2-0 to V2-7 handoff with @janaaaaaaaa and @Fhuelin.

## Resume prompt
Continue V2-1 from docs/v2/plan.md on feat/v2-treatment-planner. Read docs/v2/design.md and the branch restrictions. Do not change main or push any other branch.
