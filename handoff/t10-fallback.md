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
- Installed Python 3.12.15 and the pinned project dependencies in the ignored
  local `.venv`.
- Ran the project checks on Python 3.12: Ruff format check and lint passed,
  `pytest -q` passed all 105 tests, and `scripts/doc-check.sh` reported clean.
- The end-to-end suite exercised baseline selection and timeline updates,
  low-water delay recovery, hot-return and snow alternatives, missing evidence,
  and saved-provider replay with external network connections blocked.
- A separate local smoke walkthrough confirmed baseline margins of 96/11/6/6 h,
  low-water margins of −5 h and +6 h after a 12 h shift, and the replay's
  unknown/stale evidence labels.

## Still needed

The app and offline replay are verified by the AppTest suite. The three actual
app screenshots have not yet been captured. Capture them outside Git or in an
ignored local directory before marking T10 complete; the static SVG fallback is
ready if the app fails during the demo.
