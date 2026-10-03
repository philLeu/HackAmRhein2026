# Demo style guide

The demo uses dark surfaces, clear hierarchy and readable status accents. The
comparison gives every option an expandable route sketch so the material
journey is visible beside its timing detail. Values live only in
`config/theme.toml`; `src/treatment_planner/ui/presentation.py` applies them to
page surfaces. `.streamlit/config.toml` inherits that file for native widgets.

## Principles

- Show the material routes and production steps before deadline detail.
- Put the scenario, plan choice and result before supporting detail.
- Make uncertainty explicit. Every status has a word as well as a colour.
- Keep transport events and constraints easy to inspect during a presentation.

## Visual roles

`theme.backgroundColor` is the page, `theme.secondaryBackgroundColor` groups summary information,
`theme.textColor` is primary text and `surface.muted` is supporting text.
`theme.primaryColor` highlights metrics and interactive controls; `surface.border`
separates panels. Native headings and body text use `theme.font`, with the
shared `surface.padding` and `surface.radius` for summary cards.

Route sketches use `theme.primaryColor` for arrows and the center transport or
production node, `theme.secondaryBackgroundColor` for route nodes and
`surface.border` for their outlines. Each sketch has text labels as well as
arrows, so colour is not needed to understand a route. Timelines use
`timeline.event_color` for journeys and
`timeline.deadline_color` for dashed deadline markers. Each lane has
`timeline.height_per_lane` of vertical space. Tooltips name every event and deadline.

## Components and language

The shared page header displays the supplied PulseShift logo from
`assets/branding/pulseshift.png`. Preserve its transparency and proportions.
Use the light `branding.background` plate to keep the dark wordmark readable
on the control-room theme; `branding.width` and `branding.padding` govern size.
The compact header keeps the planning goal near the first screenful.
The image has an accessible company-logo label. V2-8 should continue calling
`apply_theme` at the page header to retain this branding. Nested components
use `show_logo=False` when applying the theme again.

Use a title and short introductory sentence, followed by a visible synthetic-data
notice, scenario selection, a four-step material-flow sketch for every
option and the comparison table. Explain sample pickup timing in words: “Original
scheduled pickup time (0 h later)” means there is no shift from the hospital's
original collection time.
Show the inspected plan's status as a native success, error or information alert.
Retain native keyboard-operable inputs, tables and expanders. Use concise domain
labels; distinguish authored fixture results from computed planning results.

All displayed instants use `DD.MM.YYYY · HH:mm UTC`, including tables, evidence,
captions, timeline axes and tooltips. Date inputs use `DD.MM.YYYY` and time inputs
use 24-hour time with UTC in the label. Missing timestamps say `Unknown`.
Machine timestamps remain timezone-aware ISO values for chart positioning.

## V2 guided components

The V2 components follow [the approved screen sketch](v2/ui-sketch.md) and
[its style addendum](v2/style-guide.md). Goal and recommendation lead the Plan
chapter, followed by three concise route cards. Full material-flow diagrams,
evidence, alternatives and timelines remain expandable even after confirmation.
Each route uses a transport icon, the shared route drawing and a written status;
unknown delay remains “Delay unknown”. Demo carry-over is a small visible note
with old/new intervals in details. The original baseline is a separate reference,
while the coordinator's confirmed plan has an explicit acknowledgement.

The V2 entry point wires these components to the planning engine. `route.card_width` controls
native wrapping of V2 route cards; `route.label_font_size` keeps the shared SVG
labels readable. Both values live in the existing theme file. Demo buttons use
native wrapping containers so full route names remain visible on narrow screens.

## Readability

Primary and secondary text must have at least 4.5:1 contrast against the dark
surfaces. Keep status words visible and use dashed lines for deadlines, so colour
is never the sole signal. Prefer fewer axis ticks over overlapping timestamps.
The demo and shared comparison screen are the living style references; do not
add isolated colours or repeat theme values in components.
