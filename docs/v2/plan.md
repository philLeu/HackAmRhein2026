# V2 release plan

Based on [design.md](design.md). Owners are proposed from existing team responsibilities. Agree owners and remaining domain rules before implementation. No implementation code is included in this planning commit.

## Branching and review

- Shared release branch: `feat/v2-treatment-planner`, created from verified origin/main. Work in a separate worktree; leave the current main checkout unchanged.
- All V2 documentation, code and tests reach GitHub only through this branch. Never push main or local task branches for V2 work.
- Each teammate uses a separate working folder and a local task branch based on the latest V2 release branch, for example `feat/v2-recommendations`. These branches stay local. Different machines can exchange reviewed commits as Git patches or bundles, then have the integration owner apply them to the shared branch.
- Proposed integration owner: @philLeu. Review each task with one teammate before integration. Apply reviewed commits, run appropriate checks and push only the shared V2 branch. Other teammates fetch and incorporate the latest V2 state before starting their next task.
- Never force-push or rebase shared history. Privacy guard and executable hooks remain mandatory before every commit and push.
- Task dependencies are satisfied when their reviewed outputs are integrated into the V2 branch, not main. Reserve app.py for the integration owner; coordinate manifest and shared contract changes through that owner.
- A release PR into main is deferred until V2 meets its acceptance checks. Merge only after explicit approval for that specific PR.

Status lives in task-specific handoff files, not this plan. Implementation file paths below are proposed outputs and may not exist yet. Split oversized tasks into one-chat subtasks before starting them.

## M1: the recommendation rules and guided screen are agreed

### Chunk A: parallel

#### V2-1 Recommendation rules and domain examples
Owner: @Fhuelin with @philLeu (proposed)
Needs: nothing
Files: docs/v2/recommendation-rules.md, docs/v2/scenarios.md, docs/decisions.md, handoff/v2-1-rules.md
Done when: all three goals have a precise definition, hard-constraint precedence, tie-breaks and examples with expected winners; no-confirmed-plan behaviour is agreed.
Notes: settle target injection time, meaning of delivery time, risk score inputs, default goal and route-status meanings. Use a score, not a claimed failure probability.

#### V2-2 Guided screen and demo-control sketch
Owner: @Fhuelin (proposed)
Needs: nothing
Files: docs/v2/ui-sketch.md, docs/v2/style-guide.md, handoff/v2-2-screen-sketch.md
Done when: the team can walk through sidebar navigation, goal selection, recommendation, confirmation, graphical route summaries, expanded details and all three demo buttons.
Notes: define temperature and snow semantics, override validity, demo clock/reset behaviour and Live/Demo transitions. Reuse existing theme tokens. Keep status text beside icons.

### Chunk B: in order

#### V2-3 Shared contracts and component boundaries
Owner: @philLeu (proposed)
Needs: V2-1, V2-2
Files: src/treatment_planner/interfaces.py, tests/test_contracts.py, docs/decisions.md, handoff/v2-3-contracts.md
Done when: goals, recommendation explanations, route summaries, evidence modes and per-route overrides have agreed shared models; contract checks pass without breaking existing inputs.
Notes: add the interface decision line in the same commit. Allocate adapter, ranking and UI files before parallel implementation begins.

## M2: live evidence, recommendations and route summaries work independently

### Chunk C: parallel after V2-3

#### V2-4 Live Rhine and ingredient-route override
Owner: @luapreta-cloud (proposed)
Needs: V2-3
Files: src/treatment_planner/data/rhine.py, src/treatment_planner/data/rhine_forecast.py, src/treatment_planner/rhine_conditions.py, src/treatment_planner/rhine_demo.py, config/rhine.json, tests/test_rhine.py, tests/test_rhine_forecast.py, tests/test_rhine_demo.py, docs/sources/rhine.md, handoff/v2-4-rhine.md
Done when: the component loads live evidence by default and supplies a labelled demo Rhine override with explicit missing/stale/outside-horizon states and documented simulated delay effects.
Notes: reuse existing live fetching; Basel conditions do not establish route-wide navigability. Do not edit app.py.

#### V2-5 Live weather and independent local-route overrides
Owner: @janaaaaaaaa (proposed)
Needs: V2-3
Files: src/treatment_planner/data/weather.py, src/treatment_planner/weather_demo.py, tests/test_weather.py, tests/test_weather_demo.py, docs/sources/weather.md, handoff/v2-5-weather.md
Done when: each journey window receives correctly timestamped live weather or independent labelled demo temperature/snow inputs; provider failures and unsupported evidence stay explicit.
Notes: preserve hourly-mean versus maximum-temperature semantics and manual route-snow evidence. Verify live access, licensing and coverage before integration. Coordinate dependency changes with the integration owner.

#### V2-6 Alternative ranking and recommendation
Owner: @philLeu (proposed)
Needs: V2-3
Files: src/treatment_planner/recommendations.py, config/recommendations.json, tests/test_recommendations.py, handoff/v2-6-recommendations.md
Done when: agreed examples yield the expected winner for each goal, tie-breaks are deterministic, and no confirmed alternative yields an explicit no-recommendation result.
Notes: rank outputs from the existing planner rather than duplicating constraint evaluation. Explain the decisive factor and preserve alternatives for inspection. Test against contract examples while adapters are built.

#### V2-7 Navigation and graphical route summaries
Owner: @Fhuelin (proposed)
Needs: V2-3
Files: src/treatment_planner/ui/navigation.py, src/treatment_planner/ui/recommendation.py, src/treatment_planner/ui/route_summary.py, src/treatment_planner/ui/demo_controls.py, config/theme.toml, tests/test_v2_screen.py, handoff/v2-7-ui.md
Done when: contract examples show sidebar chapters, recommended preselection, three route-control buttons, route arrows/icons and concise risk/delay summaries with expandable details.
Notes: use theme tokens and labels independent of colour; include ship/truck/bicycle/car/hospital/production and environmental icons. No app.py edits during parallel work.

## M3: integrated V2 is reviewable and release-ready

### Chunk D: in order; split implementation and release checks into separate chats

#### V2-8 Integration and release verification
Owner: @philLeu with team review (proposed)
Needs: V2-4, V2-5, V2-6, V2-7
Files: app.py, tests/test_v2_flow.py, docs/SOURCES.md, README.md, docs/v2/release-checklist.md, handoff/v2-8-integration.md; pyproject.toml and generated requirements.txt only if needed
Done when: Live opens by default, all three demo controls affect planning independently, goals update recommendations, changes clear confirmation, and existing scenarios plus offline demo and live-failure paths pass end to end.
Notes: validate navigation and icons on screen with a teammate. Run formatter, lint, relevant tests, documentation checks and privacy guard. Document unresolved source/model limitations. Prepare the release PR only after these checks; merging remains a separate explicit approval.

## Start here

V2-1 and V2-2 can start immediately. Confirm owners, then use a fresh chat per task: "Continue V2-1 from docs/v2/plan.md on the V2 branch. Read the design and branch restrictions first."

Keep V1 plan/history intact. This release's requirements live in docs/v2/design.md, task ownership/dependencies in this file, and task status in handoff files.
