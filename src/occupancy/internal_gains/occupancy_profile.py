from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from occupancy._defaults import (
    HOURLY_ACTIVE_PROBABILITIES,
    HOURLY_HOME_PROBABILITIES,
)


@dataclass
class OccupancyResult:
    """Typed output contract for a generated occupancy profile."""

    profile: pd.DataFrame
    year: int
    num_persons: int
    generated_at: str = field(
        default_factory=lambda: datetime.now(tz=UTC).isoformat()
    )


@dataclass
class OccupancyProfile:
    """Stochastic hourly occupancy model for a single dwelling."""

    num_persons: int
    year: int
    seed: int | None = None
    home_probabilities: np.ndarray = field(
        default_factory=lambda: HOURLY_HOME_PROBABILITIES.copy(),
    )
    active_probabilities: np.ndarray = field(
        default_factory=lambda: HOURLY_ACTIVE_PROBABILITIES.copy(),
    )

    def __post_init__(self) -> None:
        if self.num_persons <= 0:
            raise ValueError("num_persons must be greater than 0")
        if self.year < 1900:
            raise ValueError("year must be >= 1900")
        self.home_probabilities = np.asarray(
            self.home_probabilities, dtype=float
        )
        self.active_probabilities = np.asarray(
            self.active_probabilities, dtype=float
        )
        if self.home_probabilities.shape != (24, 2):
            raise ValueError("home_probabilities must have shape (24, 2)")
        if self.active_probabilities.shape != (24, 2):
            raise ValueError("active_probabilities must have shape (24, 2)")
        self._rng = np.random.default_rng(self.seed)
        self._index = pd.date_range(
            start=f"{self.year}-01-01",
            end=f"{self.year}-12-31 23:00",
            freq="h",
        )
        self._profile: pd.DataFrame | None = None

    def generate(self, seed: int | None = None) -> pd.DataFrame:
        """Generate and cache the yearly occupancy profile."""
        rng = self._rng if seed is None else np.random.default_rng(seed)

        frame = pd.DataFrame(index=self._index)
        frame["is_weekend"] = frame.index.weekday >= 5

        n_home: list[int] = []
        n_active: list[int] = []
        activity_state: list[str] = []

        for ts in frame.itertuples():
            hour = ts.Index.hour
            weekend_index = 1 if bool(ts.is_weekend) else 0

            p_home = self.home_probabilities[hour][weekend_index]
            p_active = self.active_probabilities[hour][weekend_index]

            persons_home = int(rng.binomial(self.num_persons, p_home))
            if persons_home:
                persons_active = int(rng.binomial(persons_home, p_active))
            else:
                persons_active = 0

            n_home.append(persons_home)
            n_active.append(persons_active)

            if persons_home == 0:
                activity_state.append("not_home")
            elif persons_active == 0:
                activity_state.append("at_home_inactive")
            else:
                activity_state.append("at_home_active")

        result = pd.DataFrame(
            {
                "n_home": n_home,
                "n_active": n_active,
                "activity": activity_state,
            },
            index=self._index,
        )
        self._profile = result
        return result

    def get_profile(self) -> pd.DataFrame:
        """Return a generated profile, creating one lazily if needed."""
        if self._profile is None:
            return self.generate()
        return self._profile
