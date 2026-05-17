# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- `configs/occupancy_probabilities.json` — default 24-hour home/active probability
  arrays (weekday/weekend) extracted from Python source.
- `configs/electricity_weightage.json` — default hourly usage-weight tables for
  all four appliances (tv, cooking, laundry, cleaning).
- `src/occupancy/_defaults.py` — single loader that reads both JSON files at
  import time and exposes `HOURLY_HOME_PROBABILITIES`, `HOURLY_ACTIVE_PROBABILITIES`,
  and `WEIGHTAGE_TABLE`.
- `src/occupancy/config/` subpackage (`config.py` + `__init__.py`) so that
  `from occupancy.config import ScenarioConfig` continues to work.
- `setup.ps1` / `setup.bat` now write an `occupancy.bat` console-script entry
  point into the conda env's `Scripts/` directory — no `conda-build` or `pip`
  required.
- Dockerfile now copies `src/` and `configs/` for self-contained image builds.
- `docker-compose.yml` now mounts `configs/` for live development overrides.
- `occupancy.def` (Singularity) now bundles `src/` and `configs/`.

### Changed

- `ScenarioConfig.default()` loads `configs/default_scenario.json` instead of
  hardcoding values in Python.
- Hardcoded numpy arrays and weightage-table dicts removed from
  `occupancy_profile.py` and `electricity_consumption.py`.
- `[build-system]` in `pyproject.toml`: removed redundant `wheel` dependency.

### Fixed

- Removed empty `__init__.py` from repo root (caused spurious package detection).
- Removed redundant `src/occupancy/main.py` (superseded by `__main__.py`).
- `conda develop src` is explicitly **not** used; documented workaround for
  broken `conda-build` libarchive on Windows.

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
