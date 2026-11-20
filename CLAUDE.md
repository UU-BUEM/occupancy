# CLAUDE.md

Guidance for Claude Code (and other agents) working in this repository.

## What this repo is

`occupancy` generates stochastic hourly occupancy states and electricity-
demand profiles for **households and service buildings**. It is the
intended **intermediate layer** feeding
[UU-BUEM/buem](https://github.com/UU-BUEM/buem), an open-source building
thermal-demand module: buem models only the building envelope (walls, roof,
floor, windows, doors, ventilation, U-values) and takes no occupancy/
internal-gains/electricity input itself — that's this package's job to
supply.

**Ownership boundary (user directive, 2026-08-07):** every occupancy-related
activity — people-presence/activity/sleep state, equipment on/off and power
draw, and any future occupant- or equipment-driven behavior — is modeled
inside *this* package, not downstream. buem owns the envelope/thermal
network and consumes occupancy's output; it should never need to reimplement
occupant- or equipment-behavior logic of its own (e.g. its own internal-
gains-density table) just because occupancy's existing output doesn't yet
cover a given case — extend occupancy instead. This is why, e.g., Gap 1's
floor-area-normalized internal gains (see `to_buem_profiles()`'s
`floor_area_m2`/`gain_w_per_m2`) were implemented on occupancy's side rather
than left to buem to compute independently.

The original design proposal is in
`docs/plans/equipment-service-buildings-architecture.md`, superseded during
implementation; that file points to where the actual rationale now lives:
this file (architecture, extension points), `.claude/open.md` /
`.claude/resolved.md` (research into pyCREST, richardsonpy, tsorb, StROBe,
simpy, mesa; why the Markov-chain generator exists; why simpy/mesa were not
adopted), and `CHANGELOG.md`'s `[Unreleased]` section (breaking changes and
additions).

## Repository layout

```text
occupancy/
├── src/occupancy/
│   ├── __init__.py          # public API: HouseholdProfile, MultiDwellingProfile,
│   │                        #   ServiceBuildingProfile, ElectricityConsumptionProfile,
│   │                        #   OccupancyResult, to_buem_profiles, building_seed,
│   │                        #   generate_dhw_draws, estimate_equipment_usage,
│   │                        #   HOUSEHOLD_ARCHETYPES/SERVICE_BUILDING_TYPES/EQUIPMENT_TYPES,
│   │                        #   + OccupancyProfile = HouseholdProfile (back-compat alias)
│   ├── cli.py                 # occupancy CLI: --building-type/--archetype/--region/...
│   ├── config/                 # CLI-facing ScenarioConfig (JSON scenario files)
│   ├── core/                   # shared engine used by BOTH households and services_buildings
│   │   ├── occupancy_engine.py   # generator-strategy registry (see below)
│   │   ├── equipment.py          # EquipmentSpec + trigger-strategy registry
│   │   ├── loader.py             # importlib.resources JSON loading helpers
│   │   ├── result.py             # OccupancyResult (shared output contract)
│   │   ├── seed.py               # derive_default_seed + building_seed (external-ID seeds)
│   │   ├── disaggregation.py     # estimate_equipment_usage (fit equipment to a supplied elecLoad)
│   │   └── buem_adapter.py       # OccupancyResult -> buem's Q_ig/elecLoad/occ_nothome/occ_sleeping
│   ├── households/             # base __init__.py registers HOUSEHOLD_ARCHETYPES
│   │   ├── archetypes.py         # ArchetypeSpec + registry, loads data/archetypes/*.json
│   │   ├── household_profile.py  # HouseholdProfile
│   │   ├── electricity.py        # ElectricityConsumptionProfile (EquipmentSpec-driven)
│   │   ├── building.py           # MultiDwellingProfile (N distinct households summed)
│   │   ├── dhw.py                # generate_dhw_draws (liters only; not wired into buem)
│   │   ├── crest_tpm.py          # real CREST TPMs backing the markov_chain_crest generator
│   │   └── data/{archetypes/*.json, equipment.json, tpm_crest.json,
│   │             dhw_tapping_categories.csv}
│   ├── services_buildings/     # base __init__.py registers SERVICE_BUILDING_TYPES
│   │   ├── building_types.py     # ServiceBuildingTypeSpec + registry
│   │   ├── building_profile.py   # ServiceBuildingProfile
│   │   ├── {supermarket,office,restaurant,school,hotel,bakery,warehouse,clinic}.py
│   │   │                        #   one thin file per type (8 today)
│   │   └── data/<type>/{schedule.json, equipment.json}
│   └── visualization/
```

## Core data flow

`JSON config` → `ScenarioConfig` (CLI overrides) → `HouseholdProfile` /
`ServiceBuildingProfile` → (household path only) optional
`ElectricityConsumptionProfile` → CSV.

For a multi-dwelling building, use `MultiDwellingProfile`
(`households/building.py`), not one household scaled by the dwelling
count: it sums `n = min(round(dwellings), cap)` distinct, independently
seeded households (cap defaults to 20) and scales the sum by
`dwellings / n`, so dwelling peaks diversify instead of coinciding. For a
portfolio/grid model with real building IDs, pass
`seed=building_seed(building_id, year=year)` (`core/seed.py`) so two
buildings with identical construction inputs don't collide onto the same
default seed. Neither is exposed through the CLI yet (Python API only).

Household and service-building profiles both dispatch to the **same**
`core/occupancy_engine.py` generator registry and `core/equipment.py`
equipment/strategy registry — households and service buildings are two
config-driven consumers of one shared engine, not parallel implementations.

## Extension points (the whole point of this architecture)

- **New household appliance**: add a row to
  `households/data/equipment.json` (37 items today: 29 with CREST-sourced
  ownership/power figures — see `.claude/residential/resolved.md` for
  provenance — plus 8 modern 2026-NL items, mostly estimated and flagged
  `_source: "estimated, unsourced"`; see `.claude/residential/open.md`)
  or a per-archetype override in
  `households/data/archetypes/<name>.json`'s `equipment_overrides`. Only
  write new Python if the trigger logic is genuinely novel — then register
  it via `core.equipment.register_strategy`. Currently registered:
  `probabilistic_event`, `flat_always_on`, `sessions_per_week`,
  `linear_in_occupants`, `overnight_charging_session` (one long daily
  session gated only on a daily probability — `ev_charger`). Household
  items scale with occupant count through the optional per-item
  `occupant_scaling` exponent in `strategy_params` (default `0.0` = no
  scaling; service buildings don't set it yet).
- **New household archetype**: add
  `households/data/archetypes/<name>.json` (probabilities, generator,
  equipment overrides). No code change; `households/archetypes.py` loads
  every JSON file in that folder automatically.
- **New service-building type**: add
  `services_buildings/data/<type>/{schedule.json,equipment.json}` plus a
  thin `services_buildings/<type>.py` that calls
  `load_building_type("<type>")`, then import it from
  `services_buildings/__init__.py`.
- **New occupancy-generation strategy** (e.g. from a future reference
  occupancy module the user supplies): implement a function matching
  `core.occupancy_engine.GeneratorFn` and register it with
  `register_generator`. Currently registered: `binomial_independent`
  (default, original algorithm), `markov_chain` (persistence-parameterized,
  synthesized transitions), `markov_chain_crest` (real CREST hourly
  active-occupant transition matrices for household sizes 1-5, from
  `households/data/tpm_crest.json`; used by `working_couple`; sizes > 5
  fall back to `markov_chain` with a warning), `fixed_schedule` (single open/close window +
  flat peak — most service buildings), `hourly_occupancy_curve` (explicit
  24-hour occupancy-fraction table, weekday/weekend — for building types
  whose day-shape a single rectangle can't represent, e.g. `hotel`'s
  near-continuous overnight-guest presence with checkout/check-in peaks;
  mirrors the shape of published DOE/ASHRAE 90.1 prototype-building
  `Schedule:Compact` fractional schedules more closely than
  `fixed_schedule`).
- **A building type with genuine overnight/sleeping occupants**: set
  `asleep_probabilities` in that type's `schedule.json` (same `(24, 2)`
  shape and semantics as a household archetype's field of the same name —
  conditional probability that a present-but-inactive occupant is asleep).
  Every generator threads it through to a shared `n_asleep` output column,
  which `core.buem_adapter.to_buem_profiles()` consumes directly as
  buem's `occ_sleeping` for *any* building type, not just households —
  see `hotel`'s `schedule.json` for a working example. Building types that
  never set it (most service buildings) simply always have `n_asleep == 0`.

## Conventions

- No hardcoded numeric arrays in Python — everything lives in bundled JSON
  under each subpackage's own `data/`, loaded via `importlib.resources`
  (see `core/loader.py`). There is a single source of truth per subpackage
  — no root-level `configs/` duplicate (that dual-source setup was removed
  during the households/services_buildings restructuring).
- Conventional Commits for commit messages.
- Update `CHANGELOG.md` under `[Unreleased]` for user-facing changes (see
  `CONTRIBUTING.md`).

## Dev commands

```bash
ruff format .
ruff check .
pytest
mypy src
python validate.py
```

## Known limitations / follow-ups

See `.claude/open.md` (cross-cutting), `.claude/residential/open.md`
(households), and `.claude/services/open.md` (service buildings) for the
live lists. Notably:

- `markov_chain`'s transition data is synthesized at runtime from this
  repo's own validated hourly probability arrays (see
  `core/occupancy_engine.py` docstring) — it is **not** calibrated against
  real regional survey data. `markov_chain_crest` replaces only the
  active-occupant-count transitions with real CREST (2008 UK) data; the
  presence/active split and `n_asleep` still come from this repo's own
  illustrative arrays. Sourcing real (e.g. Dutch) time-use survey data is
  flagged as follow-up, not fabricated.
- CLI/config capacity resolution for service buildings only respects the
  `--persons`/`--capacity` CLI flag, not a scenario config file's
  `num_persons` — needs a dedicated `capacity` config field.
- `region` is threaded through the data model (`OccupancyResult.region`,
  archetype/building-type JSON `region` field) but only one region's data
  (`NL`/generic-EU) is populated; adding a new region is a config addition.
