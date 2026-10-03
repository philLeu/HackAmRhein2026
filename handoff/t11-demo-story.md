# T11 demo story handoff

Status: in progress · Updated: 2026-10-03 · Branch: docs/t11-demo-story · Owner: @fhuelin

## Goal
Prepare a short rehearsal explaining the coordinator's problem, two changed
decisions, the open-data contribution and all simulated assumptions.

## State
T9 is merged. English speaker notes, exact operator cues, two slide texts and
jury answers are drafted in docs/demo-story.md. The story follows the integrated
app rather than obsolete authored fixture results. @fhuelin speaks and a teammate
clicks. Operator choice and two timed human rehearsals remain pending; dry runs are not
misrepresented as spoken rehearsals.

## Done
- Inspected current app, planning settings, source index, design and T9 checks.
- Verified baseline, low-water failure, +12h collection recovery, truck switch,
  hot-return mixed car plan and original unconfirmed provider-replay plan.
- Two automated screen dry runs passed; timings and their limits are recorded.
- Prepared source attribution, synthetic assumptions and concise jury answers.
- @fhuelin chose to speak while a teammate operates the app.
- Nine existing integration checks and strict documentation-path checks passed.

## Next
1. Review the draft with @fhuelin and choose the teammate click operator.
2. Perform two timed spoken rehearsals and record the actual times.
3. Coordinate fallback assets with T10; teammate review and explicit approval
   are required before merging the T11 PR.

## Files
- docs/demo-story.md: script, screen cues, slide texts and rehearsal record.
- docs/SOURCES.md and provider notes: source/licence authority, unchanged.
- docs/design.md and docs/scenarios.md: approved assumptions, unchanged.

## Known problem
GitHub whole-history privacy checks fail on a personal email in a historical
commit already on main. T11 must not weaken the guard or rewrite shared history
without team agreement. Keep any screenshots with private data outside Git.

## Resume prompt
Continue T11 on docs/t11-demo-story. Read docs/demo-story.md and this handoff.
Review the script with @fhuelin, record two actual spoken rehearsal times and
coordinate fallback with T10. Do not mark a human rehearsal completed based on
automated UI timings, and ask before merging the PR.
