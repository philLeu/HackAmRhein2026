# T10 offline fallback handoff

Status: in progress · Updated: 2026-10-03 · Branch: feat/t10-offline-fallback · Owner: @janaaaaaaaa

## Goal

Make the full comparison demonstrable offline and prepare a visual fallback if
the app fails.

## Done

- Added the offline walkthrough, expected deadline outcomes, uncertainty labels,
  and screenshot capture list to `docs/demo-checklist.md`.
- Added `docs/demo-fallback.svg`, a static result explanation for the baseline,
  low-water recovery, hot-return alternative and historical replay limits. It is
  labelled as a fallback illustration, not an app screenshot.
- Confirmed T9 is merged on `main`; its handoff reports 105 passing tests, nine
  end-to-end checks including blocked external network access, and a browser
  preview.
- Ran a local Python smoke walkthrough with socket connections to external
  hosts blocked. Baseline margins matched 96/11/6/6 h; low-water margins were
  −5 h at the original collection and +6 h at +12 h; hot-return and snow
  scenarios retained alternatives; saved-provider evidence stayed unknown and
  reported stale weather coverage.

## Still needed

This environment has Python 3.14 but no supported Python 3.12 runtime, Streamlit,
pytest or browser window. I could not run the T9 AppTest or capture actual app
screenshots here. The static fallback is ready. Run the README setup and the
checklist on a Python 3.12 workstation, then save the three actual app screenshots
outside Git or in an ignored local directory before marking T10 complete.
