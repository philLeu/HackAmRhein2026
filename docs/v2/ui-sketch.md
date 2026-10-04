# V2 guided screen sketch

Status: approved by @fhuelin. This describes the proposed screen, not
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
4. Confirm plan: enabled only for a selected confirmed candidate. The first
   winner is preselected for inspection, including when several plans tie.
   Tied co-winners remain marked as recommended and can be selected instead.

Keep **Original baseline**, **Recommended plan** and **Your confirmed plan**
distinct. Confirmation shows a persistent acknowledgement with the selected
plan and timestamp. Material input/evidence changes and goal changes clear
confirmation and recompute the recommendation, with a visible explanation.
When a new recommendation is available, reset “Plan to confirm” to its first
winner; do not keep the previous widget value after settings change.

## Exceptional states

- Tied leaders: show the tied group and its common score with the first co-winner
  selected for inspection. Preserve all alternatives on demand; require an
  explicit confirmation action.
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

If a plan moves a journey, carry its simulated conditions to the new journey
interval. Show “Demo conditions carried over from the previous trip time”
beside the affected route, with the old and new intervals in expanded details.
Retain the originally entered values and their simulated provenance; carrying
Unknown values forward does not make them known. Carry-over does not establish
live-provider coverage or renew a real/manual observation. Recompute hard
checks for the new interval and invalidate previous confirmation. Reset clears
carry-over notes; explicitly applying new conditions replaces that route's
carry-over note. Keep each route's values independent.

## Demo clock

Use the existing baseline fixture: decision clock 01.11.2026 · 08:00 UTC and
original injection target 08.11.2026 · 05:00 UTC. The demo clock stays fixed;
page reruns, navigation and elapsed presentation time do not advance it.
Reset restores these values. Entering Demo starts the baseline with no prior
confirmation. Show the clock and “Simulated” prominently; actual provider
retrieval timestamps remain actual timestamps, not the demo clock.

In Live, use the actual planning time and provider evidence coverage. Refresh
evidence explicitly without silently resetting the treatment inputs; material
evidence changes invalidate confirmation. Navigation alone does not refresh
evidence or advance a simulated clock.

## Review walkthrough

Open Plan; inspect the default goal and route summaries; change goal; inspect
a tie; select and confirm; navigate to sources and back; change one route;
check confirmation clears; show no-confirmed and Unknown states; reset Demo;
switch to Live and inspect provider failure. Expanded details remain optional.

V2-0's comparison ownership transfers to V2-7 after adoption. V2-2 edits design
documents only and does not change comparison.py, app.py or shared contracts.

## Acceptance examples for V2-3 / V2-7

| Action | Expected visible result |
|---|---|
| Open Live without adequate evidence | Missing/failed evidence is visible; no silently simulated recommendation. |
| Enter Demo | Fixed baseline clock, default risk goal, original target and labelled synthetic inputs; no confirmation. |
| Change only outbound snow | Return and ingredient inputs retain their values; recommendation recomputes and confirmation clears. |
| Move a journey beyond its old demo interval | Simulated conditions carry over with a small note; details show old/new intervals. |
| Change a Live journey beyond source coverage | Unknown evidence remains visible; the demo carry-over rule is not applied. |
| Equal top goal scores | First co-winner is displayed with tied alternatives available; confirmation still requires the explicit confirm action. |
| Confirm then open Sources | Confirmation persists through navigation and supporting details remain optional. |
| Reset Demo from Routes | Full baseline restored, confirmation and carry-over notes cleared; Routes chapter stays open. |
| Switch Demo to Live | Demo overrides removed, confirmation cleared, live evidence/coverage shown. |
