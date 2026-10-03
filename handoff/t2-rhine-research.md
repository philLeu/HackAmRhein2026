# Handoff: T2 Rhine source investigation

Status: done · Updated: 2026-10-03 · Branch: data/t2-rhine-research · Last owner: @philLeu

## Goal
Make the existing investigation inspectable as T2 source notes and a permitted
sample with station, parameters, units, timestamps, retrieval and licence.

## State
Converted @luapreta-cloud's notebook into T2's assigned files. The original
notebook is unchanged. Five saved observation rows are available for offline
inspection with provenance. No T6 adapter or forecast replay is implemented.

## Done
- Verified dataset 100089's station, units, 240 m datum and CC0 licence.
- Extracted the five displayed rows; did not reconstruct the reported 573 rows.
- Documented retrieval, observed coverage, original retrieval time unknown,
  forecast endpoint and one verified run's issue time/horizon.
- Separated official high-water descriptions, unverified notebook rules and
  a proposed synthetic delay mapping.

## Next (in order, concrete)
1. Review these T2 outputs with a teammate before merging this branch.
2. Start T6 against the shared interface after T1 and T2 are merged.
3. Implement observation/replay validation and explicit missing/stale/outside-
   horizon results. Validate forecast traces if using the forecast candidate.
4. T9 links docs/sources/rhine.md from the shared source index at integration.

## Files
- `docs/sources/rhine.md`: source, permissions, findings and limits.
- `data/replay/rhine/observations.csv`: five saved observations, displayed precision.
- `data/replay/rhine/manifest.json`: station, units, coverage and extraction provenance.
- `data/replay/rhine/source-metadata.json`: selected verified public metadata.
- `Rhein_water_first_try.ipynb`: original investigation, unchanged.

## Decisions made
No shared interface or domain configuration changed. The 24-hour low-water
delay is a proposal only, not an adopted team rule.

## Open questions / problems
- The original observation retrieval time is not saved in the notebook.
- The draft offset, vessel loading claims and 620/670 cm rules need further
  authoritative verification before operational use.
- A single Basel gauge does not confirm whole-route navigability or delay.
- The forecast JSON structure may change; the discharge endpoint is unverified.

## Resume prompt
> Continue from T2's completed research. Read handoff/t2-rhine-research.md and
> docs/sources/rhine.md on data/t2-rhine-research. For T6, check T1/T2 are merged
> and read the shared interface before implementing the Rhine adapter.
