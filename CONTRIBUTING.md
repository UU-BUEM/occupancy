# Contributing

Thank you for contributing to occupancy.

## Development Setup

```powershell
# Creates the conda environment and installs the package in editable mode:
.\setup.ps1          # PowerShell
setup.bat            # CMD

conda activate occupancy_env
occupancy --help
```

> **Do not run `conda develop src`.**  Use `pip install -e . --no-deps` from
> the repo root instead (this is what `setup.ps1` does automatically).

## Config Files

All default numerical parameters live in bundled JSON under each
subpackage's own `data/` folder — edit these instead of touching Python
source:

- `src/occupancy/households/data/archetypes/*.json` — per-archetype
  occupancy probabilities, generator strategy, equipment overrides
- `src/occupancy/households/data/equipment.json` — household appliance
  specs
- `src/occupancy/services_buildings/data/<type>/schedule.json` /
  `equipment.json` — per building-type schedule and equipment specs
- `src/occupancy/config/data/default_scenario.json` — CLI scenario
  defaults (year, persons, building type, flags)

To test a custom scenario, pass `--config <path>` on the CLI or call
`load_scenario_config(path)` in Python. To add a new appliance, household
archetype, or service-building type, see [Extending
occupancy](#extending-occupancy) below — it's a config addition, not a
Python change.

Keep numbers out of Python: every probability array, power figure and
schedule belongs in the subpackage's own `data/` folder, loaded via
`importlib.resources` (`core/loader.py`). Each subpackage has exactly one
source of truth for its data.

## Scope: What Belongs in occupancy

occupancy is the layer between building envelopes and occupants: it feeds
[UU-BUEM/buem](https://github.com/UU-BUEM/buem), which models only the
envelope and thermal network. Everything driven by occupants or their
equipment is modeled here, not downstream:

- **occupancy owns behavior**: who is present, active or asleep, which
  equipment runs and how much power it draws, hot-water volumes and their
  timing, and any future occupant- or equipment-driven signal.
- **buem owns physics**: the envelope, temperatures and temperature
  differences, and conversion to thermal energy (e.g. turning hot-water
  liters into kWh).

For electric vehicles, occupancy owns the driving and charging
*behaviour* (trips, when the car is home and plugged in, the uncontrolled
charging profile). The EV battery and chargers as optimisable technologies
(cost, lifetime, degradation) belong in conversion-technologies; see
`docs/ev/design.md`.

If a downstream model needs an occupant- or equipment-driven input that
occupancy doesn't produce yet, extend occupancy rather than
reimplementing that behavior downstream. For example, floor-area-based
internal gains (`to_buem_profiles(floor_area_m2=...)` with each building
type's `gain_w_per_m2`) were added here instead of letting buem keep its
own gains-density table.

## Extending occupancy

Households and service buildings share one engine: the generator registry
in `core/occupancy_engine.py` and the equipment-strategy registry in
`core/equipment.py`. Most extensions are a JSON addition. Write Python only
when the behavior itself is new. All paths below are relative to
`src/occupancy/`.

- **New household appliance**: add a row to
  `households/data/equipment.json`, or override it for one archetype in
  `households/data/archetypes/<name>.json`'s `equipment_overrides`. Record
  where each ownership and power figure comes from; mark estimates as
  `_source: "estimated, unsourced"` rather than presenting them as
  measured. To make an appliance's use grow with household size, set
  `occupant_scaling` (an exponent from `0.0` to `1.0`) in its
  `strategy_params`.
- **New equipment trigger logic**: only if no existing strategy fits,
  write a function matching `core.equipment.StrategyFn` and register it
  with `core.equipment.register_strategy`. Registered today:
  `probabilistic_event`, `flat_always_on`, `sessions_per_week`,
  `linear_in_occupants`, `overnight_charging_session`.
- **Electric vehicles** are not appliance rows: an EV is a stateful
  battery whose charging is not an internal heat gain, so it has its own
  model (`core/ev.py`) and parameters (`households/data/ev.json`). Change
  EV behaviour there, or per call through `ev_config=` overrides (e.g.
  survey distributions). Keep every EV quantity out of `total_power_kwh`.
  See `docs/ev/design.md`.
- **New household archetype**: add
  `households/data/archetypes/<name>.json` (occupancy probabilities,
  generator, equipment overrides). Every JSON file in that folder is
  loaded automatically; no code change.
- **New service-building type**: add
  `services_buildings/data/<type>/schedule.json` and `equipment.json`,
  plus a short `services_buildings/<type>.py` that calls
  `load_building_type("<type>")` (copy `bakery.py`), and import it in
  `services_buildings/__init__.py`.
- **Building type with overnight occupants**: set `asleep_probabilities`
  in its `schedule.json` (a `(24, 2)` array, as in household archetypes:
  the probability that a present but inactive occupant is asleep). It
  then appears as `n_asleep` and as buem's `occ_sleeping`. See `hotel`
  for a working example; types without it always have `n_asleep == 0`.
- **New occupancy generator**: write a function matching
  `core.occupancy_engine.GeneratorFn` and register it with
  `register_generator`. Registered today:

  | Generator | Used for |
  | --- | --- |
  | `binomial_independent` | Default; independent hourly draws |
  | `markov_chain` | Hour-to-hour persistence, synthesized transitions |
  | `markov_chain_crest` | Real CREST transition matrices, household sizes 1-5 (`working_couple`) |
  | `fixed_schedule` | One open/close window with a flat peak (most service buildings) |
  | `hourly_occupancy_curve` | Explicit 24-hour occupancy table, weekday/weekend (`hotel`) |

- **New region**: add archetype, building-type or data files with a
  different `region` value (e.g. a sibling
  `dhw_tapping_categories_DE.csv`) rather than editing the existing `NL`
  data in place.

## Code Quality

```bash
ruff format .
ruff check .
pytest
mypy src
```

## Commit Style

Use Conventional Commits:

```text
feat: add occupancy CLI output options
fix: correct random-state handling in electricity model
docs: clarify conda setup for Windows
```

## Pull Requests

- Keep PRs focused and small.
- Include tests for behavior changes.
- Update `CHANGELOG.md` under `[Unreleased]`.
- Ensure CI or local checks pass before requesting review.
