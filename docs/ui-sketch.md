# T4 comparison screen sketch

Status: layout and interaction approved by @fhuelin on 2026-10-03 and merged with T4. Timing fixtures and expected outcomes live in [scenarios.md](scenarios.md). T8 implements this sketch as reusable components in src/treatment_planner/ui/comparison.py, with the existing neutral theme in config/theme.toml; T9 owns app wiring. Integration instructions live in handoff/t8-comparison.md.

## Coordinator flow

1. Choose a labelled scenario/replay or available live inputs. Show planning decision time, original collection, order time and departure state.
2. Enter route snow separately for hospital → factory and factory → hospital: clear / snow present / unknown, with check timestamp. Enter car availability separately for each leg. Show stale status and any future route check required.
3. Compare alternatives with the same original collection and decision time. Inspect reasons and deadline margins before choosing.
4. Select a confirmed plan to view its full timeline. Unconfirmed and infeasible plans remain inspectable but cannot be presented as confirmed selections. Selection is a planning choice only; it books nothing.

## Simple screen sketch

```text
Treatment material-flow planner           [Synthetic replay ▼]
Decision time: …   Order: …   Rotterdam departure: pending/departed
Evidence: provider / issued at / coverage / replay or live
Assumptions and limitations [expand]

LOCAL ROUTE INPUTS
                    Outbound                    Return
Route snow          [unknown ▼]                  [unknown ▼]
Checked at          [date and time]              [date and time]
Car availability    [unknown ▼]                  [unknown ▼]
Evidence warnings: …

COMPARE ALTERNATIVES
Plan                  Result       Collection shift  Tightest margin
Rhine + bicycles      Infeasible   0h                -5h production
Rhine + later sample  Confirmed    12h               +6h production
Truck + bicycles      Confirmed    0h                +6h production
[Inspect plan ▼]       [Select confirmed plan]

DETAIL: selected/inspected plan
Reasons and missing evidence: …
Margins: ingredients … / sample … / production … / injection …

TIMELINE (one shared time axis, timezone shown)
Ingredients      [approval/prep] [travel] [available at factory]
Sample           collection | [outbound travel] [waiting]
Production                                      [processing]
Outbound car     [8h preparation, if used]
Return car                              [8h preparation, if used]
Hospital                                                [return] [1h handling] | injection
Deadline markers: ingredient / sample / production / injection

Footer: source attribution, coverage, manual checks, synthetic rules
```

The comparison rows illustrate S2; the generic timeline includes optional events and must display the inspected plan's actual intervals. Do not add absent preparation bars to bicycle plans. Show ingredient waiting separately from sample waiting where useful.

## Display requirements

- Use readable text labels for confirmed / infeasible / unconfirmed; status cannot rely on colour alone. Preserve visible reasons for every failed constraint.
- Make preparations, journeys, sample waiting, production and hospital handling separate events on a common axis. Distinguish long ingredient travel from short local intervals with an overview and a treatment-period detail view.
- Label manual, synthetic, replay and observed/forecast facts. Keep source issue/retrieval time distinct from validity and journey intervals.
- Show all margins, including zero and negative values. Name the binding deadline beside the tightest margin. Data-unknown results have no confirmed overall margin.
- If no alternatives pass, distinguish demonstrated failure (“No feasible plan”) from insufficient evidence (“No confirmed plan yet”). Keep alternative explanations visible.
- Update selected timeline and selection label together. When inputs change, clear the prior selection and request a new comparison; do not retain an obsolete confirmed state.
- Default unknown inputs to unknown. Clearly mark replay route-status entries as synthetic; never imply a forecast checks existing snow on the route.
- Keep visual values in T8's theme file. This task defines layout and interaction only.

## Review check

Walk through baseline, low water, hot return, snow and no feasible plan. Confirm that the coordinator can find the changed transport, separate preparations, 1h handling, deadline failure and missing evidence without reading code. @fhuelin approved this layout; subsequent component changes are reviewed through T8's PR.
