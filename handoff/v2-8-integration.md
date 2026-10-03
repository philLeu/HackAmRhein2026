# V2-8 integration handoff

Status: merged into the shared `feat/v2-treatment-planner` branch at `61a5cfb`.

The shared branch integrated guided navigation, Live and Demo evidence, independent Demo controls, planning, recommendations, route summaries and explicit confirmation. Its implementation and automated checks are recorded in the branch history.

Jana's follow-up at `82b4279` extends this flow with two Basel weather endpoints, optional daily maximum forecasts, a Live Rhine gauge proxy, revised courier rules, richer route schedules and a transport-mode tie-break. The follow-up is prepared on `feat/integrate-jana-final-touch` for review against `feat/v2-treatment-planner`; the PulseShift header branding from the shared branch is retained.

The follow-up's product rules were confirmed in chat on 2026-10-03: adopt Jana's Live assumptions and ship-then-bicycle tie-break. See [the release checklist](../docs/v2/release-checklist.md) for checks and remaining review before the V2 branch merge. The later release into `main` is a separate step.
