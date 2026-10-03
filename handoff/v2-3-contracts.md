# V2-3 shared contracts

Status: implementation done; preparing PR for teammate review

## Done

- Added shared goal, evidence mode and route status enums without changing V1 models.
- Added independent ingredient, sample and treatment demo overrides. Snow forecast, existing route snow and car availability remain separate.
- Added per-plan route summaries with explicit evidence, possible delay and simulated carry-over interval.
- Added score and recommendation result models that retain co-winners and support no-recommendation outcomes.
- Added the recommendation engine protocol and contract checks; recorded the interface decision.

## Component boundaries

- V2-4 owns Rhine evidence and the ingredient override adapter in the Rhine files listed in docs/v2/plan.md.
- V2-5 owns weather evidence and independent local-route overrides in its weather files.
- V2-6 owns scoring, ranking and recommendation in recommendations.py; it consumes all candidate plans and per-plan route summaries, and returns RecommendationResult.
- V2-7 owns route summary presentation and controls in the UI files listed in the plan. It passes typed overrides through the integration layer; it does not rank plans.
- V2-8 owns app.py wiring, mode/confirmation state and end-to-end checks. It coordinates adaptation of typed overrides into existing request/environment inputs and builds per-plan route summaries for ranking and UI.

## Next

- Have one teammate review the contract and its meaning against the agreed V2-1 rules and V2-2 screen sketch.
- Review the PR targeting feat/v2-treatment-planner with one teammate, then merge after explicit approval.
- V2-4–V2-7 can then implement against these models. If a contract needs a further change, add its decision line in the same commit.

## Resume prompt

Review the feat/v2-3-contracts PR into feat/v2-treatment-planner against docs/v2/recommendation-rules.md and docs/v2/ui-sketch.md. Run contract checks, then seek explicit approval before merging.
