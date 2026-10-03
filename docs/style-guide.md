# Demo style guide

The demo uses a control-room direction chosen by @fhuelin: dark surfaces, clear
hierarchy and readable status accents. Values live only in `config/theme.toml`;
`src/treatment_planner/ui/presentation.py` applies them to page surfaces.
`.streamlit/config.toml` inherits that file for native widgets.

## Principles

- Put the scenario, plan choice and result before supporting detail.
- Make uncertainty explicit. Every status has a word as well as a colour.
- Keep transport events and constraints easy to inspect during a presentation.

## Visual roles

`theme.backgroundColor` is the page, `theme.secondaryBackgroundColor` groups summary information,
`theme.textColor` is primary text and `surface.muted` is supporting text.
`theme.primaryColor` highlights metrics and interactive controls; `surface.border`
separates panels. Native headings and body text use `theme.font`, with the
shared `surface.padding` and `surface.radius` for summary cards.

Timelines use `timeline.event_color` for journeys and
`timeline.deadline_color` for dashed deadline markers. Each lane has
`timeline.height_per_lane` of vertical space. Tooltips name every event and deadline.

## Components and language

Use a title and short introductory sentence, followed by a visible synthetic-data
notice, scenario selection, three summary cards and the comparison table.
Show the inspected plan's status as a native success, error or information alert.
Retain native keyboard-operable inputs, tables and expanders. Use concise domain
labels; distinguish authored fixture results from computed planning results.

All displayed instants use `DD.MM.YYYY · HH:mm UTC`, including tables, evidence,
captions, timeline axes and tooltips. Date inputs use `DD.MM.YYYY` and time inputs
use 24-hour time with UTC in the label. Missing timestamps say `Unknown`.
Machine timestamps remain timezone-aware ISO values for chart positioning.

## Readability

Primary and secondary text must have at least 4.5:1 contrast against the dark
surfaces. Keep status words visible and use dashed lines for deadlines, so colour
is never the sole signal. Prefer fewer axis ticks over overlapping timestamps.
The demo and shared comparison screen are the living style references; do not
add isolated colours or repeat theme values in components.
