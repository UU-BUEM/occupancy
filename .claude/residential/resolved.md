# Resolved issues & settled decisions — households

Do not re-raise. "BY-DESIGN" are deliberate choices.

## households restructuring — fixed/settled
- `fridge`, `ironing`, `other` were hardcoded in
  `electricity_consumption.py` with no JSON representation → now
  `EquipmentSpec` rows in `households/data/equipment.json` like the other
  4 appliances, driven by the `flat_always_on`/`sessions_per_week`/
  `linear_in_occupants` strategies in `core/equipment.py`. Later expanded
  further — see below.
- **Equipment set expanded from 7 illustrative items to 29 real ones**,
  sourced from the CREST Domestic Electricity Demand Model 1.0e (Richardson,
  Thomson, Infield — Loughborough CREST), obtained directly by the user via
  the paper's own public download link (`data/inputs/*.xlsm`, gitignored,
  not committed to this repo). Checked both `.xlsm` files for an embedded
  license statement (docProps metadata + the `main` instruction sheet) —
  none found. The underlying power/cycle-length statistics on the
  `appliances` sheet are themselves credited to UK Market Transformation
  Programme Briefing Notes ("Crown Copyright", commonly OGL-licensed); the
  occupancy-dependency weighting separately derives from the UK 2000 Time
  Use Survey (UK Data Archive SN:4504), a licensed academic dataset whose
  exact reuse terms weren't independently re-verified. Given this, only
  `ownership_probability`, `rated_power_kw`, and `standby_power_kw` per
  item were taken from the sheet (attributed via each spec's
  `_crest_source` field); the hourly weekday/weekend weight shapes are
  this repo's own arrays (not CREST's 10-minute activity/TPM tables),
  calibrated so each item's expected annual energy roughly matches CREST's
  reported figure. Water heating and Electric Space Heating categories
  (DESWH, electric shower, storage heaters, ...) were deliberately
  excluded — thermal loads belonging to buem's domain, not this repo's;
  including them would double-count against buem's own heating
  calculation. `lighting` was added as one new aggregate item — CREST's
  own dedicated lighting sub-model is evidence lighting is a material
  internal-gain component, but `rated_power_kw` here is a fresh modern-
  LED-era estimate, not CREST's 2008 incandescent/CFL bulb wattages.
- `EquipmentSpec.ownership_probability` (previously unused) is now wired
  up in `ElectricityConsumptionProfile._owned_by_name()` — each household
  draws once, per seed, whether it owns each sub-1.0-probability item.
- `has_*` flags changed from a 1:1 flag→item mapping to 1:many
  (`_LEGACY_FLAG_TO_EQUIPMENT: dict[str, list[str]]`), since e.g.
  `has_fridge` now needs to cover 4 distinct cold-appliance items. Added
  `has_lighting` as a new flag alongside the existing 7.
- `internal_gains/` and `electricity/` (household-only logic) → moved to
  `households/household_profile.py` and `households/electricity.py`.
  Deep import paths removed as a breaking change (package is Alpha);
  `CHANGELOG.md` documents old→new paths.

## BY-DESIGN
- `markov_chain`'s transition-probability data is **not** copied from
  pyCREST/richardsonpy/tsorb (GPLv3), StROBe (unlicensed), or the CREST
  Excel/data download itself (CC BY-NC-ND — noncommercial + no
  derivatives). Those were reviewed for *concept* and *schema* only. The
  default TPM is synthesized at runtime from this repo's own validated
  hourly probability arrays via a documented persistence-blend
  construction (`core/occupancy_engine.py` docstring), explicitly not
  claimed as survey-calibrated.
- Household archetypes are differentiated by **composition**
  (`working_couple`, `family_with_children`, `retired_single`,
  `student_shared`), not by clustered occupancy-pattern categories (see
  `open.md` re: Buttitta & Finn 2020) — a deliberate scoping choice for
  this round, not a rejection of that approach.
