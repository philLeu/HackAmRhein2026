# Treatment material-flow planner

Team: @philLeu, @Fhuelin, @luapreta-cloud, @janaaaaaaaa · Track: Manufacturing · Updated: 2026-10-03

Status: Agreed demo flow, constraints, task split and Python/Streamlit. T4 scenario conventions and screen layout approved by @fhuelin, awaiting teammate PR review; source integrations remain to be finalised. All treatment timing rules below are team-defined demo assumptions.

## Problem
A production coordinator plans one individual treatment whose ingredients are ordered from Rotterdam. Rhine and local weather disruptions can invalidate its logistics and production schedule. The demo baseline is an invented manual planning workflow, not a documented hospital or factory process.

## What we build
A timeline planner that compares feasible alternatives for ingredient delivery, hospital-to-factory sample transport, production, and factory-to-hospital treatment transport and injection. The coordinator chooses a plan; the prototype does not book transport or make clinical decisions.

### Demo flow
1. Show a feasible baseline using Rhine shipping and bicycle couriers for both local legs.
2. Replay a low-water disruption and explain the ingredient delivery delay using an explicit simulation rule.
3. Compare keeping the baseline, postponing sample collection, and switching the ingredient shipment to a refrigerated truck before departure.
4. Add a local weather forecast that blocks a bicycle leg. Compare plans that prepare a car in advance for each affected journey, including mixed bicycle/car plans.
5. Show timing, preparation intervals, deadline margins, changed transport and assumptions for each alternative. Mark failed constraints and say "no feasible plan" when necessary.
6. The coordinator selects an alternative and sees the revised timeline.

## Domain knowledge that matters
| Rule | Confirmed demo constraint |
|---|---|
| Ingredient order | Separate order for this treatment from Rotterdam to Basel |
| Rhine shipment | Normal duration 5–7 days; maximum 10 days. Clock origin and baseline fixture are specified in docs/scenarios.md |
| Ingredient transport switch | Refrigerated truck, before departure from Rotterdam only; 6 hours approval and preparation |
| Sample collection | May move later by at most 24 hours from its original planned time |
| Sample arrival | Factory arrival within 12 hours of collection |
| Production completion | Within 24 hours of sample arrival, including waiting |
| Injection | Within 8 hours of production completion |
| Hospital handling | Configurable; default 1 hour after return delivery, inside the injection deadline |
| Bicycle availability | Blocked by forecast snowfall during the journey, snow already on the route, or temperature strictly above 30°C; evaluate each journey separately |
| Existing route snow | Coordinator-entered status per local route: clear / snow present / unknown. Snow present blocks bicycle transport; unknown leaves bicycle feasibility unconfirmed |
| Car preparation | 8 hours separately for each journey, completed before dispatch; may begin in advance based on forecasts |

T4's approved [scenario conventions](scenarios.md) specify shipment clock origin, material readiness, earliest preparation, manual snow freshness, explicit car availability and synthetic durations. Expected outcomes and boundary cases live there. The approved [screen sketch](ui-sketch.md) defines comparison, evidence display and selection behaviour.

Preparation is separate from travel. The return car's preparation must start before production finishes to leave room for travel and hospital handling. Exact preparation lead time depends on the planned dispatch time. Changing ingredients to a truck is not an instantaneous response; domain approval and preparation time must appear in the plan.

## Data
| Input | Source | Permission | Real or synthetic |
|---|---|---|---|
| Rhine conditions | Open source to research and verify | Licence pending | Real observations, with labelled replay for the demo |
| Basel weather | Candidate: MeteoSwiss local forecasts; see docs/SOURCES.md | CC BY 4.0 with attribution; integration pending | Real forecasts, with labelled replay for the demo |
| Treatment, routes and durations | Team-defined scenario | Synthetic, no patient or company records | Synthetic |
| Availability, cooling faults, approval and preparation | Explicit scenario inputs, not inferred from weather or river levels | Synthetic | Synthetic |
| Existing snow on courier routes | Coordinator-entered clear / snow present / unknown for each route, with entry timestamp | Manual demo input; no personal data | Synthetic route status for the demo |

Open data supplies environmental signals. Delivery-delay estimates, travel times and transport availability are separate demo assumptions, not facts established by those signals. Record verified providers, licence, timestamps and replay provenance in docs/SOURCES.md before using them.

## How it's built
Python with Streamlit for the timeline/comparison screen, a separate planning engine and independent environmental-data adapters. No database for the first demo. T1 establishes the shared interface and project setup; planned file ownership is in docs/plan.md. No application code has been started.

## Out of scope / faked
Multiple treatments, production capacity optimisation, in-transit ingredient transfers, real bookings, patient records, clinical validation and actual refrigeration monitoring. Journey and production durations and disruption delays use the synthetic fixtures in docs/scenarios.md. Real forecast coverage and a validated route-wide Rhine delay mapping remain unresolved; no such mapping is claimed by the demo. Existing route snow uses a timestamped manual status rather than automatic route inspection. A forecast alone cannot establish that the route is clear. Future route checks and missing/stale forecasts leave eligibility unconfirmed.

## Who does what
| GitHub username | Owns |
|---|---|
| @philLeu | foundation, planning engine, integration |
| @Fhuelin | scenarios and comparison screen |
| @luapreta-cloud | Rhine investigation underway; Rhine adapter |
| @janaaaaaaaa | weather and fallback demo |

See docs/plan.md for the agreed task boundaries and dependencies.

## Risks and fallback
MeteoSwiss local forecasts cover nine full days including the current day; the ingredient delivery plus treatment cycle can extend beyond that horizon. Transport assumptions may dominate the result. Display data coverage and uncertainty, and distinguish provisional plans from checked journey windows. Use a saved, timestamped environmental scenario for reliable replay, plus screenshots of the comparison if the live demo fails. Final scope and team review are pending.
