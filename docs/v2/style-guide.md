# V2 screen style addendum

Status: approved. Inherit the [existing style guide](../style-guide.md) and values
from `config/theme.toml`; retain the agreed dark control-room direction.

- Make the goal and recommendation the strongest visual group. One primary
  action, Confirm plan, follows the concise route summaries.
- Keep the three routes visually separate, with transport icons, directional
  arrows, material labels and status words. Reuse the adopted route sketches.
- Keep evidence, detailed constraints and full timelines behind expandable
  controls. Uncertainty and a blocked confirmation remain visible.
- Use `theme.backgroundColor` for the page, `theme.secondaryBackgroundColor`
  for cards, `surface.border` for grouping and `surface.muted` for supporting
  labels. Interactive emphasis uses `theme.primaryColor`.
- Mode and route statuses always have text; icons and accents support it.
  Existing Rhine-specific colours retain their Rhine meaning and are not
  automatically reused as general recommendation-status colours.
- Native controls retain keyboard focus and meaningful labels. Route cards
  stack on narrow screens; reading order follows ingredient, sample, return.
- All displayed timestamps follow the existing UTC format. Keep durations
  separate from timestamps and write units beside every temperature/delay.
- Copy names the material, route and evidence problem plainly. A recommendation
  is distinct from the user's confirmation; a tied score does not imply one
  candidate is better.

No theme values or application styles change in V2-2. Any new status colour
tokens needed in implementation must be added to the single theme file and
checked for readable contrast during V2-7.
