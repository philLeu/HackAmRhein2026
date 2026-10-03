# Treatment material-flow planner

> Built at [HackAmRhein 2026](https://hackamrhein.dev) with Codex. First time in this repository? The setup guide is [HACKAMRHEIN.md](HACKAMRHEIN.md).

A manufacturing-control prototype for a production coordinator managing one individual treatment. The current foundation displays fixed, labelled synthetic examples of material-flow schedules; live environmental adapters and generated alternatives are later tasks.

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

Open http://localhost:8501. Choose Baseline, Low water or Hot return, then inspect a plan. The full timeline and treatment-period detail show authored T4 events and expected margins. This preview uses no live data, books nothing and does not recalculate changed user inputs.

### Checks

Windows:

```powershell
.venv\Scripts\python.exe -m ruff format --check app.py src tests
.venv\Scripts\python.exe -m ruff check app.py src tests
.venv\Scripts\python.exe -m pytest -q
```

On macOS/Linux, use `.venv/bin/python` instead. The contract tests register the synthetic providers and comparator; adapter and engine owners add their implementations there when ready. To update dependencies, install through the project manifest and regenerate requirements.txt with `python -m pip freeze --exclude-editable` inside the project environment; never include editable-install paths or private local configuration.

## Data sources

See [docs/SOURCES.md](docs/SOURCES.md).

## Limits

Treatment timings, transport durations, availability and disruption effects are demo assumptions. The T1 comparator rejects changed inputs rather than presenting fixture results as fresh calculations. Environmental sources are candidates awaiting integration. Fixed outcomes assume renewed route checks at dispatch; a clear entry at order time does not prove a future route is clear. Full route inputs, generated alternatives, no-feasible-plan scenarios and live data arrive in T5–T9. The prototype does not make clinical decisions, book transport or process patient records.

## Team

@philLeu, @Fhuelin, @luapreta-cloud, @janaaaaaaaa. See [TEAM.md](TEAM.md) for ownership and working rules, and [docs/plan.md](docs/plan.md) for the proposed task split.
