# V2-1 recommendation rules handoff

Status: done · Updated: 2026-10-03 · Owner: @fhuelin

## Goal
Define the three recommendation goals, hard-check precedence, ties, route
statuses and examples before implementing the recommendation engine.

## Delivered
- Rules: `docs/v2/recommendation-rules.md`.
- Synthetic fixtures and deterministic score examples: `docs/v2/scenarios.md`.
- The V2 overview links to these agreed rules and allows preselection only for
  a unique confirmed winner.
- The queued domain decisions are now in `docs/decisions.md`.

## Integration
The user explicitly authorised integration into `feat/v2-treatment-planner`.
The reviewed V2-1 output reaches the shared V2 release branch through local
integration branch `codex/v2-1-integration`.
Only the shared release branch may be pushed. Main stays outside this release.

## Next
V2-2 defines the guided screen sketch. V2-3 then defines the shared contract
before the ranking engine and UI implementation begin.

## Verification
The strict documentation check, staged whitespace check and mandatory staged
privacy guard passed before commit. The commit hooks repeat the required checks.
No application code changed, so application tests are not required for this task.
