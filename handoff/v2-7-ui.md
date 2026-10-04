# V2-7 guided UI handoff

Status: integrated into `feat/v2-treatment-planner`. The PR and next-step notes below record the task handoff; current release status is in [the V2 release checklist](../docs/v2/release-checklist.md).
Owner: @fhuelin · Updated: 2026-10-03
PR: https://github.com/philLeu/HackAmRhein2026/pull/22

## State
Local branch feat/v2-7-guided-ui starts at shared V2 commit 428abbb.
V2-0 and V2-3 are integrated; use the approved V2-1/V2-2 rules and sketch.
UI implementation is saved at bcae014. Shared V2 weather update 65a2a19
was merged without conflicts; the integration adjustments are saved locally.
Latest shared V2 Rhine update d0bd1bd is also merged without conflicts.

## Scope
Navigation, goal/recommendation display, route summaries and independent typed
demo controls. Preserve V1 callers; no app.py, adapter, ranking or shared
contract edits. V2-8 owns wiring and whole-application mode/reset state.

## Next
PR #22 targets feat/v2-treatment-planner under the updated V2 workflow.
@fhuelin approved integration; one other teammate's review remains required.
GitHub guard checks failed; a local full-history audit finds a historical
personal commit email. Staged and pre-push guards passed for this task.
Resolve the inherited history issue through the team's privacy workflow;
do not bypass checks or rewrite shared history without team agreement.
V2-8 performs app wiring. Append the queued decision below when integrating.

## Implemented
- navigation.py supplies chapters and explicit Live/Demo mode selection.
- recommendation.py collects goal/target inputs and displays supplied winners;
  the first winner, including among ties, is preselected for review; confirmation
  remains explicit. Input/evidence context changes
  clear confirmation; navigation preserves the picked plan.
- route_summary.py presents supplied statuses/delays/provenance and demo
  carry-over notes. It extracts the adopted route drawing for V1/V2 reuse.
- demo_controls.py returns typed, independent route edits and a reset request;
  forecast snowfall, route snow, temperature and car availability stay separate.
- comparison.py accepts optional V2 contracts without changing V1 callers;
  sources and full adopted diagrams remain available on demand.
- tests/test_v2_screen.py supplies contract examples, not ranking logic.
- The V2 comparison also renders the supplied non-blocking weather recheck
  reminder. Its displayed dates use the shared application format.
- Weather test payloads normalize CRLF before removing hourly readings, so
  missing-reading assertions exercise the same scenario on Windows and Linux.

## V2-8 integration notes
- Call render_navigation and render_evidence_mode; default to Live. The caller
  supplies actual evidence or an explicit fixed demo fixture.
- Call render_goal on Plan and persist its returned goal/target independently
  of widget lifetime. Recompute through V2-6 before passing RecommendationResult
  and per-plan RouteSummary objects to render_comparison.
- Pass confirmation_context containing goal, target, mode, overrides and reset
  generation. Include material input/evidence changes; exclude navigation.
- render_comparison returns only an explicitly confirmed CandidatePlan. Its
  optional baseline_plan is the original reference, not the first generated plan.
- V2-8 owns whole-app confirmation invalidation even when Plan is not displayed.
  A reset must clear the component's prefixed session state and restore baseline
  goal/target/clock. Pass a stable component key across chapter switches.
- render_demo_controls requires three baseline templates, a fixed clock and the
  gauge station/datum label. Its return tuple is (DemoOverrides, reset_requested).
  Live returns empty overrides. Integrate edits, recompute, and rerun as needed.
- Adapters/integration apply carried demo conditions and construct RouteSummary
  carried_from; the UI only shows that note. It does not extend Live coverage.
- Route/Sources chapters use render_route_summaries and render_sources. Preserve
  the chosen plan in application state, rather than depending on widget presence.
- tests/test_v2_screen.py contains a composition example in APP. A local browser
  preview was generated from it; that preview is labelled synthetic/unranked.
- New route.card_width and route.label_font_size theme tokens keep route cards
  and labels readable. Demo buttons use native wrapping rather than fixed columns.

## Verification
- Final full suite after the shared weather and Rhine updates: 189 passed.
- Ruff lint and format checks pass for the changed UI modules and V2 tests.
- V1 comparison, contract and end-to-end tests remain green.
- Browser verified explicit confirmation with optional details, desktop route
  grouping and the narrow-screen button wrapping. Application wiring is pending.
- Mandatory privacy/documentation hooks run when saving this branch.

## Limits
The browser preview uses authored contract scores and summaries, not V2-6
ranking or live adapters. app.py is unchanged; the V1 entry point stays active
until V2-8 integrates these components. No shared interface changes were needed.

## Decision queued for integration
- 2026-10-03 · Supply V2 guided UI through reusable contract-driven components;
  retain V1 callers until V2-8 wiring, keep ranking out of presentation, require
  explicit confirmation and complete passing route summaries · @fhuelin ·
  Affects: V2-6, V2-7, V2-8 · Why: support independent implementation and prevent
  stale or contradictory results from becoming a confirmed plan.
