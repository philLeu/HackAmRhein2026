# Treatment material-flow planner

> Built at [HackAmRhein 2026](https://hackamrhein.dev) with Codex. First time in this repository? The setup guide is [HACKAMRHEIN.md](HACKAMRHEIN.md).

A manufacturing-control prototype for a production coordinator managing one individual treatment. PulseShift compares checked plans, recommends alternatives for a chosen goal, and requires explicit confirmation. It opens with live environmental evidence and offers a fixed, offline demo.

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

Open http://localhost:8501. **Live** is selected first. It fetches Rhine and MeteoSwiss evidence and shows source gaps without substituting simulated data. Manual route snow and car availability start unknown; enter current checks before relying on a plan. **Refresh live evidence** gets a new provider snapshot and advances the evaluation clock while keeping the treatment order and pickup inputs.

Switch to **Demo** for an offline walkthrough with a fixed 01.11.2026 clock. The three route buttons edit simulated Rhine level, outbound conditions and return conditions independently. A low Rhine level illustrates a 12-hour delivery delay; snow or heat can change eligible courier modes. Choose a planning goal, inspect the recommendation and routes, and explicitly confirm a plan. Input or goal changes clear confirmation; **Reset demo** restores all fixture inputs. The sidebar opens the Plan, Routes & conditions, and Sources & assumptions chapters. Detailed alternatives and timelines stay available on demand.

On **Sources & assumptions**, expand **Basel Rhine conditions** for the historical replay chart or request the chart's separately labelled live evidence. That chart does not set a planning delay.

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

Treatment timings, transport durations and the Rhine-level-to-delay effect are synthetic assumptions. Demo assumes renewed clear-route checks at dispatch. Live manual route checks, maximum temperature, freshness and forecast horizon may remain unknown, so some plans cannot be confirmed. Weather issues across candidate journey envelopes conservatively affect bicycle alternatives. Goal ranking covers the finite generated set, not exhaustive optimisation or a calibrated failure probability. The prototype does not make clinical decisions, book transport or process patient records.

## Team

@philLeu, @Fhuelin, @luapreta-cloud, @janaaaaaaaa. See [TEAM.md](TEAM.md) for ownership and working rules, and [docs/plan.md](docs/plan.md) for the proposed task split.
