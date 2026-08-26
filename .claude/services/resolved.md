# Resolved issues & settled decisions — service buildings

Do not re-raise. "BY-DESIGN" are deliberate choices.

## BY-DESIGN
- Service-building occupancy uses `fixed_schedule` (deterministic open/
  close hours + noise) by default, not the residential-style
  `binomial_independent`/`markov_chain` strategies — those model presence
  probability per person, which doesn't fit shift/opening-hours-driven
  building occupancy.
- Households and service buildings share one engine
  (`core/occupancy_engine.py` generator registry, `core/equipment.py`
  equipment registry) rather than parallel implementations — service
  buildings are just another config-driven consumer, not special-cased.
- Most service-building types never set `asleep_probabilities` (defaults
  to all-zero), so `n_asleep` stays `0` for them — deliberate, since
  supermarket/office/restaurant/school/bakery/warehouse/clinic are never
  occupied overnight. **Update (2026-07-29):** `hotel` is the first
  exception — it genuinely needs sleeping occupants, and supplies real
  `asleep_probabilities` through the exact same mechanism households use
  (see the round below). No engine change was required to support it,
  confirming the original "no engine change required" prediction here.

## buem-alignment round (2026-07-28) — fixed/settled
- **Per-building-type `heat_gain_present_kw`/`heat_gain_active_kw`** —
  `services_buildings/building_types.py`'s `ServiceBuildingTypeSpec` gained
  both fields (default 0.100/0.150 kW, matching `core/buem_adapter.py`'s
  old global constants), read from each `schedule.json` and threaded onto
  `OccupancyResult` by `ServiceBuildingProfile.to_result()`. See
  `residential/resolved.md` for the household-archetype side of the same
  change and `open.md` for the remaining calibration caveat.

## activity/equipment profiles round (2026-07-29) — fixed/settled
- **New `hourly_occupancy_curve` generator**
  (`core/occupancy_engine.py`) — an explicit 24-hour occupancy-fraction
  table, for building types whose day-shape `fixed_schedule`'s single
  open/close window + flat peak can't represent. Added because `hotel`
  needed it: near-continuous overnight guest presence plus checkout/
  check-in peaks is not a rectangle. Shaped like DOE/ASHRAE 90.1
  prototype-building `Schedule:Compact` fractional schedules.
  `ServiceBuildingTypeSpec`/`ServiceBuildingProfile` gained
  `asleep_probabilities` plumbing (mirroring households) to support it.
- **Four new building types**: `hotel`, `bakery`, `warehouse`, `clinic` —
  occupant density/operating-hours ballparks sourced from DOE/NREL
  Commercial Reference Building Models (Deru et al. 2011), ASHRAE 90.1
  Table 9.5.1 (lighting power density by building type), and ASHRAE 62.1
  Table 6-1 (occupant density) — see each type's `schedule.json`
  `_comment` for the specific citation. These are hand-interpolated
  between published reference points, not a literal reproduction of any
  single source table — same "illustrative, not survey-calibrated"
  caveat as every other schedule/equipment JSON in this repo. Web search
  for CIBSE Guide A, TABULA/EPISCOPE non-residential, and DOE's raw
  `.idf` `Schedule:Compact` blocks (the exact hour-by-hour source data)
  did not yield usable numbers this round — flagged in `open.md` as a
  concrete follow-up if someone can pull the DOE prototype `.idf` files
  directly (e.g. from `NREL/OpenStudio-Prototype-Buildings` on GitHub)
  rather than via web search.

## hospital/university/glasshouse round (2026-08-20) — fixed/settled
- **Three new building types**: `hospital`, `university`, `glasshouse` —
  see each `schedule.json`/`equipment.json` `_comment` for full citations.
  Summary: `hospital` (24/7 inpatient, distinct from the outpatient
  `clinic` — the exact gap `open.md` flagged since the 2026-07-29 round)
  sources its `occupancy_fraction`, `heat_gain_present_kw`, and
  `gain_w_per_m2` from Ahmed, Akhondzada, Kurnitski & Olesen (2017,
  *Sustainable Cities and Society* 35:134-144) Tables 4-8's "Hospital"
  columns — REHVA Technology and Research Committee-collected schedule
  data feeding the prEN16798-1/ISO 17772-1 standards, the first source in
  this repo's reference set with a genuinely hospital-specific (not
  generic office/school-derived) schedule; its day-shape independently
  matches the real hospital's design occupancy schedule in Dobosi, Tanasa,
  Kaba, Retezan & Mihaila (2019, *E3S Web of Conferences* 111, 06073)
  Figure 5. `university` sources its occupancy day-shape from an ORNL/DOE
  college-building occupancy-schedule study (Bae, Yoon, Jung, Malhotra &
  Im), anchored on that paper's classroom curve (largest single teaching-
  space type by floor area) rather than a formal area-weighted blend of
  all its published space types; it is deliberately *not* a copy of
  `school` — rolling class-registration schedules keep peak occupancy well
  under 50% of capacity (vs. `school`'s single whole-building timetable
  reaching 85%) and push occupancy into the evening, which `school`
  (closes 16:00) never has. `glasshouse` has no cited source at all (see
  `open.md`) — general domain-knowledge illustrative defaults, the first
  type in this package to leave `gain_w_per_m2` unset (`None`) and the
  first to use `strategy_params.gate: "none"` for more than one equipment
  item (climate control, supplemental grow-lighting, and irrigation all
  run on their own schedule, not on occupancy).
- **`hourly_occupancy_curve` bugfix**: a curve cell of exactly `0.0`
  (e.g. an all-zero weekend column — the only way this generator can
  express full weekly closure, since unlike `fixed_schedule` it has no
  `closed_weekends` param of its own) did not stay at `0.0`: Gaussian
  jitter was added unconditionally, so a positive noise draw could give a
  supposedly-closed hour a coin-flip's chance of a few phantom occupants.
  `fixed_schedule` already guarded against the equivalent case (only adds
  jitter when `is_open`); `hourly_occupancy_curve` now does the same
  (`core/occupancy_engine.py`). Caught while adding `university`, the
  first consumer of this generator to rely on an exactly-zero cell for
  closure — `hotel`'s own curve has no zero cells, so it was never
  affected and its behavior is unchanged. Regression test:
  `tests/test_core.py::test_hourly_occupancy_curve_zero_cells_stay_zero_despite_noise`.
