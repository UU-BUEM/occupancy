# Open issues / TODOs — households

## >>> NEXT MAJOR TASKS <<<
- [core] **Source real regional TPM survey data** for `markov_chain` —
  currently the transition matrix is synthesized at runtime from this
  repo's own hourly probability arrays (persistence-blended binomial pmf,
  see `core/occupancy_engine.py` docstring), not calibrated against a real
  survey. Only `working_couple` uses it today; other archetypes still use
  `binomial_independent`. Do not copy TPM data from pyCREST/richardsonpy/
  tsorb (GPLv3). Note the two official CREST Excel tools obtained directly
  (`data/inputs/CREST_Domestic_electricity_demand_model_1.0e.xlsm`,
  `Domestic_Lighting_Model_1.0e.xlsm` — gitignored, not committed) contain
  `tpm1-5_wd`/`tpm1-5_we` sheets with the real TPM data; these carry no
  embedded license statement (checked docProps + `main` sheet, none
  found), unlike the separate EEDAL 2009 conference paper PDF which *is*
  explicitly CC BY-NC-ND (noncommercial, no derivatives) for the writeup
  itself — don't conflate the two. If real TPM calibration happens, use
  these files as the source and document the resulting data's provenance
  the same way `equipment.json` does now (see `resolved.md`).
- [households] **More archetypes / real calibration** — the 5 current
  archetypes (`generic`, `working_couple`, `family_with_children`,
  `retired_single`, `student_shared`) have illustrative, hand-authored
  probability arrays, explicitly not survey-calibrated (each JSON file
  says so in `_comment`). Real data is a follow-up.
- [households] **Consider an "occupancy-pattern" archetype axis, distinct
  from household composition** — Buttitta & Finn (2020, *Energy &
  Buildings* 206:109577, "occupancy-integrated archetypes") cluster UK TUS
  2015 diary data directly into 6 categories independent of household
  size/composition: 5 weekday patterns (OP1 Daily absence, OP2 Working
  hours absence, OP3 Lunchtime absence, OP4 Constant presence 1, OP5
  Constant presence 2) + 1 weekend pattern, via k-modes clustering, then a
  **3-state** (Active/Non-Active/Absent) first-order Markov chain with a
  transition matrix per category per 10-min step (144 steps/day) — no
  dependence on occupant count at all (a deliberate simplification vs.
  CREST, since heating demand tracks occupied/unoccupied periods more than
  headcount). This is a genuinely different, complementary axis to our
  composition-based archetypes (`working_couple`, `family_with_children`,
  ...) and could be added alongside them (e.g. an `occupancy_pattern`
  field cross-cut with `archetype`) once real data is sourced. Concept/
  methodology only — no data or code from the paper may be reused (no
  stated OA license on the paper text itself; MATLAB implementation is
  "available for download" via Mendeley Data but licensing wasn't
  confirmed, so treat as not reusable until checked).
- [households] Only `working_couple` demonstrates `markov_chain`; the
  rest use `binomial_independent`. Intentional scoping, not a bug.
