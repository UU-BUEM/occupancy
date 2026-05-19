# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

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
