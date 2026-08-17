# Superseded — see docs/dhw/

This file's original content (the 2026-08-17 first-pass literature review)
has been expanded into a proper, comprehensive set of documents at
`docs/dhw/`, per the user's explicit request to document this in the
`docs/` folder rather than `.claude/`. Read there instead:

- `docs/dhw/README.md` — index.
- `docs/dhw/sources_reviewed.md` — every paper/source consulted, access
  status, and exactly what was extracted from each (including the
  2026-08-17/18 second pass: Richardson 2008/2009/2010 papers + 2010 PhD
  thesis reviewed for completeness, and McKenna & Thomson 2016 read in
  full this time, not just via secondary sources).
- `docs/dhw/questions_answered.md` — direct answers to the four
  conceptual questions (fixture ownership, draw-duration reuse, what
  "flow rate" means, the cooking-vs-dishwasher scope clarification).
- `docs/dhw/design.md` — the implemented DHW tapping-event model
  (`households/dhw.py`, `households/data/dhw_tapping_categories.csv`),
  every deterministic value it depends on in reviewable tables, and open
  items.
- `docs/buem_engine_reference.md` — how buem's 5R1C engine actually
  consumes occupancy's output today, and where a future DHW energy term
  would (and would not) plug in.

`.claude/open.md`'s "dhw-cooking" cross-repo entry still tracks the
current status pointer; `CHANGELOG.md`'s `[Unreleased]` section has the
user-facing summary of what shipped.
