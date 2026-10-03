# T4 domain scenarios

Status: approved by @fhuelin on 2026-10-03; awaiting teammate PR review. These examples are synthetic planning fixtures, not clinical guidance or observed journey durations. Shared constraints remain in [design.md](design.md); the fixture conventions below supply the agreed examples for T5 and T8 once T4 is merged.

## Approved demo conventions

| Rule | Demo convention |
|---|---|
| Shipment clock | The 10-day clock starts at ingredient-order placement; ingredient arrival at the factory must be at or before order + 240 hours. |
| Material readiness | Production starts only when both ingredients and the sample are at the factory. No extra ingredient release or unloading period in the demo. |
| Earliest preparation | Each preparation starts at or after the planning decision time. Preparation can overlap other events. A shipment switch is allowed only while departure is still in the future. |
| Manual route snow | Each route has its own status and entry time. At decision time an entry up to 6 hours old is current; older, missing or future-dated entries become unknown. Clear is a snapshot, not assurance of future conditions; future dispatches need a renewed route check and remain provisional until then. |
| Car availability | Explicit available / unavailable / unknown for each journey, independent of weather. Unknown prevents confirmation. Two legs do not automatically share one prepared car. |
| Journey durations | Rhine 144 hours (6 days) from order to factory arrival, including the initial 6 hours before departure; refrigerated truck 48 hours travel after 6 hours approval/preparation; bicycle 1 hour per leg; car 1 hour per leg. |
| Production | 18 hours processing after all required material is ready; waiting counts toward the 24-hour arrival-to-completion deadline. |
| Disruption | Low-water fixture adds 12 hours to Rhine arrival. This is a synthetic delay input, not a conversion from a measured water level. |

All intervals below use UTC on an invented fixture calendar. Let O = 2026-11-01 08:00Z, the ingredient order time. Nominal Rotterdam departure is O + 6h, original sample collection C is O + 144h, and the planning decision D is O. Preparations cannot start before D. All local routes and treatment identifiers are invented; use no patient or company records.

## Common checks and presentation

- Collection shift: 0 to 24 hours inclusive from C; advancing collection is outside the defined alternatives.
- Sample deadline: sample factory arrival <= actual collection + 12h.
- Production deadline: completion <= sample factory arrival + 24h, including waiting for ingredients.
- Injection deadline: injection <= production completion + 8h. Include a separate 1h hospital handling interval after return delivery.
- Ingredient deadline: factory arrival <= O + 240h under the approved clock convention.
- Bicycle eligibility: check the entire interval of each leg separately. Exactly 30°C passes the temperature rule; any value above 30°C, forecast snowfall during the interval, or existing route snow blocks it. Unknown/stale inputs or incomplete coverage leave it unconfirmed.
- Car: a separate 8h preparation interval for each leg, completed before dispatch, plus explicit availability. Car eligibility here assumes no other demonstrated car disruption.
- Result: confirmed only if every applicable check passes with adequate evidence; infeasible for a demonstrated failure; unconfirmed if there is no demonstrated failure but evidence is missing. Passing a time calculation alone does not confirm environmental eligibility.
- Deadline margin = deadline minus actual event time: negative fails, zero passes. Show each margin separately.

For confirmed replay examples, assume labelled synthetic weather covers both full journey intervals, no snowfall, 20°C, cars available, and route-clear checks renewed at dispatch. Show these assumptions alongside the result. Live forecasts outside their horizon cannot substitute for this fixture coverage.

## S1 Baseline

| Event | Start | End |
|---|---|---|
| Rhine ingredient travel | Nov 1 14:00 | Nov 7 08:00 |
| Sample collection and outbound bicycle | Nov 7 08:00 | Nov 7 09:00 |
| Production | Nov 7 09:00 | Nov 8 03:00 |
| Return bicycle | Nov 8 03:00 | Nov 8 04:00 |
| Hospital handling | Nov 8 04:00 | Nov 8 05:00 |

The 144h ingredient duration is order-to-arrival; the travel bar starts at departure. Expected: baseline confirmed under the stated fixture evidence. Collection shift 0h; sample margin 11h; production margin 6h; injection margin 6h; ingredient margin 96h.

## S2 Low water: keep, postpone, or switch shipment

Ingredient arrival shifts to Nov 7 20:00 (O + 156h).

| Alternative | Sample arrival | Production | Injection | Expected outcome |
|---|---|---|---|---|
| Keep collection and Rhine | Nov 7 09:00 | Nov 7 20:00 to Nov 8 14:00 | Nov 8 16:00 | Infeasible: 11h waiting + 18h processing = 29h; production margin -5h. |
| Postpone collection by 12h, keep Rhine | Nov 7 21:00 | Nov 7 21:00 to Nov 8 15:00 | Nov 8 17:00 | Confirmed with renewed evidence: collection shift 12h, production margin 6h, sample margin 11h, injection margin 6h. |
| Switch to refrigerated truck before departure, keep collection | Nov 7 09:00 | Nov 7 09:00 to Nov 8 03:00 | Nov 8 05:00 | Confirmed: approval/preparation Nov 1 08:00–14:00, truck travel Nov 1 14:00–Nov 3 14:00; ingredients wait at factory. |

Delayed Rhine ingredient margin is 84h; truck ingredient margin is 186h. These are alternatives, not automatically ranked recommendations. After Rotterdam departure, omit the truck switch and explain why it is unavailable. If the 6h approval cannot finish before the permitted departure, that switch fails; do not draw instantaneous replacement.

## S3 Hot return journey

Use S1 times; outbound journey stays at 20°C. Return forecast has a maximum of 30.1°C during Nov 8 03:00–04:00.

- Keeping both bicycle legs is infeasible: return temperature is above 30°C.
- Mixed plan: outbound bicycle, return car. Return preparation Nov 7 19:00–Nov 8 03:00 overlaps production; return travel Nov 8 03:00–04:00; handling to 05:00. Expected confirmed with car available; injection margin 6h.
- If preparation starts only at production completion, car dispatch is Nov 8 11:00, handling ends 13:00, and injection margin is -2h. Expected infeasible.
- Repeat at exactly 30.0°C with all other evidence unchanged: both bicycles pass. Repeat with 30.1°C confined to outbound only: prepare the outbound car Nov 7 00:00–08:00 and retain the return bicycle.

## S4 Snow and independent preparations

Use S1 dates. Forecast snowfall during outbound blocks its bicycle; manual snow present on the return route blocks its bicycle even when the return forecast has no snowfall.

| Event | Interval |
|---|---|
| Outbound car preparation | Nov 7 00:00–08:00 |
| Outbound car travel | Nov 7 08:00–09:00 |
| Production | Nov 7 09:00–Nov 8 03:00 |
| Return car preparation | Nov 7 19:00–Nov 8 03:00 |
| Return car travel and handling | Nov 8 03:00–05:00 |

Expected: two-car-leg alternative confirmed with both cars available and two distinct preparation events; same margins as S1. A clear route entry does not override forecast snowfall. With snow on only one route, retain the eligible bicycle on the other route. With unknown route snow and otherwise adequate weather, that bicycle plan is unconfirmed. An unavailable required car makes that alternative infeasible; unknown car availability makes it unconfirmed.

## S5 No feasible plan

Change low-water delay to +48h, so ingredient arrival is Nov 9 08:00 (O + 192h). Decision D is Nov 7 00:00, after Rotterdam departure, so truck substitution is unavailable. Weather and route evidence remain adequate, cars available.

Latest legal collection is Nov 8 08:00 (C + 24h), with factory arrival 09:00. Waiting until Nov 9 08:00 takes 23h; processing to Nov 10 02:00 adds 18h. Production elapsed is 41h and margin is -17h. Every earlier collection is worse; cars take the same travel time in this fixture. Expected: no feasible plan within the defined alternatives, despite ingredient arrival meeting the 10-day limit (48h margin). Explain the production deadline failure and the departure restriction.

## Boundary and uncertainty walkthroughs

| Case | Expected result |
|---|---|
| Collection at C + 24h | Collection constraint passes exactly; evaluate all other checks independently. |
| Collection at C + 24h + 1 minute | Fails collection constraint even if every later deadline passes. |
| Ingredient arrival exactly O + 240h / one minute later | Ingredient constraint passes / fails; this alone does not decide the whole plan. |
| Sample travel 12h / 12h + 1 minute | Sample arrival constraint passes / fails. |
| Production including waiting 24h / 24h + 1 minute | Production constraint passes / fails. |
| Return travel plus handling 8h / 8h + 1 minute | Injection constraint passes / fails; handling cannot be omitted. |
| Car preparation ends at dispatch / after dispatch | Preparation timing passes / fails. |
| Preparation would need to start before D | Infeasible; do not backdate preparation. |
| Current clear route entry exactly 6h old / older by one minute | Snapshot current / unknown under the approved freshness rule; a future dispatch still requires a renewed check. |
| Missing entry time, future-dated entry, or unknown route status | Bicycle eligibility unconfirmed. |
| Forecast covers outbound but stops before return arrival | Outbound can be checked; return bicycle eligibility unconfirmed. |
| Missing or stale weather, or missing Rhine input for the delay scenario | Affected alternative unconfirmed; explain the missing evidence and offer labelled replay. |

Provider-specific weather/Rhine freshness and timestamp semantics belong to T2/T3 source notes and T6/T7 adapters; these fixtures do not invent them. A route check is not a weather forecast. A missing input is not evidence of safe conditions. Show “no confirmed plan yet” when evidence is missing, distinct from “no feasible plan” when all supported alternatives demonstrably fail.

## Acceptance walkthrough

@fhuelin approved the conventions and [ui-sketch.md](ui-sketch.md). A teammate still needs to review S1–S5 and the sketch through the PR before merge. Accepted rules are recorded in docs/decisions.md and linked from docs/design.md. T5 can turn these examples into executable checks; T8 can render their events and reasons after T1 and T4 are merged.
