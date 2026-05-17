# Occupancy

Standalone occupancy and residential electricity profile modeling repository for UU-BUEM.

## What This Repo Does

This package generates stochastic hourly occupancy states and can derive
total hourly electricity demand from those states.

Core models:

- Occupancy model: `OccupancyProfile`
- Electricity model: `ElectricityConsumptionProfile`

## Repository Layout

```text
occupancy/
├── src/
│   └── occupancy/
│       ├── __init__.py
│       ├── __main__.py
│       ├── _defaults.py
│       ├── cli.py
│       ├── config/
│       │   ├── __init__.py
│       │   └── config.py
│       ├── electricity/
│       │   ├── __init__.py
│       │   └── electricity_consumption.py
│       └── internal_gains/
│           ├── __init__.py
│           └── occupancy_profile.py
├── configs/
│   ├── default_scenario.json
│   ├── occupancy_probabilities.json
│   └── electricity_weightage.json
├── infrastructure/
│   ├── env/
│   │   └── occupancy_env.yml
│   └── container/
│       ├── Dockerfile
│       ├── docker-compose.yml
│       └── occupancy.def
├── tests/
├── pyproject.toml
├── meta.yaml
├── setup.py
├── setup.ps1
└── setup.bat
```

## Quickstart (Conda)

```powershell
# 1. Create/update the conda environment and install the 'occupancy' command:
.\setup.ps1          # PowerShell
setup.bat            # CMD

# 2. Activate and verify:
conda activate occupancy_env
occupancy --help
```

> `conda develop src` is **not** used here — `setup.ps1` sets `PYTHONPATH` via
> `conda env config vars` and writes a lightweight `occupancy.bat` wrapper into
> the env's `Scripts/` directory.  No `conda-build` or `pip` required.

Generate yearly occupancy profile:

```bash
occupancy --year 2026 --persons 3 --seed 42 --output outputs/occupancy.csv
```

Generate occupancy + electricity profile:

```bash
occupancy --year 2026 --persons 3 --seed 42 --include-electricity \
  --output outputs/occupancy_electricity.csv
```

Run a fully reproducible scenario from config:

```bash
occupancy --config configs/default_scenario.json
```

## Configuration

All default numerical parameters live in `configs/` and are loaded at runtime —
no hardcoded arrays in Python source.

| File | Contents |
| --- | --- |
| `default_scenario.json` | Year, persons, seed, appliance flags, output path |
| `occupancy_probabilities.json` | 24-hour home/active probability arrays (weekday vs weekend) |
| `electricity_weightage.json` | Hourly usage-weight arrays per appliance |

Pass a custom scenario JSON via `--config` to override any subset of these
values without touching the defaults.

## Docker

```bash
# Build a self-contained image (src/ and configs/ are baked in):
docker compose -f infrastructure/container/docker-compose.yml build

# Run (compose mounts local src/ and configs/ for live development):
docker compose -f infrastructure/container/docker-compose.yml up

# Standalone run (no compose, uses baked-in code):
docker run --rm occupancy:latest python -m occupancy --help
```

Output CSV is written to `outputs/` on the host via bind mount.

## Development Checks

```bash
ruff format .
ruff check .
pytest
mypy src
```
