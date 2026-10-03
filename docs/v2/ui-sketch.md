# V2 guided screen sketch

Status: draft for @fhuelin review. This describes the proposed screen, not
implemented application behavior. Recommendation rules live in
[recommendation-rules.md](recommendation-rules.md).

## Screen structure

- Header: treatment planner title, Live/Demo mode, evidence freshness and the
  active planning clock. Always show whether inputs are simulated.
- Sidebar: Plan, Routes & conditions, Sources & assumptions. Preserve inputs
  and selection when moving between chapters; navigation alone does not
  invalidate confirmation.
- Plan: goal selector, recommendation with its decisive reason and timing,
  three concise route summaries, and explicit confirmation. Keep alternatives,
  check details and timelines in closed expandable sections.
- Routes & conditions: the same three route summaries with evidence and
  input controls available on demand. Keep route-specific inputs independent.
- Sources & assumptions: provider timestamps, coverage, missing/stale evidence,
  source attribution and model limitations. Retain context when navigating back.

## Plan hierarchy

1. Goal: Lower disruption risk by default; Injection timing and Ingredient
   delivery timing available beside it. Injection timing reveals the target
   date/time input in UTC.
2. Recommendation: a prominent summary card with transport choices, sample
   pickup, ingredient arrival and injection time. Explain the decisive score
   in one sentence and expose its calculation under Details.
3. Route summaries: Rotterdam → Production (ingredients), Hospital → Production
   (sample), Production → Hospital (finished treatment). Use the adopted route
   arrows and transport labels. Place production completion between sample
   arrival and treatment return in expanded timelines.
4. Confirm plan: enabled only for a selected confirmed candidate. A unique
   winner is preselected; co-winners require an explicit selection.

Keep **Original baseline**, **Recommended plan** and **Your confirmed plan**
distinct. Confirmation shows a persistent acknowledgement with the selected
plan and timestamp. Material input/evidence changes and goal changes clear
confirmation and recompute the recommendation, with a visible explanation.

## Exceptional states

- Tied leaders: show the tied group and its common score; prompt the coordinator
  to select before enabling confirmation. Preserve all alternatives on demand.
- No confirmed plan: show why and disable confirmation. Expand provisional
  alternatives separately without presenting them as recommended.
- Live unavailable: identify failed/missing coverage and offer an explicit
  switch to Demo. Do not substitute simulated inputs silently.
- Route summaries: Normal, At risk, Blocked or Unknown, with text and evidence.
  A possible delay is a supported estimate with units, or “Delay unknown”.

## Demo controls

Entering Demo reveals three route buttons at the top of every chapter:
Rotterdam → Basel, Hospital → Production, Production → Hospital. Each opens
only its route's controls; opening or cancelling a panel changes no inputs.
Use Apply to commit edits together, recompute plans and clear confirmation.
Keep simulated provenance and the affected journey interval visible.

Switching to Live removes demo overrides and clears a confirmed demo plan.
Returning to Demo begins from the labelled deterministic fixture rather than
silently restoring a previously confirmed plan.

Reset demo restores the full baseline: all route controls, the fixture clock,
the Lower disruption risk goal and the original target injection time. Clear
confirmation, selected alternatives and pending panel edits. Keep the current
navigation chapter; return the recommendation to its baseline state.

Local-route panels have separate controls for Forecast snowfall and Snow on
route. Snow on route uses Clear / Snow present / Unknown. Forecast snowfall
uses No / Yes / Unknown. Unknown is never interpreted as clear conditions.
Temperature states its statistic and unit: simulated maximum temperature (°C)
for the displayed journey interval; provider hourly means stay labelled as such.
Do not represent a provider mean as a maximum. Car availability remains an
independent route input and is not inferred from weather.

## Decisions pending

- Override validity: define explicit interval coverage after schedule changes.
- Demo clock: choose fixture anchoring and whether advancing it is allowed.

## Review walkthrough

Open Plan; inspect the default goal and route summaries; change goal; inspect
a tie; select and confirm; navigate to sources and back; change one route;
check confirmation clears; show no-confirmed and Unknown states; reset Demo;
switch to Live and inspect provider failure. Expanded details remain optional.

V2-0's comparison ownership transfers to V2-7 after adoption. V2-2 edits design
documents only and does not change comparison.py, app.py or shared contracts.
