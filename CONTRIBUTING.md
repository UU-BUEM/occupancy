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

All default numerical parameters are in `configs/` — edit these instead of
touching Python source:

- `configs/occupancy_probabilities.json` — hourly home/active probability arrays
- `configs/electricity_weightage.json` — appliance usage-weight tables
- `configs/default_scenario.json` — scenario defaults (year, persons, flags)

To test a custom scenario, pass `--config <path>` on the CLI or call
`load_scenario_config(path)` in Python.

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
