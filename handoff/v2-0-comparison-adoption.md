# V2-0 comparison adoption handoff

Status: fixes applied; ready for re-review

## Scope

Review and correct the existing comparison improvements from `d5da04c` on a
local task branch based on `feat/v2-treatment-planner`. The shared release
branch and `app.py` were not changed.

## Changes

- Adopted the route sketches, plain pickup wording and expandable comparison
  details from Jana's existing comparison work.
- Corrected result wording so weather and route restrictions are not described
  as missed deadlines. A late result is reported only when a failed check has
  a negative deadline margin.
- Added a neutral status for non-deadline failures such as invalid collection
  timing; it no longer claims that a deadline was missed.
- Added a shortlist fallback that keeps one confirmed plan visible whenever
  the full generated set contains one, even when the heuristic examples fail.
- Added regression tests for the collection-timing label and the real planner
  scenario with outbound route snow and unavailable return car. The planner
  generates 16 candidates, including four confirmed alternatives, and the
  shortlist retains a confirmed car-outbound/bicycle-return plan.

## Verification

- Full suite: 143 passed.
- Ruff check and format check passed for the changed Python files.
- `git diff --check` passed.
- Strict `scripts/doc-check.sh` passed.

The repository-wide Ruff check still reports 12 pre-existing findings in the
interface skill templates, the Rhine notebook and weather replay processing;
none are in the files changed by this task.

## Integration notes

- Local branch: `feat/v2-0-comparison-adoption`.
- This task does not edit the shared decision log concurrently. Existing
  decision entries from the adopted comparison commit should be reviewed by
  the integration owner during application.
- After integration, comparison UI ownership transfers to V2-7 as specified
  in `docs/v2/plan.md`.

## Remaining V2 work

V2-5 (live weather and independent local-route overrides) remains blocked until
V2-3 shared contracts are integrated; V2-3 depends on V2-1 domain rules and
V2-2 screen/demo decisions. Start V2-5 after that contract handoff.
