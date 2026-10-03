# T5 planning handoff

Status: done · Updated: 2026-10-03 · Branch: feat/t5-planning · Last owner: @philLeu

## Goal and state

Implement the agreed T4 alternatives with shared inputs/results, deadlines,
preparations and explicit unknown evidence. Built from main at 7f2b014 after
T1 and T4 merged. Implementation is complete; teammate PR review and explicit
merge approval remain. App registration belongs to T9. Publication is pending:
automatic approval review rejected the branch push because it requires explicit
authorization for the code payload and GitHub destination. No PR is open yet.

## Done

- Added config/planning.json with approved synthetic domain values and source note.
- Added PlanningComparator implementing the shared PlanComparator signature;
  contracts are unchanged. Tests register the real implementation within the
  T5-owned test file, preserving T1's test ownership.
- Evaluated all shipment/per-leg mode combinations at original collection,
  latest legal collection, delay/alignment and first deadline-recovery times.
  Returned alternatives are inspectable and unranked; this is a finite demo
  search, not a complete continuous-time/weather optimisation.
- Omitted truck switches after departure; an earlier decision with insufficient
  approval time yields an infeasible truck alternative with the reason.
- Included distinct car preparations, ingredient waiting, processing, travel
  and hospital handling, plus independent deadline/preparation margins.
- Car preparations never start before the decision. A preparation that cannot
  finish by planned dispatch fails, with delayed travel shown for inspection.
- Tested S1–S5, 30°C versus 30.1°C, inclusive deadlines, preparation boundaries,
  missing/stale/incomplete weather, manual freshness, independent car availability,
  failure-over-unknown priority, protocol compatibility and input immutability.
- Existing screen/contract tests continue to pass. No dependency added.

## Integration usage

Load domain settings with `load_settings(Path("config/planning.json"))` from
the repository root; callers elsewhere supply their own absolute config path.
Use `PlanningComparator(weather_location=adapter_location).compare(request,
environment, settings)`. Windows with location labels equal to CourierLeg.value
are checked only for that leg; otherwise the explicit common location is used.

Default planning preserves missing Rhine evidence and future route renewal as
unconfirmed. Adapter report issues propagate; provider freshness remains an
adapter responsibility. A river reading supports input availability only: the
configured delay remains a labelled synthetic assumption, never a conversion
from a gauge reading or proof of route navigability.

For the approved T4 walkthrough only, `PlanningComparator(t4_replay=True)`
explicitly assumes synthetic Rhine delay evidence and renewed clear route checks
at dispatch. Route renewal applies only to SYNTHETIC/REPLAY manual provenance
with a current decision-time entry; missing/stale/future entries stay unknown.
Weather still needs complete, known, issue-free journey coverage. The assumptions
are included in every replay CandidatePlan. Do not enable replay for live inputs.

The `evaluate` method checks one explicit alternative, including illegal shifts
for boundary testing. Its `prepare_return_at_completion=True` option reproduces
T4's late-return-preparation counterexample. Generated alternatives prepare ahead.

## Next

1. Obtain push/PR authorization, publish feat/t5-planning, then have a teammate
   review S1–S5 results; merge only with explicit approval for that PR.
2. T9 connects the comparator/config to the screen and provider inputs, displaying
   assumptions and reasons, and distinguishing no confirmed plan from all
   generated alternatives being infeasible.
3. Future search expansion can include provider weather transition times; the
   current finite alternative set should not be described as exhaustive optimisation.

## Verification

54 tests passed (42 new T5 checks and 12 foundation checks). Ruff formatting,
lint, documentation paths and whitespace checks passed using the project's
existing Python 3.12 development environment and the task worktree on PYTHONPATH.

## Resume prompt

Continue T5 PR review on feat/t5-planning from handoff/t5-planning.md. Keep shared
interfaces and app wiring unchanged; use docs/scenarios.md for domain acceptance.
