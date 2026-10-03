# Glossary

Domain terms used in the code and docs, one line each. Code names use these words. Add a term when it first appears in code; remove it when it's no longer used.

| Term | Meaning | Used in |
|---|---|---|
| Treatment request | Non-personal scenario with ingredient order, original collection and planning decision times | interfaces.py |
| Provenance | Source, evidence kind, source timestamp and retrieval timestamp | interfaces.py |
| Courier leg | Hospital-to-factory or factory-to-hospital journey, evaluated independently | interfaces.py |
| Time window | Timezone-aware interval with explicit start and end | interfaces.py |
| Candidate plan | An alternative with modes, timeline events, checks and assumptions | interfaces.py |
| Deadline margin | Deadline minus actual completion or arrival time; zero passes, negative fails | ConstraintResult |
| Unconfirmed | No demonstrated failure, but insufficient evidence to confirm a plan | ResultStatus |
| Fixture | Authored synthetic example with fixed expected results | demo.py |
