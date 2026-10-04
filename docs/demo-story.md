# Five-minute PulseShift demo

Speaker: @philLeu. App operator: @Fhuelin. Rehearse together on the presentation laptop; the timings below are cues, not a claim that a spoken run has been measured.

## Before the team is called

Start the app using the [README](../README.md), open it at full screen, and check that **Demo** mode works without network access. Keep this cue sheet and the [fallback checklist](demo-checklist.md) available. Use **Reset demo** before the presentation so the fixed fixture starts clean. If Live evidence is slow or unavailable, start directly in Demo and say why.

## Speaker and operator cues

| Time | Speaker | Operator |
|---|---|---|
| 0:00–0:45 | “One individual treatment depends on ingredients arriving from Rotterdam, a sample reaching production, and the finished treatment returning to the hospital. A disruption at any step changes the schedule. We built PulseShift to make the options and their evidence visible to a production coordinator.” | Show the Plan chapter and its three routes. |
| 0:45–1:25 | “Live mode brings in Basel Rhine gauge observations and MeteoSwiss forecasts at the modeled production site and hospital. The gauge is a simplified proxy for the shipping route, not a measured arrival time. We keep source coverage and unknowns visible.” | If available, point to both weather cards and the Rhine gauge. Switch to **Demo** for the repeatable walkthrough. |
| 1:25–2:25 | “The same planning engine now works with clearly labelled simulated inputs. First, a low Basel gauge adds an illustrative 12-hour ship delay. The recommendation and schedule respond; we can inspect a truck alternative before the ship departs.” | Open **Rotterdam → Basel**, set the gauge to **470 cm**, apply, then show the changed recommendation and ingredient route detail. |
| 2:25–3:25 | “Next, forecast snowfall on the return journey rules out a bicycle there. A car option includes preparation time. Each journey has its own evidence and route status.” | Open **Production → Hospital**, set **Forecast snowfall** to **Yes**, apply, then show a car-return plan and its route summary. |
| 3:25–4:15 | “The app ranks confirmed candidates for the chosen goal. When scores tie, it shows one plan first and labels the tie; the coordinator can switch plans. The plan is never confirmed automatically.” | Show the plan picker, choose a confirmed plan, click **Confirm plan**, then change one input to show confirmation clearing. If clicks are slow, skip the last input change and state the behavior. |
| 4:15–5:00 | “This is a planning prototype. Treatment timing and transport durations are invented; the river and weather sources cover points and forecast windows, not a whole route. It does not book transport, use patient records, or make clinical decisions. Next we would validate the workflow and assumptions with coordinators.” | Open **Sources & assumptions**. Finish on the app, ready for questions. |

## Questions to anticipate

- **What is live?** Public Rhine and MeteoSwiss evidence, with source times and coverage. Demo disruptions and treatment schedules are synthetic.
- **Is this an optimal or clinical decision?** No. The engine compares a finite set of alternatives under stated rules; a coordinator must confirm a plan.
- **What happens when evidence is missing?** The app marks the route or plan unknown or unconfirmed rather than presenting it as checked.
- **Why use a Basel gauge for the Rhine route?** It is an explicit simplifying assumption for the demonstration, not route-wide measurement or a provider delivery estimate.
- **What did the team build?** A Streamlit interface, planning and recommendation logic, independent Rhine and weather adapters, and an offline Demo mode. See [TEAM.md](../TEAM.md) for contributions.
