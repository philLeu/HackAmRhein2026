# V2 integration release checklist

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
- Recommendation score ties prefer Rhine ship, then more bicycle legs; any remaining tie stays visible for explicit choice.
- The PulseShift header logo and theme from the shared V2 branch remain in the integrated app.

## Verification

- `ruff format --check app.py src tests`
- `ruff check app.py src tests`
- `pytest -q`
- `bash scripts/doc-check.sh --strict`
- Automated AppTest covers the Live cards and road controls plus all three offline Demo chapters. Interactive visual review of the running app remains pending.
- Have a teammate inspect Plan, Routes & conditions and Sources & assumptions on desktop and a narrow screen, including keyboard access and written status beside icons.
- Review the integration PR into `feat/v2-treatment-planner`; merge it only after explicit approval. Then run the full checks on the shared V2 branch before preparing the later PR into `main`.

## Known limits

- The team's uniform-Basel-level assumption is a planning simplification, not route-wide measurement or a provider ETA.
- MeteoSwiss hourly mean and optional daily maximum are separate forecast statistics.
- Demo disruption effects and transport durations are synthetic assumptions.
- The finite candidate set is not an exhaustive optimizer and the app does not book transport or make clinical decisions.
