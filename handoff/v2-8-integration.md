# V2-8 integration handoff

Status: V2-8 and Jana's follow-up are merged into `feat/v2-treatment-planner`; the latter landed through PR #26 at `4ce19f1`. Current release status is in [the V2 release checklist](../docs/v2/release-checklist.md).

The shared branch integrated guided navigation, Live and Demo evidence, independent Demo controls, planning, recommendations, route summaries and explicit confirmation. Its implementation and automated checks are recorded in the branch history.

Jana's follow-up at `82b4279` extended this flow with two Basel weather endpoints, optional daily maximum forecasts, a Live Rhine gauge proxy, revised courier rules, richer route schedules and a transport-mode tie-break. It was integrated through PR #26; the PulseShift header branding from the shared branch was retained.

The follow-up's product rules were confirmed in chat on 2026-10-03: adopt Jana's Live assumptions and ship-then-bicycle tie-break. See [the release checklist](../docs/v2/release-checklist.md) for remaining review before the later release into `main`.
