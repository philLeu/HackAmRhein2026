# Demo checklist: offline fallback

Use the project's Python 3.12 setup and the commands in [README.md](../README.md).
The default synthetic walkthrough and **Saved provider replay** read local files;
the app does not need internet access. Keep the historical replay clearly
labelled and do not describe its readings as current conditions.

## Run the story

1. Open **Synthetic walkthrough → Baseline**. Inspect the ship / bicycle / bicycle
   alternative. Expected margins: ingredients 96 h, sample 11 h, production 6 h,
   injection 6 h. Select it and confirm the selected timeline is shown.
2. Choose **Low water**. Inspect the unshifted ship plan: production margin −5 h,
   so it cannot be selected. Inspect collection shifted by 12 h: production margin
   +6 h and confirmed. The refrigerated-truck alternative keeps the collection
   time; its approval/preparation and travel intervals are visible.
3. Choose **Hot return**. The 30.1°C return forecast blocks the bicycle. Inspect
   the car alternative and confirm its 8 h preparation overlaps production and
   the injection margin remains +6 h.
4. Choose **Snow**. Snow blocks bicycle legs. Inspect a car plan and show the
   separate preparation intervals for the two legs.
5. Choose **Missing weather** and set both car availabilities to **unknown**.
   The result should say no confirmed plan yet, with unknown weather and
   availability checks. It must not say all alternatives are infeasible.
6. Choose **Saved provider replay**. The saved observations and forecast load
   without network access. Show the source and coverage details: the Rhine sample
   is historical, its original retrieval time is unknown, and the MeteoSwiss
   replay has missing/stale journey coverage and no hourly maximum temperature.
   Bicycle plans remain unconfirmed. Freshness controls are inspection values,
   not an approved operational policy.

## Capture a visual backup

Keep screenshots outside Git or in an ignored local directory, and exclude any
personal or company data. Capture these three screens:

- baseline comparison with the selected plan and its timeline;
- low-water alternatives with the −5 h failure and +6 h recovery visible;
- saved-provider replay with source attribution and unknown evidence visible.

If the app cannot start, use the [static fallback story](demo-fallback.svg) and
the accepted scenario details in [scenarios.md](scenarios.md). The fallback is
an explanation of tested expectations, not a screenshot of the running app.

## Result language

- **Confirmed:** every required check has adequate evidence and passes.
- **Infeasible:** at least one supported check fails.
- **Unconfirmed:** missing or incomplete evidence prevents confirmation.

All treatment and transport timings are invented. The low-water delay is a
synthetic 12 h input, not a conclusion from the Basel gauge. The app books no
transport and makes no clinical decision.
