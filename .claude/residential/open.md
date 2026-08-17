# Open issues / TODOs — households

## >>> NEXT MAJOR TASKS <<<
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
- [households] **`asleep_probabilities` is hand-authored, not calibrated**
  — see `resolved.md` for the `n_asleep`/`asleep_probabilities` addition
  itself. The per-archetype curves (peak overnight, `student_shared`
  shifted later, `retired_single` with a midday-nap allowance) are
  illustrative, same caveat as `home_probabilities`/`active_probabilities`
  above. If/when the Buttitta & Finn 3-state (Active/Non-Active/Absent)
  approach is adopted, it would likely subsume `asleep_probabilities`
  entirely rather than sit alongside it — revisit together.
- [households] **Per-archetype `heat_gain_present_kw`/`heat_gain_active_kw`
  values are illustrative** (ISO 7730 / ASHRAE Fundamentals Ch. 18-informed
  ballparks, not survey-calibrated) — see `resolved.md` and
  `services/open.md`'s matching note for building types.
