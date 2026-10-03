# Expandable Rhine conditions

Status: done; implementation verified, awaiting teammate review and explicit merge approval.

## Goal
Bring the updated notebook classifications, BAFU ensemble forecast and historical/predicted chart into the dashboard as inline expansion above plan comparison.

## Done
- Recorded the approved design, T12/T13 tasks and additive shared interface decision.
- Extracted classification rules into config/rhine.json and pure assessment/summary logic.
- Added validated BAFU hourly median, min-max and percentile parsing with issue-time provenance.
- Captured two days of observations and a forecast for offline replay at the existing historical clock.
- Added saved/live evidence selection, summary, chart, findings and explicit incomplete forecast coverage.
- Updated README and source notes, including limitations and separate forecast attribution.
- All 138 tests, formatter, linter and documentation checks pass. Browser verified inline expansion, responsive chart, selected forecast marker and matching written findings.
- Live public endpoints verified: 118 forecast points and 574 observations; observation coverage latency was reported explicitly.

## Next
Review the implementation PR from feat/rhine-forecast-dashboard. Teammate review and explicit approval are required before merging.

## Constraints
Classes describe notebook station rules, not route-wide safety or delivery delays. No extrapolation or silent replay fallback. Historical chart evidence has its own clock; live evidence does not alter synthetic planning inputs. Actual capture retrieval happened after the replay evaluation time; issue time is preserved.

## Resume prompt
Review feat/rhine-forecast-dashboard. Read this handoff and inspect the expandable Rhine chart. The implementation and proposal belong in one PR. Do not merge without explicit approval.
