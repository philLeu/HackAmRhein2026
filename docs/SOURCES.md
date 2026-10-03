# Sources

Every dataset, API, notable library and AI tool used, with licence. Feeds the sources slide on Sunday.

| What | Source / URL | Licence or permission | Used for |
|---|---|---|---|
| Codex (OpenAI) | chatgpt.com/codex | Tool, AI-assisted development | Coding assistant |
| MeteoSwiss local forecasts (candidate; not integrated) | https://opendatadocs.meteoswiss.ch/e-forecast-data/e4-local-forecast-data | CC BY 4.0; acknowledge "Source: MeteoSwiss"; terms: https://opendatadocs.meteoswiss.ch/general/terms-of-use | Temperature and weather-type forecasts for courier journey checks; Basel point and snow-symbol mapping pending verification |
| Rhine observations (candidate; not integrated) | https://www.hydrodaten.admin.ch/de/seen-und-fluesse/stationen-und-daten/2289 | Licence and programmatic retrieval still to verify | Basel Rheinhalle river-condition signal; does not establish navigability of the whole Rotterdam–Basel route |

## Research notes (2026-10-03)

- MeteoSwiss documents local forecasts for nine full days including the current day, updated hourly. Parameter files include hourly temperature and weather types representing the preceding three hours. They do not provide direct confirmation that a particular courier route is free of snow. Check time intervals, point identifiers, units and missing values before integration.
- MeteoSwiss forecast data may be reused with attribution under CC BY 4.0. Its weather-symbol graphics are proprietary; use numerical codes/descriptions with our own graphics.
- No datasets have been downloaded or integrated yet. Confirm actual forecast coverage for each planned journey; the ingredient delivery plus treatment cycle can extend beyond the available horizon.
- Synthetic scenarios must be labelled separately from environmental observations. Exact Rhine delay mapping and any route-snow flag are demo inputs until supported by verified evidence.
