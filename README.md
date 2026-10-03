# Treatment material-flow planner

> Built at [HackAmRhein 2026](https://hackamrhein.dev) with Codex. First time in this repository? The setup guide is [HACKAMRHEIN.md](HACKAMRHEIN.md).

A manufacturing-control prototype for a production coordinator managing one individual treatment. The integrated demo generates alternative schedules with the planning engine, editable route inputs and explicit plan selection. It runs offline with synthetic walkthroughs or saved provider evidence.

## The problem

Environmental disruptions can delay ingredients from Rotterdam or block courier journeys between a Basel hospital and production site. The coordinator needs to compare revised plans before these delays affect the treatment timeline. The demo uses an invented planning workflow and synthetic treatment inputs.

The agreed rules and remaining design questions are in [docs/design.md](docs/design.md).

## How to run it

Use Python 3.12 and run these commands from the repository root. Dependencies stay in the local, ignored virtual environment. requirements.txt pins the resolved dependencies; pyproject.toml declares the project and development tools. No activation is required.

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

macOS/Linux:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1
```

Open http://localhost:8501. In **Synthetic walkthrough**, choose Baseline, Low water, Hot return, Snow or Missing weather. Inspect an alternative, check its reasons and margins, then select a confirmed plan. Full and treatment-period timelines include preparations and deadline markers. Route edits automatically recompute alternatives and clear selection.

Choose **Saved provider replay** to inspect the archived Rhine and MeteoSwiss captures offline. The historical evaluation clock and adjustable freshness inspection controls are shown on screen. Provider issues remain visible; hourly mean temperature is never substituted for maximum temperature. Source attribution and synthetic assumptions appear in both modes.

Above the plan comparison, click **Basel Rhine conditions** to expand the historical and predicted chart. The summary uses the notebook's classes and shows the worst future median class in the selected window. **Rhine chart evidence** defaults to saved forecast replay; choose **Live Rhine conditions** to fetch public observations and the BAFU forecast. This evidence has its own labelled clock and does not alter the synthetic planning delays. The chart shows uncertainty bands, restriction zones and near-threshold texture. Forecast dates beyond coverage remain unknown.

### Checks

Windows:

```powershell
.venv\Scripts\python.exe -m ruff format --check app.py src tests
.venv\Scripts\python.exe -m ruff check app.py src tests
.venv\Scripts\python.exe -m pytest -q
```

On macOS/Linux, use `.venv/bin/python` instead. Contract, adapter, planning and end-to-end screen tests cover shared models, deadlines, changed-input selection and offline evidence. To update dependencies, install through the project manifest and regenerate requirements.txt with `python -m pip freeze --exclude-editable` inside the project environment; never include editable-install paths or private local configuration.

## Data sources

See [docs/SOURCES.md](docs/SOURCES.md).

## Limits

Treatment timings, transport durations, availability and disruption effects are demo assumptions. The synthetic walkthrough explicitly assumes renewed route checks at dispatch for unedited synthetic entries. Edited manual entries retain their evidence limits. Saved-provider replay uses a historical clock, requires renewed future route checks and preserves missing/stale/outside-horizon data. Freshness controls are for inspection; no operational policy is claimed. Weather issues across candidate journey envelopes conservatively affect bicycle alternatives. The finite alternative set is unranked and is not exhaustive optimisation. There is no live weather integration or automatic network fallback. The prototype does not make clinical decisions, book transport or process patient records.

## Team

@philLeu, @Fhuelin, @luapreta-cloud, @janaaaaaaaa. See [TEAM.md](TEAM.md) for ownership and working rules, and [docs/plan.md](docs/plan.md) for the proposed task split.
