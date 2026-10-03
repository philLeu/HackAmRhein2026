# Handoff: T3 Weather source investigation

Status: in progress · Updated: 2026-10-03 · Branch: data/t3-weather-research · Last owner: @janaaaaaaaa

## Goal
Provide an inspectable Basel forecast sample with temperature, snow-code meaning,
validity intervals, issue time, coverage and licence, as specified in docs/plan.md.

## State
Work is in a separate writable local clone. The original checkout is read-only in
this environment. A standalone downloader, CSV export, readable HTML table and
source notes are ready. A live capture has 220 real MeteoSwiss rows for Basel
postcode 4056, issued at 2026-10-03 11:00 UTC. The former timestamp error came from
a capitalized `Date` header; the parser now handles header case and spacing.
Snow-code meanings are verified from the official PDF, with code 133 explicitly
unresolved. German short descriptions are now included beside the raw code.

## Done
- Read the task boundaries and current decisions at repository commit b3caddb.
- Confirmed provider timestamps are UTC interval ends; temperature uses the prior
  hour and weather type the prior three hours.
- Activated the privacy hooks in this working copy.
- Implemented metadata-based postcode lookup, same-run asset selection, separate
  validity intervals, missing/invalid statuses and source provenance.
- Saved a four-row synthetic example; it is visibly labelled and has no fake
  retrieval timestamp. It now demonstrates the verified code mapping.
- Tested run selection, point-type collisions, Celsius metadata, missing values,
  duplicate timestamps, coverage gaps, the DST transition, output overwrite
  rejection and network failure without fabricated fallback.
- Found the official symbol-description PDF and added a source-linked mapping
  of day/night snowfall and mixed precipitation. Tests cover snow, rain,
  unknown codes and the contradictory language descriptions for code 133.
- Reproduced the user's timestamp failure with `Date` headers; corrected header
  normalization and verified both parameter CSVs through capture generation.
- Retrieved and saved the live sample in
  `data/replay/weather/capture-20261003T112609Z/`.
- Added German code descriptions to forecast CSV and HTML output; refreshed the
  saved capture's derived table without modifying its downloaded-input hashes.

## Next
1. Inspect the live preview and confirm the German descriptions are useful.
2. Ask the provider about code 133 if clarification becomes available; until then
   preserve `unknown`. Agree the forecast freshness policy with the team.
3. Implement T7 only after T1 provides the shared interface and T3 is complete.

## Files
- docs/sources/weather.md: source notes and standalone run/test commands.
- data/replay/weather/fetch_basel_weather.py: live capture and explicit example CLI.
- data/replay/weather/weather_csv.py: provider CSV selection and normalization.
- data/replay/weather/snow_codes.json: verified mapping and code 133 exception.
- data/replay/weather/test_weather_research.py: meaningful offline checks.
- data/replay/weather/example-input/: labelled synthetic provider-format inputs.
- data/replay/weather/synthetic-example/: generated table, CSV and provenance.
- handoff/t3-weather-research.md: this task's current state.

## Decisions made
No shared interface, transport rules or shipment clocks have been changed.

## Open questions / problems
- A genuine forecast sample has not been retrieved.
- Code 133 remains ambiguous in the source; other documented snow codes are
  mapped. The forecast freshness policy still needs agreement.
- Git commits require the verified private GitHub noreply address; files can be
  prepared and checked without committing.
- T1 has not provided the application dependency workflow or formatter. No
  third-party package was installed; do not claim formatter or live tests passed.
- The original checkout remains unchanged. Task files are staged in this working
  clone, and a transferable patch is saved outside the repository. No commit,
  push or merge has been made. Documentation and privacy checks passed.

## Resume prompt
> Continue T3 from handoff/t3-weather-research.md on data/t3-weather-research.
> Follow Next, preserve the distinction between synthetic examples and real data,
> and leave timing assumptions and shared interfaces to their task owners.
