from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from occupancy._defaults import (
    HOURLY_ACTIVE_PROBABILITIES,
    HOURLY_HOME_PROBABILITIES,
)
from occupancy.electricity.electricity_consumption import (
    ApplianceWeights,
    ElectricityConsumptionProfile,
)

_DEFAULT_SCENARIO_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "configs"
    / "default_scenario.json"
)


def _normalize_probability_array(
    value: Any,
    fallback: np.ndarray,
) -> np.ndarray:
    if value is None:
        return np.asarray(fallback, dtype=float)
    array = np.asarray(value, dtype=float)
    if array.shape != (24, 2):
        raise ValueError("probability arrays must have shape (24, 2)")
    return array


@dataclass(frozen=True)
class ScenarioConfig:
    year: int
    num_persons: int
    seed: int | None = None
    include_electricity: bool = False
    output: Path = Path("outputs/occupancy_profile.csv")
    has_cooking: bool = True
    has_tv: bool = True
    has_laundry: bool = True
    has_cleaning: bool = True
    has_ironing: bool = True
    has_fridge: bool = True
    has_other: bool = True
    home_probabilities: np.ndarray = field(
        default_factory=lambda: HOURLY_HOME_PROBABILITIES.copy(),
    )
    active_probabilities: np.ndarray = field(
        default_factory=lambda: HOURLY_ACTIVE_PROBABILITIES.copy(),
    )
    weightage_table: dict[str, ApplianceWeights] = field(
        default_factory=(
            ElectricityConsumptionProfile._default_weightage_table
        ),
    )

    @classmethod
    def default(cls) -> ScenarioConfig:
        return load_scenario_config(_DEFAULT_SCENARIO_PATH)

    @classmethod
    def from_mapping(cls, mapping: dict[str, Any]) -> ScenarioConfig:
        if not mapping:
            return cls.default()

        scenario = mapping.get("scenario", mapping)
        occupancy = mapping.get("occupancy", {})
        electricity = mapping.get("electricity", {})

        weightage_table = electricity.get("weightage_table")
        if weightage_table is None:
            weightage_table = (
                ElectricityConsumptionProfile._default_weightage_table()
            )
        else:
            weightage_table = (
                ElectricityConsumptionProfile._normalize_weightage_table(
                    weightage_table,
                )
            )

        return cls(
            year=int(scenario["year"]),
            num_persons=int(scenario["num_persons"]),
            seed=scenario.get("seed"),
            include_electricity=bool(
                scenario.get("include_electricity", False)
            ),
            output=Path(
                scenario.get("output", "outputs/occupancy_profile.csv")
            ),
            has_cooking=bool(scenario.get("has_cooking", True)),
            has_tv=bool(scenario.get("has_tv", True)),
            has_laundry=bool(scenario.get("has_laundry", True)),
            has_cleaning=bool(scenario.get("has_cleaning", True)),
            has_ironing=bool(scenario.get("has_ironing", True)),
            has_fridge=bool(scenario.get("has_fridge", True)),
            has_other=bool(scenario.get("has_other", True)),
            home_probabilities=_normalize_probability_array(
                occupancy.get("home_probabilities"),
                HOURLY_HOME_PROBABILITIES,
            ),
            active_probabilities=_normalize_probability_array(
                occupancy.get("active_probabilities"),
                HOURLY_ACTIVE_PROBABILITIES,
            ),
            weightage_table=weightage_table,
        )


def load_scenario_config(path: str | Path) -> ScenarioConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return ScenarioConfig.from_mapping(data)
