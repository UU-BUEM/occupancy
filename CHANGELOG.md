# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [2.0.0] - 2026-07-24

### Added (household equipment expansion)

- `households/data/equipment.json` expanded from 7 illustrative appliances
  to 29 real ones (Cold, Consumer Electronics + ICT, Cooking, Wet
  categories), plus a new aggregate `lighting` item. `ownership_probability`,
  `rated_power_kw`, and `standby_power_kw` are sourced from the CREST
  Domestic Electricity Demand Model 1.0e (Richardson, Thomson, Infield --
  Loughborough University CREST, obtained via the paper's own public
  download link); hourly weekday/weekend weight shapes remain this repo's
  own illustrative arrays, calibrated so each item's expected annual
  triggered-use energy roughly matches CREST's reported figure. Water
  heating and Electric Space Heating categories are deliberately excluded
  (thermal loads belonging to buem's domain). See
  `.claude/residential/resolved.md` for the full attribution/license
  rationale.
- `ownership_probability` (previously defined in `EquipmentSpec` but
  unused) is now wired up: each household draws, once per seed, whether it
  owns each sub-1.0-probability item (`ElectricityConsumptionProfile._owned_by_name`).
- New `has_lighting` flag (`ElectricityConsumptionProfile`, `ScenarioConfig`,
  CLI, `default_scenario.json`), alongside the existing `has_*` flags —
  each now gates a *list* of individual equipment items rather than one
  (e.g. `has_fridge` covers `chest_freezer`/`fridge_freezer`/`refrigerator`/
  `upright_freezer`).

### Breaking

- Full restructuring for households + service buildings. `src/occupancy/internal_gains/`
  and `src/occupancy/electricity/` are removed; root `configs/` is removed
  (each subpackage now bundles its own `data/` via `importlib.resources`,
  no more dual source-of-truth). `src/occupancy/_defaults.py` is removed.
  Top-level `from occupancy import OccupancyProfile, ElectricityConsumptionProfile,
  OccupancyResult` continues to work (now aliased to the new
  `HouseholdProfile`); deep import paths do not — update
  `occupancy.internal_gains.occupancy_profile.OccupancyProfile` →
  `occupancy.households.HouseholdProfile`, and
  `occupancy.electricity.electricity_consumption.ElectricityConsumptionProfile`
  → `occupancy.households.ElectricityConsumptionProfile`.
- Occupancy profile columns renamed `n_home` → `n_present` (generalized for
  service buildings, which don't have a "home"); `activity` values renamed
  `not_home`/`at_home_inactive`/`at_home_active` →
  `not_present`/`present_inactive`/`present_active`.
- `ElectricityConsumptionProfile`'s `weightage_table` constructor arg and
  `get_weightage_table()` method are replaced by `equipment` and
  `get_equipment_table()`, returning `dict[str, EquipmentSpec]` instead of
  `dict[str, ApplianceWeights]`. `ScenarioConfig`'s JSON schema:
  `electricity.weightage_table` → `electricity.equipment`.
- Equipment item names changed with the CREST-informed expansion above:
  `fridge` → `chest_freezer`/`fridge_freezer`/`refrigerator`/
  `upright_freezer`; `cooking` → `hob`/`oven`/`microwave`/`kettle`/
  `small_cooking_group`; `laundry` → `dish_washer`/`tumble_dryer`/
  `washing_machine`/`washer_dryer`; `tv` → `tv_1`/`tv_2`/`tv_3`/`vcr_dvd`/
  `tv_receiver_box`; `cleaning` → `vacuum`; `other` → 8 named electronics
  items. `has_*` flags keep their old names and behavior (each now maps to
  the corresponding list of new item names).

### Added

- `src/occupancy/core/`: shared engine used by both households and service
  buildings — `occupancy_engine.py` (pluggable generator-strategy registry:
  `binomial_independent`, `markov_chain`, `fixed_schedule`), `equipment.py`
  (config-driven `EquipmentSpec` + trigger-strategy registry:
  `probabilistic_event`, `flat_always_on`, `sessions_per_week`,
  `linear_in_occupants`), `result.py` (`OccupancyResult`, now wired up as
  the shared output contract with `building_type`/`region` fields).
- `src/occupancy/households/`: household occupancy + electricity modeling,
  with a `HOUSEHOLD_ARCHETYPES` registry (`generic`, `working_couple`,
  `family_with_children`, `retired_single`, `student_shared`) loaded from
  `data/archetypes/*.json`. `fridge`, `ironing`, `other` — previously
  hardcoded with no JSON representation — are now `EquipmentSpec` rows like
  the other 4 appliances.
- `working_couple` archetype uses the new `markov_chain` generator as a
  proof-of-concept: a persistence-parameterized Markov chain over active-
  occupant count (inspired by the CREST/Richardson/tsorb transition-
  probability-matrix approach), synthesized at runtime from this repo's own
  validated hourly probability arrays — not copied from any external
  survey dataset. Other archetypes keep the original `binomial_independent`
  generator (bit-for-bit reproducible under the same seed).
- `src/occupancy/services_buildings/`: service (non-residential) building
  modeling, starting with `supermarket`, `office`, `restaurant`, `school`.
  Each type is a thin module (config path + registration) backed by
  `data/<type>/{schedule.json,equipment.json}`; new types register via
  `SERVICE_BUILDING_TYPES`.
- CLI: `--building-type`, `--archetype`, `--region` flags (all default to
  the pre-restructuring household behavior).
- `validate.py` — repo-root validation script for conda env, CLI, tests, and
  package structure checks.
- `push.ps1` — Windows push workflow ported from `UU-BUEM/weather`; supports
  conventional commit validation, tag creation, and changelog body auto-read.

### Changed

- `.github/workflows/ci.yml`: `actions/checkout@v6`, `setup-miniconda@v4`
  (auto-activate, fixes MultipleKeysError), `codecov-action@v6`, added
  `fetch-depth: 0` so `setuptools-scm` reads full tag history in CI.
- `.github/workflows/release.yml`: `actions/checkout@v6`.
- `pyproject.toml`: renamed `write_to` → `version_file` (setuptools-scm ≥ 8).
- `src/occupancy/__init__.py`: fallback version `"1.1.0"` → `"unknown"` to
  avoid silently reporting a stale version number when `_version.py` is absent.
- `.gitignore`: added `push.ps1` and `.commit-message.md`.

## [1.1.0] - 2026-05-18

### Added

- `configs/occupancy_probabilities.json` — default 24-hour home/active
  probability arrays (weekday/weekend) extracted from Python source.
- `configs/electricity_weightage.json` — default hourly usage-weight tables
  for all four appliances (tv, cooking, laundry, cleaning).
- `src/occupancy/_defaults.py` — single loader that reads both JSON files at
  import time and exposes `HOURLY_HOME_PROBABILITIES`,
  `HOURLY_ACTIVE_PROBABILITIES`, and `WEIGHTAGE_TABLE`.
- `src/occupancy/config/` subpackage (`config.py` + `__init__.py`) with
  `importlib.resources`-based path resolution for bundled JSON defaults.
- `src/occupancy/visualization/plots.py` — `plot_weekly_active_occupants`
  separated from core module so matplotlib is not a hard dependency.
- `OccupancyResult` dataclass — typed output contract (profile, year,
  num_persons, generated_at) consumed by downstream modules.
- `conda_build_config.yaml` — numpy=1.26 pin, aligns with `UU-BUEM/weather`.
- `.env.example` — documents `OCCUPANCY_OUTPUT_DIR` environment variable.
- `.github/workflows/ci.yml` — CI pipeline: lint, type-check, tests, CLI
  smoke test, Codecov upload.
- `.github/workflows/release.yml` — auto-publish build artifacts to GitHub
  Releases on `v*` tag push.

### Changed

- Python baseline raised to 3.12 everywhere (pyproject.toml, meta.yaml,
  ci.yml, occupancy_env.yml); removes pre-release 3.14 dependency.
- `ScenarioConfig.default()` uses `importlib.resources` instead of fragile
  four-level `Path(__file__).parent` traversal.
- `meta.yaml` overhauled: Jinja2 version templating from git tag, `pip install
  . --no-deps -vv` build script, pinned numpy/pandas run deps, pip in host.
- `infrastructure/env/occupancy_env.yml` pinned: numpy=1.26.*, pandas=2.2.*,
  pytest=8.*, pytest-cov=5.*; ruff/mypy moved to pip subsection; `-e .` entry
  removed (must be run separately from repo root).
- Docker base image standardised to `continuumio/miniconda3:24.1.2-0` (pinned,
  aligns with weather); bind-mount pattern replaces build-time `COPY src/`;
  OCI LABEL metadata added.
- `setup.ps1` / `setup.bat` now run `pip install -e . --no-deps` and include
  post-install `python -m occupancy --help` verification.
- `pyproject.toml`: dep upper bounds (numpy<3, pandas<3), wheel added to
  build-system.requires, ruff/mypy target updated to py312.

### Fixed

- Deleted `setup.py` stub (conflicted with pyproject.toml build system).
- `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` added to both workflows (Node 20
  deprecation on GitHub Actions).
- `contents: write` permission added to release workflow (resolved 403 error
  when creating GitHub Releases with default read-only token).
- `!src/occupancy/config/data/` negation added to `.gitignore` so bundled
  JSON config files are not excluded by the top-level `data/` rule.

## [0.1.0] - 2026-05-15

### Added

- Occupancy-native package API with `occupancy` CLI.
- `src/occupancy/__init__.py`, `src/occupancy/__main__.py`, and `src/occupancy/cli.py`.
- Clean conda environment, container, and setup scripts for independent repo usage.

### Changed

- Refactored occupancy and electricity modules to remove BuEM/weather coupling.
- Updated package metadata, script entry points, and repository URLs.
- Reduced dependencies to those actually required for occupancy modeling.

### Fixed

- Invalid import path from BuEM monorepo in electricity module.
- Multiple weather-template leftovers in docs and infrastructure.
