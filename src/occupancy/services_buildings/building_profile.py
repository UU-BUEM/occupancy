from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from occupancy.core.equipment import generate_equipment_power
from occupancy.core.occupancy_engine import (
    OccupancyGenerationContext,
    get_generator,
)
from occupancy.core.result import OccupancyResult
from occupancy.services_buildings.building_types import get_building_type


@dataclass
class ServiceBuildingProfile:
    """Stochastic hourly occupancy + electricity demand for one service
    (non-residential) building.

    ``building_type`` selects the default capacity, generator strategy
    (typically ``fixed_schedule``), and equipment set from
    :data:`occupancy.services_buildings.building_types.SERVICE_BUILDING_TYPES`.
    Unlike households, occupancy and equipment demand are combined in a
    single profile — there is no separate electricity-profile class.
    """

    building_type: str
    year: int
    capacity: int | None = None
    seed: int | None = None
    region: str | None = None
    generator: str | None = None
    generator_params: dict[str, Any] | None = None
    include_equipment: bool = True

    def __post_init__(self) -> None:
        if self.year < 1900:
            raise ValueError("year must be >= 1900")

        self._type_spec = get_building_type(self.building_type)
        if self.capacity is None:
            self.capacity = self._type_spec.capacity_default
        if self.capacity <= 0:
            raise ValueError("capacity must be greater than 0")
        if self.region is None:
            self.region = self._type_spec.region

        self._generator_name = self.generator or self._type_spec.generator
        self._generator_params = (
            self.generator_params
            if self.generator_params is not None
            else self._type_spec.generator_params
        )

        self._rng = np.random.default_rng(self.seed)
        self._index = pd.date_range(
            start=f"{self.year}-01-01",
            end=f"{self.year}-12-31 23:00",
            freq="h",
        )
        self._profile: pd.DataFrame | None = None

    def generate(self, seed: int | None = None) -> pd.DataFrame:
        """Generate and cache the yearly occupancy (+ equipment) profile."""
        assert self.capacity is not None
        rng = self._rng if seed is None else np.random.default_rng(seed)
        ctx = OccupancyGenerationContext(
            size=self.capacity,
            index=self._index,
            rng=rng,
            asleep_probabilities=self._type_spec.asleep_probabilities,
            params=self._generator_params or {},
        )
        strategy = get_generator(self._generator_name)
        profile = strategy(ctx)

        if self.include_equipment:
            specs = [
                spec
                for spec in self._type_spec.equipment.values()
                if spec.enabled
            ]
            profile["total_power_kwh"] = generate_equipment_power(
                specs, profile, rng
            )

        self._profile = profile
        return profile

    def get_profile(self) -> pd.DataFrame:
        """Return a generated profile, creating one lazily if needed."""
        if self._profile is None:
            return self.generate()
        return self._profile

    def to_result(self) -> OccupancyResult:
        assert self.region is not None
        return OccupancyResult(
            profile=self.get_profile(),
            year=self.year,
            num_persons=self.capacity or 0,
            building_type=self.building_type,
            region=self.region,
            heat_gain_present_kw=self._type_spec.heat_gain_present_kw,
            heat_gain_active_kw=self._type_spec.heat_gain_active_kw,
            gain_w_per_m2=self._type_spec.gain_w_per_m2,
        )
