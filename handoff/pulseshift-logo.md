# PulseShift logo

Status: ready for review · Owner: @fhuelin

## State
Separate task branch feat/pulseshift-logo from shared V2 commit 3c61251.
The supplied transparent PNG is preserved in assets/branding/pulseshift.png.
The shared apply_theme header renders it on a light plate with an accessible
label; dimensions and background live in config/theme.toml.
No app.py or shared-contract edits. V2-8 retains the logo by calling apply_theme.

## Next
Open a PR targeting the shared V2 branch.
Teammate review and explicit merge approval remain required.

## Verification
- 29 existing application, comparison and V2 screen tests passed.
- Ruff lint and formatting passed for the changed UI modules.
- Browser verified one accessible logo above the application title, with its
  original proportions and readable wordmark on the light plate.
- The source artwork contains no personal information or credentials; the
  supplied PNG is copied unchanged. Screenshots stay in ignored .hack/.

## Decision queued for integration
- 2026-10-03 · Show the supplied PulseShift logo in the shared page header
  on a light plate, preserving the transparent source asset · @fhuelin ·
  Affects: branding, V2-8 · Why: identify the application and keep its dark
  wordmark readable on the approved dark theme.
