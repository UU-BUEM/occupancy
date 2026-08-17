# DHW / cooking heat-demand documentation

Answers buem's `dhw_cooking_heat_handoff.md` ask. Read in this order:

1. **`sources_reviewed.md`** — every paper/source consulted, its access
   status, and exactly what was extracted from it and where it's used.
   Written for direct reuse in a journal-paper citation list.
2. **`questions_answered.md`** — direct answers to the conceptual
   questions that gated this work: does fixture ownership matter, can
   draw duration reuse the kitchen-equipment timing signal, what does
   "flow rate" mean and how does it drive heat demand, and confirmation
   of the "cooking" scope (excludes dishwasher/washing machine).
3. **`design.md`** — what was actually built (`generate_dhw_draws()`,
   `dhw_tapping_categories.csv`), every deterministic value it relies on
   in one reviewable table, and the open items/follow-ups still needed.

See also `../buem_engine_reference.md` — how buem's 5R1C thermal engine
actually consumes occupancy's output today, and precisely where (and
where not) a future DHW energy term would plug in. Not DHW-specific on
its own, but written primarily to answer the DHW-scoping question "does
this even reach buem's thermal solve" (no, and won't until buem's own
future update — see that doc).

## Quick orientation

- **Implementation**: `src/occupancy/households/dhw.py`,
  `src/occupancy/households/data/dhw_tapping_categories.csv`.
- **Tests**: `tests/test_dhw.py`.
- **Public API**: `occupancy.generate_dhw_draws`,
  `occupancy.households.dhw.load_tapping_categories`,
  `occupancy.households.dhw.REFERENCE_NUM_PERSONS`.
- **Output contract**: liters per hour, per fixture and total — never
  kWh (see `questions_answered.md` §3 for why that line is drawn there).
- **Not yet done**: wiring into `to_buem_profiles()` or any household's
  default `.generate()` output (deliberately opt-in — see `design.md`);
  service-building DHW; real per-fixture ownership (uses a household-size
  scaling shortcut instead — see `design.md`'s open items).
