# Design handoff

Status: in progress · Updated: 2026-10-03 · Branch: main (initial repository snapshot)

## Goal
Agree a small manufacturing-control demo using real environmental open data to compare material-flow plans.

## State
Design draft and starter kit form the initial repository snapshot; no application code yet. Shared repository is https://github.com/philLeu/HackAmRhein2026. Check Git history and remote tracking for current publication state. Future work goes through task branches and pull requests.

## Done
- Confirmed four team usernames and shared repository in TEAM.md; @janaaaaaaaa has joined.
- Captured one-treatment timeline, Rotterdam shipment, schedule and transport alternatives, and local bicycle/car courier rules in docs/design.md.
- Recorded confirmed product decisions in docs/decisions.md.
- Confirmed snow blocking includes either forecast snowfall during the journey or existing snow on the route.
- Existing route snow will use a coordinator-entered clear / snow present / unknown status for the demo; unknown leaves bicycle feasibility unconfirmed.
- Researched candidate MeteoSwiss local forecasts and Rhine observations; recorded source links, weather attribution and forecast-horizon limitations in docs/SOURCES.md. No data downloaded or integrated.
- Repository privacy setup completed; Git Bash checks need PATH=/usr/bin:/mingw64/bin:$PATH in this execution environment.

## Next
1. Agree synthetic transport/production durations and remaining timing semantics; define freshness of manual route status.
2. Verify open Rhine/weather providers, licence, timestamps and forecast coverage; document in docs/SOURCES.md.
3. Agree synthetic durations and remaining timing semantics listed in docs/design.md.
4. Agree stack, proposed team ownership and review policy from docs/plan.md, then finalise the design. See handoff/docs-plan.md for the proposed task split.
5. Run privacy and documentation checks before saving/sharing. Ask explicitly before merging any PR.

## Files
TEAM.md; docs/design.md; docs/decisions.md; docs/SOURCES.md.

## Known limitations
Environmental data cannot establish transport availability or refrigeration state. A 5–10 day ingredient delivery may exceed detailed local weather forecast coverage. All treatment timing rules are demo assumptions, not validated medical requirements.

## Resume prompt
Continue the design from handoff/docs-design.md. Read docs/design.md and docs/decisions.md, resolve the next open question, and preserve the confirmed constraints. No application code before design agreement.
