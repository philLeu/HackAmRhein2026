# Treatment material-flow planner

> Built at [HackAmRhein 2026](https://hackamrhein.dev) with Codex. First time in this repository? The setup guide is [HACKAMRHEIN.md](HACKAMRHEIN.md).

A planned manufacturing-control prototype for a production coordinator managing one individual treatment. It compares material-flow schedules using Rhine conditions and local weather, showing delivery deadlines and alternatives involving shipping, refrigerated trucks, bicycles and cars.

## The problem

Environmental disruptions can delay ingredients from Rotterdam or block courier journeys between a Basel hospital and production site. The coordinator needs to compare revised plans before these delays affect the treatment timeline. The demo uses an invented planning workflow and synthetic treatment inputs.

The agreed rules and remaining design questions are in [docs/design.md](docs/design.md).

## How to run it

This repository is currently at the design stage; no executable application has been built yet. The first build task will add tested setup and run commands.

## Data sources

See [docs/SOURCES.md](docs/SOURCES.md).

## Limits

Treatment timings, transport durations, availability and disruption effects are demo assumptions. Environmental sources are candidates awaiting integration. The prototype does not make clinical decisions, book transport or process patient records.

## Team

@philLeu, @Fhuelin, @luapreta-cloud, @janaaaaaaaa. See [TEAM.md](TEAM.md) for ownership and working rules, and [docs/plan.md](docs/plan.md) for the proposed task split.
