# Contributing

Thank you for contributing to occupancy.

## Development Setup

```powershell
# Creates the conda environment, sets PYTHONPATH, and writes the 'occupancy'
# console script into the env's Scripts/ directory:
.\setup.ps1          # PowerShell
setup.bat            # CMD

conda activate occupancy_env
occupancy --help
```

> **Do not run `conda develop src`.**  It requires `conda-build` and has known
> `libarchive` issues on Windows.  PYTHONPATH is managed via
> `conda env config vars` instead.

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
