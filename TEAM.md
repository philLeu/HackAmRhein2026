# Team

Track: Manufacturing · Challenge: Open-data-driven material-flow decisions · Repo: https://github.com/philLeu/HackAmRhein2026

## People

<!-- Public file. GitHub usernames only. -->

| GitHub username | Working on (areas, files) |
|---|---|
| @philLeu | app foundation, planning engine and final integration |
| @Fhuelin | domain scenarios and timeline/comparison screen |
| @luapreta-cloud | Rhine dataset investigation already started; Rhine adapter |
| @janaaaaaaaa | weather research, weather adapter and fallback demo |

Task boundaries and files are in docs/plan.md. The team agreed this split.

Special roles: demo owner: @philLeu · time keeper: Optional, to be agreed

## Working rules

- Branches `<type>/<task>-<topic>` (e.g. `feat/t3-csv-upload`), never a person's name; never commit to `main` directly.
- The privacy check must pass before every commit and push. Never `--no-verify`.
- Every change goes through a pull request. Merge only after explicit approval for that PR.
- Merge policy: one other teammate checks each PR, followed by explicit merge approval.
- Sync times: To be agreed.
- Keep `main` working so the demo can run when needed.
- Decisions that affect others: `docs/decisions.md`.
- Secrets in `.env` only. Data sources in `docs/SOURCES.md`.

## Where to see status

Each task's `handoff/` file.
