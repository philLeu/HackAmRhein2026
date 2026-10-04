# V2 recommendation rules

The planner recommends only from plans whose required checks pass with
adequate evidence. Constraint failures stay infeasible; missing, stale or
incomplete evidence stays unconfirmed. A strong score cannot override either.
When no plan is confirmed, show no recommendation, explain the failed or
missing checks, and let the coordinator open provisional alternatives.

## Goals

The coordinator chooses one goal. The default is **Lower disruption risk**.

| Goal | Primary comparison | Explanation |
|---|---|---|
| Injection timing | Minimise weighted deviation from the coordinator's target injection time: 1 point per minute early and 2 points per minute late. | Show early/late deviation and weighted score. A missing target prevents ranking under this goal and requests a target. |
| Ingredient delivery timing | Earliest confirmed ingredient arrival at production. | Show the arrival timestamp and transport. Do not substitute sample or completed-treatment arrival. |
| Lower disruption risk (default) | Maximise the smallest remaining margin among ingredient arrival, sample arrival, production completion and injection deadlines. | Show the limiting deadline and its margin. Preparation completion remains a mandatory check, but its zero margin at planned dispatch does not enter this comparison. |

For lower disruption risk, when the smallest deadline margins tie, prefer the
plan with fewer local routes carrying a specific, evidence-backed,
non-blocking risk warning. Count each affected route at most once. Do not
invent points, likelihoods, source warnings or safety-buffer thresholds.

All stated goal scores are compared only after the hard-check filter. If plans
tie on the selected goal score (including the existing risk-warning tie-break),
apply the route-mode preferences lexicographically: first prefer Rhine ship
over truck; when ingredient modes tie, prefer the plan with more bicycle legs
than car legs. If both shipment mode and bicycle count tie, keep the plans tied.
The overview displays the first winner for inspection after both ranking stages,
including when several plans remain tied. The tie stays visible and other
co-winners remain selectable; confirmation still requires the coordinator.

## Route summaries

Assign each route one main status and show the evidence or check that supports it:

- **Blocked:** a demonstrated hard route-eligibility failure. Keep its reason
  visible. A plan using that route cannot be confirmed.
- **Unknown:** no demonstrated hard failure, but required route evidence is
  missing, stale or outside coverage. Never score it as safe or as zero risk.
- **At risk:** route checks pass with adequate evidence, and the source supplies
  a specific warning that does not block the selected mode. State the warning
  and its source. Do not label missing evidence or a failed check At risk.
- **Normal:** required evidence is adequate, checks pass and no specific
  non-blocking warning is present.

A demonstrated block takes precedence as the main label if other evidence is
also missing; include the missing-evidence issue in the route details. A failed
preparation/deadline check remains visible as a check result even if the route
itself is Normal. Use text as well as colour and icons.

## Expected examples

Use the UTC fixture values in [scenarios.md](scenarios.md) and existing
[T4 scenarios](../scenarios.md); none describes clinical or observed logistics.
The recommendation reason names the primary objective and any goal or route-mode
tie-break used.

- For the baseline fixture with the target set to its original injection time,
  schedules reaching that target score zero. Preserve equivalent co-winners.
- Under the 12-hour synthetic low-water delay, a 12-hour collection shift can
  recover the original production/injection timing; a pre-departure truck can
  bring ingredients earlier. Delivery timing favours the earliest confirmed
  ingredient arrival. If another goal gives equal scores, preserve the tie.
- Under the hot-return fixture, return bicycles that fail the heat rule are
  excluded. Recommend only confirmed car-return alternatives; show all tied
  best scores and their preparation intervals.
- In the no-feasible-plan or missing-evidence examples, show no recommendation
  and distinguish demonstrated failures from unknown checks.

## Decision record

These agreed V2-1 rules are recorded in [the decision log](../decisions.md).
