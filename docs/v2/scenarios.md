# V2 recommendation examples

All dates are UTC. Use the invented fixture clock and hard limits in the
[approved scenario conventions](../scenarios.md); provider evidence is not
relabelled as a measured delay or clinical outcome. Use these cases to verify
that each goal explains its winner or preserves equal winners.

| Case | Input | Expected result |
|---|---|---|
| Original baseline | Complete synthetic evidence; target injection is 08.11.2026 · 05:00 UTC, the original baseline injection time. | The original timetable reaches score 0 for injection timing. Any other confirmed plan with the same goal score remains an equal winner; no automatic pick. |
| Low-water delay | Synthetic 12-hour Rhine delay; decision is before the permitted truck switch deadline; target injection is 08.11.2026 · 17:00 UTC. | The 12-hour postponed ship schedule reaches the injection target if every check passes. Earliest-delivery favours the confirmed plan with earliest ingredient arrival. Lower-risk compares only the four named delivery/sample/production/injection margins; equal leaders remain tied. |
| Hot return | Return maximum 30.1°C; required evidence and car availability supplied. | A return bicycle fails the heat rule. Only confirmed car-return plans can be recommended. Each car has its own preparation interval; preparation must pass but does not count as a zero-margin risk penalty. |
| Outbound snow | Forecast snowfall overlaps the outbound leg; the return leg is clear. | Outbound bicycle is blocked. Keep a feasible return bicycle available; a mixed-mode plan is eligible if its checks pass. |
| No feasible plan | The approved +48-hour low-water example after Rotterdam departure. | No confirmed plan: explain the production-deadline failure and unavailable shipment switch. Show provisional alternatives only when requested. |
| Missing journey evidence | Weather coverage or a required route observation is absent/stale. | An affected plan is unconfirmed, never ranked as safe. If no confirmed alternative remains, show no recommendation and expose the missing evidence on demand. |

## Scoring checks

These isolated arithmetic examples assume both candidates have passed every
hard check with adequate evidence. They do not replace the fixture evidence.

| Goal/case | Plan A | Plan B | Expected winner |
|---|---|---|---|
| Injection timing | 30 minutes early: score 30 | 30 minutes late: score 60 | A |
| Ingredient delivery | Arrival 08.11.2026 · 10:00 UTC | Arrival 08.11.2026 · 11:00 UTC | A |
| Risk margin first | Minimum scored margin 6 hours; 1 At risk route | Minimum scored margin 5 hours; 0 At risk routes | A |
| Risk tie-break | Minimum scored margin 6 hours; 1 At risk route | Minimum scored margin 6 hours; 0 At risk routes | B |
| Exact risk tie | Minimum scored margin 6 hours; 0 At risk routes | Minimum scored margin 6 hours; 0 At risk routes | A and B, tied; no preselection |

- Injection score uses the target timestamp entered for that run. For example,
  30 minutes early scores 30; 30 minutes late scores 60. Lower scores rank
  first, subject to every hard check passing.
- Delivery score compares the ingredient-arrival instant at production only.
- Risk score takes the smallest remaining margin from the ingredient-arrival,
  sample-arrival, production-completion and injection checks. Larger positive
  margins rank first. The zero margin on a just-in-time preparation check and
  the collection-shift cap do not enter this score; they still must pass.
- If risk margins tie, fewer distinct At risk local routes rank first.
- Two plans identical on every goal score stay co-winners. Show them as tied;
  do not imply one is better or preselect one until asked.
- Infeasible and unconfirmed plans are not scoreable candidates. Report their
  reasons separately. When the confirmed set is empty, leave the
  recommendation empty.
