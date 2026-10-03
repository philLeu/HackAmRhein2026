# Handoff: consistent timestamps and demo visual polish

Status: done · Updated: 2026-10-03 · Branch: feat/demo-visual-polish · Last owner: @fhuelin

## Goal
Use one date/time presentation across the application and improve the demo's appearance.

## State
Dark control-room direction chosen by @fhuelin. Presentation covers the authored fixture app and reusable T8 comparison components. T9 integration remains separate. Synced with main after the Rhine research and weather freshness/coverage fix.

## Done
- One timezone-aware UTC formatter for captions, evidence, event/deadline tables, chart axes, tooltips and accessible descriptions.
- Date inputs use DD.MM.YYYY; time inputs explicitly use 24-hour time.
- Native Streamlit widgets inherit config/theme.toml through .streamlit/config.toml; custom panels share that palette.
- Summary cards, clearer introductory copy, labelled status alerts and roomier timelines with dashed deadlines.
- Style guide and team decision recorded.
- Full tests pass; changed Python files pass Ruff and formatting. Repository-wide lint has existing findings in skill templates, weather processing and weather tests.

## Next
1. Teammate review of the demo-polish PR.
2. Merge only after explicit approval for that PR and teammate review.

## Files
- src/treatment_planner/ui/formatting.py: timestamp presentation.
- src/treatment_planner/ui/presentation.py: theme application.
- app.py and existing UI modules: display changes.
- config/theme.toml and docs/style-guide.md: single theme source and visual guidance.

## Resume prompt
> Review feat/demo-visual-polish and its PR; keep T9 integration separate and ask before merging.
