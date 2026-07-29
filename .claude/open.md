# Open issues / TODOs — cross-cutting

Household-specific items: `residential/open.md`. Service-building-specific
items: `services/open.md`.

## >>> NEXT MAJOR TASKS <<<
- [region] **Multi-region data** — `region` is threaded through
  `OccupancyResult` and archetype/building-type JSON, but only one
  region's data (`NL`) is populated. Adding a new region is a config
  addition (new archetype/building-type JSON files with a different
  `region` value); no registry keying by region exists yet if two regions
  need the *same* archetype id with different data — would need the
  registry key to become `(id, region)` if/when that's needed.

## cross-module
- [all] Keep ruff/mypy/pytest clean; honour `pyproject.toml` settings at
  root.
- [all] Public API (`OccupancyProfile`/`HouseholdProfile`/
  `ElectricityConsumptionProfile`/`OccupancyResult`/`ServiceBuildingProfile`,
  all re-exported from `occupancy/__init__.py`) is the compatibility
  surface going forward — deep module paths are not guaranteed stable.

## external (context only)
- [buem] **Superseded** — a prior pass claimed buem's `cfg_attribute.json`
  has no occupancy/internal-gains/electricity fields; that was wrong (or
  read a stale/different version). Direct inspection of
  `buem.config.cfg_attribute.ATTRIBUTE_SPECS` and
  `buem.thermal.model_buem.ModelBUEM._addPara`/`_addConstraints_sequential`
  (2026-07-28) confirms buem's `cfg` dict *requires* four series —
  `Q_ig`, `elecLoad`, `occ_nothome`, `occ_sleeping` — and raises
  `ValueError` if any are missing. `occupancy.core.buem_adapter.to_buem_profiles()`
  now builds all four from an `OccupancyResult`; see CHANGELOG
  `[Unreleased]` and README "Feeding buem".
- [buem] **User context (2026-07-28):** `occupancy` used to live inside the
  `buem` monorepo; it has since been split out into this standalone repo,
  and `buem` itself is being refactored to depend on it externally instead
  — that refactor is in progress, not complete. The package-name-mismatch
  item below is exactly the seam that refactor needs to close.
- [buem] **Package-name mismatch — fixed on buem's side (2026-07-29,
  uncommitted as of that date)**. buem's working tree now imports
  `from occupancy import ElectricityConsumptionProfile, HouseholdProfile,
  to_buem_profiles` and calls
  `to_buem_profiles(ElectricityConsumptionProfile(occupancy_profile=
  HouseholdProfile(...)).to_result())` in `cfg_attribute.py` — matching
  this repo's real public API and the exact pattern documented in this
  repo's README "Feeding buem" section. `pyproject.toml`'s
  `buem-occupancy`/`buem-weather` extras were also renamed to
  `occupancy`/`weather`. Not yet committed/merged on buem's side as of this
  note; re-verify once merged. Neither package is published to PyPI/
  conda-forge yet, so `pip install buem[occupancy]` won't resolve until
  either occupancy is published somewhere pip can reach, or the dependency
  is pointed at a VCS/local URL — occupancy does already ship a working
  conda recipe (`meta.yaml`) buildable locally via `conda build .` +
  `conda install --use-local occupancy`, which needs no publishing step.
  buem now targets Python >=3.14 (env + pyproject bumped); occupancy
  declares `>=3.12` with no upper pin so there's no hard version conflict,
  but occupancy's own dev/CI baseline is 3.12 (see `resolved.md` "Python
  baseline") and has never been run under 3.14 — untested, not blocked.
- [buem] **Original mismatch note (superseded by the fix above, kept for
  history)** — `buem`'s `cfg_attribute.py` imports
  `from buem_occupancy.occupancy_profile import OccupancyProfile` and
  `from buem_occupancy.electricity_consumption import ElectricityConsumptionProfile`
  (`pip install buem-occupancy`) as its intended real (non-fallback) source
  for `elecLoad`. Those class names and the
  `OccupancyProfile(num_persons=..., year=..., seed=...).generate()` /
  `ElectricityConsumptionProfile(occupancy_profile=...).generate()["total_power_kwh"]`
  shapes match this repo's actual API almost exactly — but this repo is
  packaged/importable as `occupancy`, not `buem_occupancy`, and the
  submodule paths (`occupancy.households.household_profile` /
  `occupancy.households.electricity`) don't match buem's expected
  `buem_occupancy.occupancy_profile` / `buem_occupancy.electricity_consumption`
  either. Also: buem's fallback path only ever calls
  `OccupancyProfile`/`ElectricityConsumptionProfile` (i.e. household-only)
  — it has no notion of pulling a `ServiceBuildingProfile` result, and no
  `Q_ig`/`occ_nothome`/`occ_sleeping` wiring at all, real or fallback. This
  needs resolving on the buem side (package rename/alias, or buem depending
  on `occupancy` directly and calling `to_buem_profiles()`) — flagged here,
  not fixed here, since it's a buem-repo change.
- [reference-repos] Design informed by pyCREST, richardsonpy, tsorb (all
  GPLv3 — concepts/schema only, no data/code copied), StROBe (unlicensed —
  household-archetype concept only), simpy and mesa (evaluated and
  deliberately not adopted as dependencies), plus two journal papers
  (Richardson et al. 2009 CREST domestic demand model; Buttitta & Finn
  2020 occupancy-integrated archetypes, *Energy & Buildings* 206:109577)
  — see `residential/open.md` for paper-specific follow-ups and license
  notes (CREST's own data download is CC BY-NC-ND, no derivatives).
