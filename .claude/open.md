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
- [buem] Confirmed via inspecting `UU-BUEM/buem`'s `cfg_attribute.json`:
  buem is purely envelope/thermal (walls/roof/floor/windows/doors/
  ventilation, U-values) with no occupancy/internal-gains/electricity
  fields — this repo is buem's intended upstream source for those inputs.
- [reference-repos] Design informed by pyCREST, richardsonpy, tsorb (all
  GPLv3 — concepts/schema only, no data/code copied), StROBe (unlicensed —
  household-archetype concept only), simpy and mesa (evaluated and
  deliberately not adopted as dependencies), plus two journal papers
  (Richardson et al. 2009 CREST domestic demand model; Buttitta & Finn
  2020 occupancy-integrated archetypes, *Energy & Buildings* 206:109577)
  — see `residential/open.md` for paper-specific follow-ups and license
  notes (CREST's own data download is CC BY-NC-ND, no derivatives).
