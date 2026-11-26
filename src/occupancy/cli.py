from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from occupancy.config import ScenarioConfig, load_scenario_config
from occupancy.core.ev import EVConfig
from occupancy.households import (
    ElectricityConsumptionProfile,
    HouseholdProfile,
    load_ev_config,
)
from occupancy.services_buildings import ServiceBuildingProfile
from occupancy.services_buildings.building_types import SERVICE_BUILDING_TYPES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="occupancy",
        description="Generate stochastic occupancy and electricity profiles "
        "for households and service buildings.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to a JSON scenario config file.",
    )
    parser.add_argument(
        "--building-type",
        choices=["household", *sorted(SERVICE_BUILDING_TYPES)],
        default=None,
        help="Building type to model (default: household).",
    )
    parser.add_argument(
        "--archetype",
        default=None,
        help="Household archetype (household building type only).",
    )
    parser.add_argument(
        "--region",
        default=None,
        help="Region key, e.g. 'NL' (default region data only, no-op today).",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Target year (e.g. 2026).",
    )
    parser.add_argument(
        "--persons",
        type=int,
        default=None,
        help="Number of occupants (household) or building capacity (service).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility.",
    )
    parser.add_argument(
        "--include-electricity",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Also generate total electricity demand profile.",
    )
    parser.add_argument(
        "--ev",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Household has an electric vehicle (default: yes). EV columns "
        "are added with --include-electricity; EV charging is never part "
        "of total_power_kwh.",
    )
    parser.add_argument(
        "--ev-ownership-probability",
        type=float,
        default=None,
        help="EV ownership is unknown: draw it with this probability "
        "(community analysis; bundled default 0.20 for Loenen). Overrides "
        "--ev.",
    )
    parser.add_argument(
        "--ev-charger-kw",
        type=float,
        default=None,
        help="Home charger power in kW (default 7.4).",
    )
    parser.add_argument(
        "--ev-config",
        type=Path,
        default=None,
        help="JSON file of EV parameter overrides (e.g. survey-derived "
        "distributions), merged over households/data/ev.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV path.",
    )
    return parser


def _ev_arguments(
    args: argparse.Namespace, config: ScenarioConfig
) -> tuple[bool | None, EVConfig | dict[str, Any] | str | Path | None]:
    """Resolve (has_ev, ev_config) from CLI flags over the scenario file."""
    has_ev = args.ev if args.ev is not None else config.has_ev
    file_overrides = (
        args.ev_config if args.ev_config is not None else config.ev_overrides
    )
    flag_overrides: dict[str, Any] = {}
    if args.ev_ownership_probability is not None:
        has_ev = None
        flag_overrides["ownership_probability"] = args.ev_ownership_probability
    if args.ev_charger_kw is not None:
        base = load_ev_config(file_overrides)
        flag_overrides["charging_modes"] = {
            base.home_mode.name: {"power_kw": args.ev_charger_kw}
        }
    if not flag_overrides:
        return has_ev, file_overrides
    return has_ev, load_ev_config(file_overrides).with_overrides(
        flag_overrides
    )


def main() -> int:
    args = build_parser().parse_args()

    config = ScenarioConfig.default()
    if args.config is not None:
        config = load_scenario_config(args.config)

    year = args.year if args.year is not None else config.year
    persons = args.persons if args.persons is not None else config.num_persons
    seed = args.seed if args.seed is not None else config.seed
    include_electricity = (
        args.include_electricity
        if args.include_electricity is not None
        else config.include_electricity
    )
    output = args.output if args.output is not None else config.output
    building_type = (
        args.building_type
        if args.building_type is not None
        else config.building_type
    )
    region = args.region if args.region is not None else config.region

    if building_type == "household":
        archetype = (
            args.archetype if args.archetype is not None else config.archetype
        )
        household = HouseholdProfile(
            num_persons=persons,
            year=year,
            archetype=archetype,
            seed=seed,
            region=region,
            home_probabilities=config.home_probabilities,
            active_probabilities=config.active_probabilities,
        )
        profile = household.get_profile()

        if include_electricity:
            has_ev, ev_config = _ev_arguments(args, config)
            electricity = ElectricityConsumptionProfile(
                occupancy_profile=household,
                seed=seed,
                equipment=config.equipment,
                has_cooking=config.has_cooking,
                has_tv=config.has_tv,
                has_laundry=config.has_laundry,
                has_cleaning=config.has_cleaning,
                has_ironing=config.has_ironing,
                has_fridge=config.has_fridge,
                has_other=config.has_other,
                has_lighting=config.has_lighting,
                has_ev=has_ev,
                ev_config=ev_config,
            )
            profile = electricity.get_profile()
    else:
        building = ServiceBuildingProfile(
            building_type=building_type,
            year=year,
            capacity=persons if args.persons is not None else None,
            seed=seed,
            region=region,
            include_equipment=include_electricity,
        )
        profile = building.get_profile()

    output.parent.mkdir(parents=True, exist_ok=True)
    profile.to_csv(output)
    print(f"Saved profile with {len(profile)} hourly rows to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
