# T1 foundation handoff

Status: in progress · Updated: 2026-10-03 · Branch: feat/t1-foundation · Last owner: @philLeu

## Goal
A fresh clone starts with the README commands, shows a labelled synthetic treatment timeline and comparison, and passes the shared contract check.

## State
Started from main at c73e414 after the plan and T4 scenarios were merged. Shared models, synthetic providers/comparator and a Streamlit screen are implemented. Dependencies installed in the project .venv; requirements.txt generated without editable paths. Used the existing Python 3.12 fallback after offering pixi. Contract and app interaction tests pass (12 tests); fresh-copy and browser checks remain.

## Done
- Updated local main and created the task branch.
- Read the agreed T4 scenarios and screen sketch, shared interface guidance and existing decisions.
- Implemented timezone-aware inputs, evidence coverage, unknown states and provider/planner protocols.
- Displayed authored baseline, low-water and hot-return examples, including advance return-car preparation.
- Ran formatting and contract/app checks; all 12 tests pass.

## Next
1. Verify browser rendering and README instructions from a fresh copy.
2. Run final formatting/lint, privacy and documentation checks; commit, push and prepare a PR. Merge needs explicit approval and teammate review.

## Files
app.py; src/treatment_planner/; tests/test_contracts.py; project dependency manifest; README.md; docs/decisions.md.

## Open questions
Real providers, generated alternatives, full UI interactions and final integration remain later tasks. The dependency workflow remains adjustable if the team prefers pixi.

## Resume prompt
Continue T1 from handoff/t1-foundation.md on feat/t1-foundation. Read docs/plan.md, docs/scenarios.md and docs/ui-sketch.md. Preserve the interface boundary and keep all fixture comparisons labelled synthetic placeholders.
