# V2: guided treatment material-flow planning

Status: Release direction, V2-1 recommendation rules and V2-2 screen sketch agreed; shared contracts are next.

## Outcome

Help the production coordinator choose a plan with less manual comparison. Open with live environmental evidence, recommend and preselect a confirmed alternative for the chosen goal, and show concise route risks and possible delays. Keep explicit user confirmation and optional access to alternatives, evidence and constraints.

Extend the existing Python/Streamlit application, planning engine and independent adapters. Keep one treatment per planning run. Do not add bookings, patient records, multiple-treatment capacity optimisation or a stack migration to this release.

## Guided flow

1. Open in Live mode with source timestamps, freshness and coverage available.
2. Choose an optimisation goal: injection timing, ingredient delivery timing or lower disruption risk.
3. See the recommended alternative, its main reason and timing. Preselect only a unique confirmed winner; equal winners remain tied without automatic selection. Preselection is distinct from confirmation. Other alternatives remain available on demand.
4. Inspect three graphical route summaries with transport icons, direction arrows, status text and possible delay. Expand a route for detailed evidence, assumptions and constraint results.
5. Confirm the selected plan. Changes to the goal, inputs or material evidence invalidate previous confirmation and recompute the recommendation.

Sidebar chapters: Plan, Routes & conditions, Sources & assumptions. Keep the goal and recommendation together on Plan. The approved screen behavior lives in [ui-sketch.md](ui-sketch.md), with visual guidance in [style-guide.md](style-guide.md). Preserve the existing theme and UTC display convention unless the team approves a change.

Show ingredient movement separately from sample/treatment movement:

- Rotterdam -> ship or refrigerated truck -> PulseShift production site in Basel.
- Hospital -> bicycle or car -> Production -> bicycle or car -> Hospital.

Use ship, truck, bicycle, car, hospital and production-site icons, plus high/low Rhine and sun/snow/heat indicators. Pair every status icon and colour with text. Reuse code-native icons; do not require generated artwork.

## Live data and demo controls

Live is the default. Show current forecast conditions for the modeled PulseShift production site (MeteoSwiss postcode 4056) and University Hospital Basel (4031), and request both points across candidate courier journeys. The provider's physical postcode 4056 reference is Novartis Campus Basel; the model treats it as the PulseShift site. The coordinator records road clearance for each leg. Snowfall blocks bicycles; cars are always available and need one hour of preparation. A daily maximum forecast of 28°C or higher is a trip-day recheck reminder, not an eligibility block. Source failures, stale inputs and outside-horizon journeys remain explicit. Offer Demo mode when live data fails; never silently substitute simulation.

A Demo switch at the top reveals three buttons opening route controls:

1. Rotterdam -> Basel: Rhine level, with station and unit identified.
2. Hospital -> Production: temperature and snow.
3. Production -> Hospital: independent temperature and snow.

Use a deterministic demo fixture and clock when Demo mode is active. Label all simulated evidence. Define reset behaviour and override validity windows in the screen sketch. Switching back to Live removes demo overrides and invalidates any confirmed demo plan.

Demo controls must feed the planning flow, rather than changing only chart decoration. For Live shipping, assume the Basel gauge level is uniform along the route and apply the existing illustrative low-water delay mapping; state that it is not a measured ETA. Display the current gauge on a 0–10 m scale. Separate forecast snowfall from existing route snow; their meaning must be explicit. Keep hourly mean and daily maximum temperature distinct.

## Recommendation rules

The agreed objectives, default goal, hard-check precedence, tie handling and
route-status meanings live in [recommendation-rules.md](recommendation-rules.md).
Expected winners and score examples live in [scenarios.md](scenarios.md).
Explain the decisive trade-off in one sentence. The risk score is not a
calibrated failure probability.

Display a supported delay estimate or "delay unknown"; do not turn uncertainty
into zero delay. Keep the existing distinction between confirmed, infeasible
and unconfirmed plans.

## Release evidence

Existing baseline, low-water, hot-return, snow and missing-evidence scenarios remain valid. Verify goal-specific rankings, independent demo overrides, confirmation invalidation, live failure behaviour, freshness and coverage, and offline demo execution. Include keyboard-readable controls and status text independent of colour.

Task boundaries and branch workflow live in [plan.md](plan.md). Record agreed domain/contract changes in ../decisions.md; update source notes and README alongside their implementation.
