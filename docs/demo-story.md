# T11: three-minute demo story

English speaker notes for the integrated treatment material-flow planner.
The coordinator and treatment below are invented. This is a proposed story,
not evidence of a real hospital workflow or a measured operational benefit.
Speaker: @leuphil. A teammate clicks; the team still needs to choose the operator.

## Prepare the screen

Start the app using the [README](../README.md). Preload **Synthetic walkthrough**
and **Baseline**, with the default route inputs unchanged. Use browser zoom at
125% if the comparison and treatment-period timeline remain readable on the
presentation display. Keep this document and the two slide texts below open.

The operator follows
the cue table; the speaker follows the script. Do not edit manual route inputs
during the main story: the synthetic walkthrough explicitly assumes renewed
clear-route checks at dispatch, whereas manual edits retain their evidence limits.

## Spoken script: 180 seconds including clicks and pauses

### 00:00–00:30 · The moment it hurts

“Imagine a coordinator planning one individual treatment. Ingredients travel
from Rotterdam to Basel. A sample must reach production, and the finished
treatment must return to the hospital on time. A delayed shipment or a blocked
courier journey changes the whole schedule. Our example is invented, but it
makes that coordination problem visible.”

### 00:30–00:45 · The workaround we model

“Our demo models a coordinator comparing revised schedules by hand. Changing
one arrival time is easy; tracking waiting, preparation and every deadline
together is harder. This prototype puts those trade-offs on one screen.”

### 00:45–02:15 · Live demo

“Here is the baseline: Rhine shipping and two bicycle journeys. The generated
plan passes the demo checks. We select it and inspect its timeline.

“Now we introduce a simulated twelve-hour Rhine delay. Keeping collection
unchanged makes production miss its deadline by five hours. We can postpone
collection by twelve hours, or switch the ingredient shipment to a refrigerated
truck before departure. Both pass these demo checks. We choose the truck and
can see its approval and preparation time.

“The second decision concerns the return journey. A simulated hot spell blocks
the return bicycle. We keep the outbound bicycle and choose a return car.
Notice that its eight-hour preparation overlaps production. Waiting until
production ends would be too late.

“These decisions use labelled synthetic inputs. In saved provider replay, the
original ship-and-bicycle plan is unconfirmed. The app shows missing evidence
instead of silently treating uncertainty as a pass.”

### 02:15–02:45 · Why the domain rules matter

“Preparation is part of the schedule, and waiting consumes the production
deadline. Each courier journey needs its own evidence. A Basel river observation
cannot establish the entire shipping route, and hourly mean temperature cannot
prove a maximum-temperature rule. We show those limits alongside the alternatives.”

### 02:45–03:00 · Next step

“The next step is to validate the workflow, timing rules and evidence requirements
with coordinators. This is a planning prototype: it makes no clinical decisions
and books no transport. Its value today is making assumptions and trade-offs inspectable.”

## Operator cues and verified outcomes

Choose alternatives by their ingredients, courier modes and collection shift,
not by a row number. Row order is not a recommendation or ranking.

| Script point | Action | What to show |
|---|---|---|
| Baseline | Inspect Rhine ship; bicycle / bicycle; collection +0h. Click **Select confirmed plan**. | Selected confirmation, full timeline and production margin +6h. |
| Low water: failure | Set **Scenario → Low water**. Inspect the same modes at +0h. | Prior selection clears; production margin −5h; selection disabled. |
| Low water: alternatives | Inspect Rhine ship; bicycle / bicycle; +12h, then refrigerated truck; bicycle / bicycle; +0h. | Each is confirmed; production margin +6h. Truck timeline includes **Truck approval / preparation**. Select the truck. |
| Hot return | Set **Scenario → Hot return**. Inspect Rhine ship; bicycle / bicycle; +0h, then bicycle / car; +0h. Select the mixed plan. | Bicycle failure, followed by confirmed mixed plan. **Return car preparation** runs 07.11.2026 · 19:00 UTC to 08.11.2026 · 03:00 UTC, during processing. Injection margin +6h. |
| Evidence limits | Set **Evidence mode → Saved provider replay**. Inspect Rhine ship; bicycle / bicycle; +0h. Open evidence and show **Sources and demo limits**. | That plan is unconfirmed and cannot be selected; missing maximum temperature and original Rhine retrieval time remain visible. Do not claim that all alternatives are unconfirmed. |

The mixed car plan's tightest overall margin is 0h because preparation finishes
at dispatch; its injection margin is +6h. Name the specific constraint when
describing a margin. Scenario changes recompute plans and clear selection.

## Two slide texts

These are presentation summaries of [SOURCES.md](SOURCES.md), the authoritative
source index, and the [design limits](design.md). Keep those links with the slides.

### Slide: sources and contributions

- **Rhine:** FOEN/BAFU observations via Open Data Basel-Stadt, CC0 1.0; saved Basel gauge sample. The expandable station chart also uses a BAFU ensemble forecast with separate free-use/source-citation terms; see [Rhine source notes](sources/rhine.md).
- **Weather:** Source: MeteoSwiss, CC BY 4.0; saved forecast with issue time and coverage. No proprietary weather artwork.
- **Synthetic inputs:** invented treatment, journey/process durations, availability, route checks and disruption effects; declared alongside results.
- **Software:** Python; Streamlit (Apache-2.0), Altair (BSD-3-Clause), pytest/Ruff/setuptools/wheel (MIT). Dependency details are in [pyproject.toml](../pyproject.toml) and [requirements.txt](../requirements.txt).
- **AI assistance:** Codex assisted development and this script; team members supplied and reviewed the domain assumptions. Do not imply independent clinical validation.

### Slide: limits and next validation

- One invented treatment; finite, unranked alternatives. No capacity optimisation, bookings, patient records or clinical decisions.
- The demonstrated Rhine delay and hot return are simulations, not measured effects of the provider data.
- Provider replay is historical, evaluated at 03.10.2026 · 11:30 UTC. Mean temperature is not maximum temperature; a local gauge does not establish route-wide navigability.
- Synthetic renewed route checks are an explicit walkthrough assumption. Provider/manual inputs preserve missing, stale and outside-coverage evidence.
- Validate workflow, timing assumptions, route evidence and required governance with the intended users before operational use.

## Rehearsal and fallback

Two automated screen dry runs passed on 03.10.2026. They checked the cue sequence,
selection changes, margins, preparation events and the unconfirmed replay plan.
They took approximately 2.1s and 1.0s for automated interaction; these are **not**
spoken rehearsal times or claims about presentation length.

The spoken script is deliberately short to leave room for clicking and pauses.
Before calling T11 rehearsed, do two spoken runs with a timer on the presentation
display. Record actual total times below; leave them blank until measured.
After run one, cut about 20% of any overlong explanation. Keep both changed
decisions, the preparation insight, attribution and uncertainty statement.
If the live portion is slow, explain the +12h option from the table without
opening its timeline, and show provider limits from the slide.

| Human rehearsal | Presenter / operator (GitHub usernames only) | Total | Adjustment |
|---|---|---|---|
| Run 1 | @leuphil / operator to choose | Not measured | Pending |
| Run 2 | @leuphil / operator to choose | Not measured | Pending |

Coordinate fallback screenshots or recording with T10, which owns offline
readiness. If the app is unavailable, use the two slide texts and the verified
outcomes above. Say that the live app is unavailable; do not pretend a static
image is interactive. A fallback video is not yet available or tested by T11.

## Likely jury questions

| Question | Short answer |
|---|---|
| Who uses it, and what do they do today? | A production coordinator. We model manual schedule comparison; we have not yet validated the workflow with operational users. |
| What is simulated? | Treatment and transport timings, availability, renewed synthetic route checks, the Rhine delay and hot weather. The engine computes the alternatives from those inputs. |
| What does the open data add? | Inspectable environmental evidence with provenance and coverage. It exposes uncertainty; it does not establish shipping delay or clinical feasibility. |
| May you use the data? | The documented Basel observations are CC0 1.0; MeteoSwiss is CC BY 4.0 with attribution. See the source index for the exact captures and limits. |
| Why not use the average temperature? | A mean can hide a threshold exceedance, so a missing maximum stays unknown. |
| Why does the car prepare during production? | Its preparation must finish before dispatch, while return travel and hospital handling must fit the injection deadline. |
| Is this the optimal plan? | No. We show a finite, unranked alternative set; the coordinator chooses. |
| What would real use require? | Validated workflow and timings, suitable current evidence, availability inputs, and clinical/security/governance review. Costs and deployment requirements have not been established. |
| What did each teammate contribute? | Refer to [TEAM.md](../TEAM.md); each person explains their own contribution. |
