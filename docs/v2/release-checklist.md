# V2 integration release checklist

Status: V2 was merged into `main` through PR #28. Use this checklist for subsequent demo changes and release checks.

## Integrated behavior

- Live evidence is the initial mode; refresh happens only after an explicit action.
- Offline Demo mode uses the planning engine and has independent Rhine, outbound and return controls.
- Each candidate exposes ingredient, outbound and return route summaries with evidence status and expandable detail.
- Goal changes recompute the recommendation; unavailable or unconfirmed evidence cannot be presented as a checked route.
- Material input changes invalidate confirmation; navigation alone does not.
- Live failures and unsupported route coverage remain explicit; there is no replay or synthetic fallback.
- Live weather uses both courier endpoints: modeled PulseShift production site (provider reference postcode 4056) and University Hospital Basel.
- The coordinator enters road status per leg. Forecast snowfall blocks bicycles; cars are always available with one hour of preparation.
- The Live overview shows endpoint forecast temperatures/weather symbols and a Basel gauge bar from 0 to 10 m. The ship delay applies the explicitly simplified uniform-Basel-level assumption and illustrative 0/12-hour rule.
- Daily maximum forecasts at or above 28°C prompt a trip-day recheck and do not block bicycle eligibility.
- Recommendation score ties prefer Rhine ship, then more bicycle legs; any remaining tie stays visible, with the first tied plan shown for inspection and explicit confirmation required.
- The PulseShift header logo and theme from the shared V2 branch remain in the integrated app.

## Verification

- `ruff format --check app.py src tests`
- `ruff check app.py src tests`
- `pytest -q`
- `bash scripts/doc-check.sh --strict`
- Automated AppTest covers the Live cards and road controls plus all three offline Demo chapters. The full application suite, standalone weather tests, Ruff and strict documentation checks passed on the shared V2 branch after PR #26 merged.
- One other teammate must inspect Plan, Routes & conditions and Sources & assumptions on desktop and a narrow screen, including keyboard access and written status beside icons. Record the reviewer and findings before release.
- Review and merge any final demo changes through a separate PR into `main`, with another teammate's review and explicit approval for that PR.

## Manual screen review

1. On desktop, open Live mode and inspect Plan, Routes & conditions and Sources & assumptions. Check that source freshness, unsupported coverage and route status are stated in words as well as icons or colour.
2. Switch to Demo mode and try each of the three disruption controls. Change the goal, select a route, confirm a plan, then change an input; confirmation should clear and the recommendation should update.
3. At a narrow browser width (about 390 px), repeat the chapter and control checks. Look for clipped text, sideways scrolling, hidden buttons or overlapping route details.
4. Use Tab and Shift+Tab to reach the mode switch, chapters, controls, route details and confirmation. Use Enter or Space to activate them; check focus remains visible and each control has a usable label.

The inherited GitHub history privacy guard failure is tracked separately and is not part of this cleanup.

## Known limits

- The team's uniform-Basel-level assumption is a planning simplification, not route-wide measurement or a provider ETA.
- MeteoSwiss hourly mean and optional daily maximum are separate forecast statistics.
- Demo disruption effects and transport durations are synthetic assumptions.
- The finite candidate set is not an exhaustive optimizer and the app does not book transport or make clinical decisions.
