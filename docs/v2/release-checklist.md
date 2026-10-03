# V2 release checks

## Verified in the integration branch

- Live is the default evidence mode. Source failures and coverage gaps remain visible; no simulated fallback is applied.
- The three Demo route controls affect planning independently. A low simulated Rhine level adds the documented 12-hour delay; unknown level leaves ship plans unconfirmed. Snow and heat can block bicycle alternatives.
- All generated candidates are ranked for the selected goal. Equal leaders require an explicit choice, and confirmation clears when the goal, inputs or evidence change.
- The fixed Demo clock, Reset demo, sidebar navigation, optional detail and offline chart replay are covered by the end-to-end tests.
- Run `.venv/Scripts/python.exe -m pytest -q`, Ruff format and lint checks, `bash scripts/doc-check.sh` and `bash scripts/hack-guard.sh --staged` before the PR.

## Before the release PR into main

- A teammate checks the Plan and Routes chapters on desktop and narrow screens, including keyboard access and written status next to each icon.
- Review the V2 task PR, then merge it into `feat/v2-treatment-planner` only with explicit approval for that PR.
- Run the full checks on the shared V2 branch and review the live-source and synthetic-model limits in [SOURCES.md](../SOURCES.md). Open the release PR only after these checks; merge that PR only with explicit approval.

## Model and source limits

Treatment clocks, process durations and the demo Rhine delay are illustrative. MeteoSwiss hourly means cannot establish a journey maximum, future manual route status needs renewal, and one Basel gauge does not establish Rhine route navigability. The risk score compares deadline margins; it is not a probability.
