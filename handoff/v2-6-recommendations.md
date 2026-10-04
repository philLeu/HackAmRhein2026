# V2-6 alternative ranking and recommendation

Status: integrated into `feat/v2-treatment-planner`. The next-step notes below record the task handoff; current release status is in [the V2 release checklist](../docs/v2/release-checklist.md).
Owner: @philLeu
Branch: feat/v2-6-recommendations
Base: 65a2a19 on feat/v2-treatment-planner
Updated through: d0bd1bd (V2-4), merged without conflicts

## Done

- Added GoalRecommendationEngine implementing the existing shared contract.
- Added configured early/late weights from the agreed V2-1 rules.
- Ranking uses the full planner output and preserves co-winners in stable ID order.
- Failed/unconfirmed plans and supplied blocked/unknown route summaries are excluded.
- Missing score inputs produce an explicit explanation rather than a fabricated score.
- Added 24 tests covering agreed arithmetic, ties, hard-check precedence and real-planner disruptions.

## Verification

- Full application suite after incorporating V2-4: 204 passed.
- Ruff lint and format checks passed for both added Python files.
- Strict documentation check passed; whitespace check passed.
- Staged privacy guard and commit hooks passed.
- Initial full-suite weather failure was Windows checkout CRLF conversion: the
  existing fixture mutation uses LF byte strings. Restoring the CSV fixture bytes
  exactly as stored in Git resolved it, with no tracked weather change.

## Next

- Have a teammate review, then obtain explicit approval for that PR before merging.
- V2-7/V2-8 can consume the recommendation contract when this task is integrated.

## Integration contract

V2-8 calls GoalRecommendationEngine().recommend(plans, goal, target_injection,
route_summaries). Scores are best-first; plan IDs stabilise display order without
breaking ties. Empty winner IDs mean no recommendation; multiple IDs mean a tie.
All original candidates remain with the caller for inspection. No UI or app wiring
is included in V2-6.

Only supplied, evidence-backed At risk local-route warnings are counted. Omitted
summaries contribute no explicit warnings and do not assert route safety; confirmed
planner checks remain the eligibility authority. V2-8 should supply all per-plan
route summaries. The >=28°C weather reminder is not a ranking warning by itself.

## Resume prompt

Continue V2-6 on feat/v2-6-recommendations. Read docs/v2/recommendation-rules.md
and this handoff, finish verification, then prepare the PR into
feat/v2-treatment-planner. Merge only after explicit approval.
