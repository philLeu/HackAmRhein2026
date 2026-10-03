# V2-5 live weather and independent local-route overrides

Status: implementation ready for review and integration
Owner: @janaaaaaaaa
Branch: feat/v2-5-weather
Base: 428abbb on feat/v2-treatment-planner (integrated V2-3)

## Delivered

- Live weather provider using the latest complete MeteoSwiss cycle, independent
  journey clipping, actual issue/retrieval clocks, explicit refresh and snapshot
  reuse. Missing, stale, unsupported and outside-horizon evidence stay explicit.
- Shared source parsing with the T3 utility; existing standalone commands still
  work. No dependency or shared interface changes.
- Per-leg synthetic weather and local-route adapters using the V2-3 override
  models, preserving Unknown, snow/availability distinctions and source clocks.
- Carry-over metadata for moved simulated trips, without extending live coverage.
- Source documentation and offline regression checks, including real-planner
  examples for independent return heat, outbound route snow and unavailable cars.
- Added the user's inclusive 28°C trip-day recheck advisory, configured in
  config/weather.json. It is independent of feasibility/issues and distinguishes
  source hourly means from simulated maxima. A small comparison hook makes the
  reminder visible in the current demo; V2-7 can reuse the standalone UI component.

## Verification

- Core implementation full application suite: 164 passed.
- After adding the 28°C advisory, affected weather/comparison/demo suite: 47 passed.
- Existing standalone weather parser suite: 18 passed.
- Ruff lint and format checks for application code, tests and the capture
  compatibility entry point passed; strict documentation and whitespace checks passed.
- The documented standalone synthetic capture command also passed.
- Live access verified at 2026-10-03 18:45 UTC; details and source limitations
  are in docs/sources/weather.md.

## Integration boundaries

V2-8 wires the public WeatherLiveProvider and per-leg DemoWeatherProvider into
app.py. Keep the live provider instance across reruns and refresh explicitly;
invalidate confirmation on material changes. Use the caller's positive forecast
age inspection limit. No maximum-temperature policy has been changed.

For demo overrides, retain each route's baseline when its override is None.
Pass the per-candidate journey to its provider, adapt the route input separately,
and pass demo_carry_over to RouteSummary.carried_from for V2-7 presentation.
The original typed override stays untouched. Reset/mode state and constructing
the per-plan summaries remain with V2-8/V2-7.

Source docs are the authority for the single forecast point, hourly means versus
maxima, attribution and actual coverage. The existing comparison now includes the
user-requested advisory; live/demo provider wiring is still owned by V2-8.
V2-8 updates the top-level sources/README once the component is wired.

## Queued shared decision

- 2026-10-03 · Reuse the MeteoSwiss parsing code for live and replay, assess live
  forecast age at the actual evaluation clock, and keep per-leg demo carry-over
  separate from data-quality issues · @janaaaaaaaa · Affects: V2-5, V2-7, V2-8 ·
  Why: preserve source meaning and independent simulated journeys without
  mislabelling future-valid forecasts or blocking them because of a display note.
- 2026-10-03 · Warn when a forecast or simulated journey temperature is >=28°C
  and ask the coordinator to refresh and recheck the plan on the trip day ·
  @janaaaaaaaa · Affects: V2-5, V2-7, V2-8 · Why: highlight forecasts close to the
  bicycle heat limit while preserving the existing checks, temperature statistic
  and explicit-refresh workflow. This advisory does not alter risk ranking.

## Next

- Review the component with a teammate and integrate it into the shared V2 branch.
- Wire the controls and route summaries through the integration owner.
- Continue to show unsupported maximum temperature as unknown unless the team
  approves a different source/statistic; do not silently treat a mean as a maximum.
