# Occupancy

Stochastic occupancy and electricity-demand profile modeling for households
and service buildings, for UU-BUEM. Feeds
[UU-BUEM/buem](https://github.com/UU-BUEM/buem) (a pure envelope/thermal
model) with the occupancy/internal-gains/electricity input it doesn't
generate itself.

## What This Repo Does

This package generates stochastic hourly occupancy states and derives total
hourly electricity demand from those states, for:

- **Households** — via composition archetypes (`generic`, `working_couple`,
  `family_with_children`, `retired_single`, `student_shared`, ...).
- **Service buildings** — `supermarket`, `office`, `restaurant`, `school`,
  easily extended with more types.

Core models:

- Household occupancy: `HouseholdProfile` (aliased as `OccupancyProfile`)
- Household electricity: `ElectricityConsumptionProfile`
- Service building occupancy + electricity: `ServiceBuildingProfile`

Everything — occupancy probabilities, household archetypes, appliance/
equipment specs, service-building schedules — is config-driven JSON, not
hardcoded Python. Adding a new appliance, household archetype, or building
type is a config addition; see `CLAUDE.md` and
`docs/plans/equipment-service-buildings-architecture.md` for the extension
points and design rationale.

## Repository Layout

```text
occupancy/
├── src/
│   └── occupancy/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── config/                 # CLI-facing ScenarioConfig
│       │   ├── __init__.py
│       │   ├── config.py
│       │   └── data/default_scenario.json
│       ├── core/                   # shared engine (households + services_buildings)
│       │   ├── equipment.py          # EquipmentSpec + trigger-strategy registry
│       │   ├── occupancy_engine.py   # generator-strategy registry
│       │   ├── loader.py
│       │   └── result.py             # OccupancyResult
│       ├── households/
│       │   ├── __init__.py           # HOUSEHOLD_ARCHETYPES registry
│       │   ├── archetypes.py
│       │   ├── household_profile.py
│       │   ├── electricity.py
│       │   └── data/
│       │       ├── archetypes/*.json
│       │       └── equipment.json
│       ├── services_buildings/
│       │   ├── __init__.py           # SERVICE_BUILDING_TYPES registry
│       │   ├── building_profile.py
│       │   ├── building_types.py
│       │   ├── supermarket.py
│       │   ├── office.py
│       │   ├── restaurant.py
│       │   ├── school.py
│       │   └── data/<type>/{schedule,equipment}.json
│       └── visualization/
│           ├── __init__.py
│           └── plots.py
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

> `conda develop src` is **not** used here. `setup.ps1` creates the conda
> environment and runs `pip install -e . --no-deps` from the repo root so the
> editable install works correctly.

Generate a household occupancy profile (defaults to the `generic` archetype):

```bash
occupancy --year 2026 --persons 3 --seed 42 --output outputs/occupancy.csv
```

Generate occupancy + electricity for a specific household archetype:

```bash
occupancy --year 2026 --persons 2 --archetype working_couple --seed 42 \
  --include-electricity --output outputs/working_couple.csv
```

Generate a service building profile:

```bash
occupancy --building-type supermarket --year 2026 --seed 42 \
  --include-electricity --output outputs/supermarket.csv
```

Run a fully reproducible scenario from config:

```bash
occupancy --config path/to/scenario.json
```

## Configuration

Every numerical default — occupancy probabilities, household archetypes,
appliance/equipment specs, service-building schedules — is bundled JSON
under each subpackage's own `data/` folder (`config/data/`,
`households/data/`, `services_buildings/data/`), loaded via
`importlib.resources`. No hardcoded arrays in Python source.

| Location | Contents |
| --- | --- |
| `config/data/default_scenario.json` | Year, persons/capacity, seed, building type, appliance flags, output path |
| `households/data/archetypes/*.json` | Per-archetype occupancy probabilities, generator strategy, equipment overrides |
| `households/data/equipment.json` | 29 household appliances as `EquipmentSpec` rows (ownership/power figures sourced from the CREST Domestic Electricity Demand Model) |
| `services_buildings/data/<type>/schedule.json` | Capacity, generator strategy + params (open hours, etc.) |
| `services_buildings/data/<type>/equipment.json` | That building type's `EquipmentSpec` rows |

Pass a custom scenario JSON via `--config` to override any subset of the
scenario/occupancy/electricity fields without touching the bundled defaults.
Adding a new appliance, household archetype, or service-building type is a
JSON addition — see `CLAUDE.md` for the registry mechanism.

## Docker

```bash
# Build the image (bind-mounts src/ at runtime, including package data):
docker compose -f infrastructure/container/docker-compose.yml build

# Run (src/ is bind-mounted for live development):
docker compose -f infrastructure/container/docker-compose.yml up

# Standalone run:
docker run --rm occupancy:latest python -m occupancy --help
```

Output CSV is written to `outputs/` on the host via bind mount.

## Development Checks

```bash
ruff format .
ruff check .
pytest
mypy src
python validate.py
```
