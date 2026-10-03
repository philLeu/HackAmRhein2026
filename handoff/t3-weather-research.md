# Handoff: T3 Weather source investigation

Status: done · Updated: 2026-10-03 · Branch: docs/t3-weather-handoff · Last owner: @janaaaaaaaa

## Goal
Provide an inspectable Basel forecast sample with temperature, snow-code meaning,
validity intervals, issue time, coverage and licence, as specified in docs/plan.md.

## State
The permitted live capture is committed at
`data/replay/weather/capture-20261003T112609Z/`. It contains 220 real MeteoSwiss
temperature rows and 217 weather-code rows for the 4056 postcode centre (point
ID 405600), from a forecast issued at 2026-10-03 11:00 UTC and retrieved at
11:26 UTC. The selected location, valid intervals, coverage, provenance and CC BY
4.0 attribution are documented in `docs/sources/weather.md` and the capture files.
The former timestamp error came from a capitalized `Date` header; the parser now
handles header case and spacing. Snow-code meanings are verified against the
official PDF, with ambiguous code 133 explicitly retained as unknown. German
short descriptions appear beside the raw code.

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
- Keep code 133 as `unknown` unless MeteoSwiss clarifies its conflicting
  language descriptions.
- Agree a forecast freshness age before live/replay evidence is treated as
  usable; T7 requires the caller to provide this policy.
- The source supplies hourly mean temperature rather than hourly maximum, so it
  cannot confirm the planning rule's maximum-temperature limit. T7 preserves
  the mean separately and leaves the maximum unknown.

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
- Code 133 remains ambiguous in the source; its mapped result is `unknown`.
- The team has not agreed a forecast freshness age.
- Hourly mean temperature does not prove whether an hourly maximum crossed 30°C.
- This capture is a historical snapshot, not a current forecast; re-fetch before
  any live use.
- The offline research suite passes: 18 tests.

## Resume prompt
> Continue from the T3 handoff only to resolve its open data questions. Preserve
> the distinction between the real historical capture and synthetic examples;
> coordinate any freshness or temperature-rule changes with the team.
