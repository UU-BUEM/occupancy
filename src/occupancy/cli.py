from __future__ import annotations

import argparse
from pathlib import Path

from occupancy.config import ScenarioConfig, load_scenario_config
from occupancy.electricity.electricity_consumption import (
    ElectricityConsumptionProfile,
)
from occupancy.internal_gains.occupancy_profile import OccupancyProfile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="occupancy",
        description="Generate stochastic occupancy and electricity profiles.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to a JSON scenario config file.",
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
        help="Number of occupants.",
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
        "--output",
        type=Path,
        default=None,
        help="Output CSV path.",
    )
    return parser


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

    occupancy = OccupancyProfile(
        num_persons=persons,
        year=year,
        seed=seed,
        home_probabilities=config.home_probabilities,
        active_probabilities=config.active_probabilities,
    )
    profile = occupancy.get_profile()

    if include_electricity:
        electricity = ElectricityConsumptionProfile(
            occupancy_profile=occupancy,
            seed=seed,
            weightage_table=config.weightage_table,
            has_cooking=config.has_cooking,
            has_tv=config.has_tv,
            has_laundry=config.has_laundry,
            has_cleaning=config.has_cleaning,
            has_ironing=config.has_ironing,
            has_fridge=config.has_fridge,
            has_other=config.has_other,
        )
        profile = electricity.get_profile()

    output.parent.mkdir(parents=True, exist_ok=True)
    profile.to_csv(output)
    print(f"Saved profile with {len(profile)} hourly rows to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
