from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from occupancy.core.occupancy_engine import OccupancyGenerationContext, get_generator
from occupancy.core.result import OccupancyResult
from occupancy.households.archetypes import get_archetype


@dataclass
class HouseholdProfile:
    """Stochastic hourly occupancy model for a single household.

    ``archetype`` selects the default occupancy-probability data and
    generator strategy from :data:`occupancy.households.archetypes.HOUSEHOLD_ARCHETYPES`
    (default ``"generic"``, the pre-restructuring behavior). Any of
    ``home_probabilities``/``active_probabilities``/``generator``/
    ``generator_params`` can be overridden explicitly, same as before.
    """

    num_persons: int
    year: int
    archetype: str = "generic"
    seed: int | None = None
    region: str = "NL"
    home_probabilities: np.ndarray | None = None
    active_probabilities: np.ndarray | None = None
    generator: str | None = None
    generator_params: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.num_persons <= 0:
            raise ValueError("num_persons must be greater than 0")
        if self.year < 1900:
            raise ValueError("year must be >= 1900")

        archetype_spec = get_archetype(self.archetype)

        home = (
            self.home_probabilities
            if self.home_probabilities is not None
            else archetype_spec.home_probabilities
        )
        active = (
            self.active_probabilities
            if self.active_probabilities is not None
            else archetype_spec.active_probabilities
        )
        self.home_probabilities = np.asarray(home, dtype=float)
        self.active_probabilities = np.asarray(active, dtype=float)
        if self.home_probabilities.shape != (24, 2):
            raise ValueError("home_probabilities must have shape (24, 2)")
        if self.active_probabilities.shape != (24, 2):
            raise ValueError("active_probabilities must have shape (24, 2)")

        self._generator_name = self.generator or archetype_spec.generator
        self._generator_params = (
            self.generator_params
            if self.generator_params is not None
            else archetype_spec.generator_params
        )

        self._rng = np.random.default_rng(self.seed)
        self._index = pd.date_range(
            start=f"{self.year}-01-01",
            end=f"{self.year}-12-31 23:00",
            freq="h",
        )
        self._profile: pd.DataFrame | None = None

    def generate(self, seed: int | None = None) -> pd.DataFrame:
        """Generate and cache the yearly occupancy profile."""
        assert self.home_probabilities is not None
        assert self.active_probabilities is not None
        rng = self._rng if seed is None else np.random.default_rng(seed)
        ctx = OccupancyGenerationContext(
            size=self.num_persons,
            index=self._index,
            home_probabilities=self.home_probabilities,
            active_probabilities=self.active_probabilities,
            rng=rng,
            params=self._generator_params or {},
        )
        strategy = get_generator(self._generator_name)
        self._profile = strategy(ctx)
        return self._profile

    def get_profile(self) -> pd.DataFrame:
        """Return a generated profile, creating one lazily if needed."""
        if self._profile is None:
            return self.generate()
        return self._profile

    def to_result(self) -> OccupancyResult:
        return OccupancyResult(
            profile=self.get_profile(),
            year=self.year,
            num_persons=self.num_persons,
            building_type="household",
            region=self.region,
        )
