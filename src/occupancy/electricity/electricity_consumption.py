from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from occupancy._defaults import WEIGHTAGE_TABLE as _DEFAULT_WEIGHTAGE_TABLE
from occupancy.internal_gains.occupancy_profile import OccupancyProfile


@dataclass(frozen=True)
class ApplianceWeights:
    """Weekday and weekend hourly weight profile for one appliance."""

    weekday: np.ndarray
    weekend: np.ndarray


def _normalize_wt(
    table: dict[str, Any],
) -> dict[str, ApplianceWeights]:
    return {
        appliance: ApplianceWeights(
            weekday=np.asarray(day["weekday"], dtype=float),
            weekend=np.asarray(day["weekend"], dtype=float),
        )
        for appliance, day in table.items()
    }


def _default_wt_factory() -> dict[str, ApplianceWeights]:
    return _normalize_wt(_DEFAULT_WEIGHTAGE_TABLE)


@dataclass
class ElectricityConsumptionProfile:
    """Hourly residential electricity demand derived from occupancy states."""

    occupancy_profile: OccupancyProfile
    weightage_table: dict[str, ApplianceWeights] = field(
        default_factory=_default_wt_factory,
    )
    has_cooking: bool = True
    has_tv: bool = True
    has_laundry: bool = True
    has_cleaning: bool = True
    has_ironing: bool = True
    has_fridge: bool = True
    has_other: bool = True
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.seed is None:
            self.seed = self.occupancy_profile.seed
        self._rng = np.random.default_rng(self.seed)
        self._profile: pd.DataFrame | None = None

    @staticmethod
    def _normalize_weightage_table(
        table: dict[str, Any],
    ) -> dict[str, ApplianceWeights]:
        return _normalize_wt(table)

    @classmethod
    def _default_weightage_table(cls) -> dict[str, ApplianceWeights]:
        return _default_wt_factory()

    def get_weightage_table(self) -> dict[str, ApplianceWeights]:
        return self.weightage_table

    def generate(self) -> pd.DataFrame:
        occ_profile = self.occupancy_profile.get_profile().copy()
        total = np.zeros(len(occ_profile), dtype=float)

        if self.has_fridge:
            total += self.fridge_profile(occ_profile)
        if self.has_tv:
            total += self.tv_profile(occ_profile)
        if self.has_cooking:
            total += self.cooking_profile(occ_profile)
        if self.has_laundry:
            total += self.laundry_profile(occ_profile)
        if self.has_cleaning:
            total += self.cleaning_profile(occ_profile)
        if self.has_ironing:
            total += self.ironing_profile(occ_profile)
        if self.has_other:
            total += self.other_profile(occ_profile)

        occ_profile["total_power_kwh"] = total
        self._profile = occ_profile
        return occ_profile

    def fridge_profile(self, occ_profile: pd.DataFrame) -> np.ndarray:
        return np.full(len(occ_profile), 0.04, dtype=float)

    def _day_weights(
        self,
        appliance: str,
        is_weekend: np.ndarray,
        hours: np.ndarray,
    ) -> np.ndarray:
        assert self.weightage_table is not None
        weights = self.weightage_table[appliance]
        return np.where(
            is_weekend,
            weights.weekend[hours],
            weights.weekday[hours],
        )

    def tv_profile(self, occ_profile: pd.DataFrame) -> np.ndarray:
        standby = 0.002
        on = 0.25
        tv_power = np.full(len(occ_profile), standby, dtype=float)
        is_weekend = occ_profile.index.weekday >= 5
        hours = occ_profile.index.hour
        n_home = occ_profile["n_home"].values
        n_active = occ_profile["n_active"].values

        percent_active = np.divide(
            n_active,
            n_home,
            out=np.zeros_like(n_active, dtype=float),
            where=n_home > 0,
        )
        p_tv_on = (0.2 + 0.6 * percent_active) * self._day_weights(
            "tv",
            is_weekend,
            hours,
        )
        p_tv_on[n_home == 0] = 0

        tv_on_hours = self._rng.binomial(1, p_tv_on)
        tv_power[(n_home > 0) & (tv_on_hours == 1)] = on
        tv_power[n_home == 0] = 0
        return tv_power

    def cooking_profile(self, occ_profile: pd.DataFrame) -> np.ndarray:
        cooking_power = np.zeros(len(occ_profile), dtype=float)
        is_weekend = occ_profile.index.weekday >= 5
        hours = occ_profile.index.hour
        n_home = occ_profile["n_home"].values
        n_active = occ_profile["n_active"].values

        percent_active = np.divide(
            n_active,
            n_home,
            out=np.zeros_like(n_active, dtype=float),
            where=n_home > 0,
        )
        p_cook = (0.2 + 0.6 * percent_active) * self._day_weights(
            "cooking",
            is_weekend,
            hours,
        )
        p_cook[n_active == 0] = 0

        cook_events = self._rng.binomial(1, p_cook)
        cooking_power[(n_active > 0) & (cook_events == 1)] = 1.5
        return cooking_power

    def laundry_profile(self, occ_profile: pd.DataFrame) -> np.ndarray:
        laundry_power = np.zeros(len(occ_profile), dtype=float)
        is_weekend = occ_profile.index.weekday >= 5
        hours = occ_profile.index.hour
        weekday = occ_profile.index.weekday
        n_active = occ_profile["n_active"].values

        base_prob = np.where(is_weekend, 0.15, 0.05)
        base_prob[(weekday == 2) | (weekday == 3)] += 0.05
        p_laundry = base_prob * self._day_weights("laundry", is_weekend, hours)
        p_laundry[n_active == 0] = 0

        laundry_events = self._rng.binomial(1, p_laundry)
        laundry_power[(n_active > 0) & (laundry_events == 1)] = 0.5
        return laundry_power

    def cleaning_profile(self, occ_profile: pd.DataFrame) -> np.ndarray:
        cleaning_power = np.zeros(len(occ_profile), dtype=float)
        is_weekend = occ_profile.index.weekday >= 5
        hours = occ_profile.index.hour
        n_home = occ_profile["n_home"].values
        n_active = occ_profile["n_active"].values

        percent_active = np.divide(
            n_active,
            n_home,
            out=np.zeros_like(n_active, dtype=float),
            where=n_home > 0,
        )
        mask = (percent_active > 0.2) & (percent_active < 0.8) & (n_active > 0)
        p_clean = np.where(is_weekend, 0.2, 0.05) * self._day_weights(
            "cleaning",
            is_weekend,
            hours,
        )
        p_clean[~mask] = 0

        cleaning_events = self._rng.binomial(1, p_clean)
        cleaning_power[mask & (cleaning_events == 1)] = 0.4
        return cleaning_power

    def ironing_profile(self, occ_profile: pd.DataFrame) -> np.ndarray:
        ironing_power = np.zeros(len(occ_profile), dtype=float)
        possible_hours = np.where(occ_profile["n_active"].values > 0)[0]
        n_sessions = int(len(occ_profile) / (24 * 7))
        if len(possible_hours) > 0 and n_sessions > 0:
            chosen_hours = self._rng.choice(
                possible_hours,
                size=n_sessions,
                replace=False,
            )
            ironing_power[chosen_hours] = 1.0
        return ironing_power

    def other_profile(self, occ_profile: pd.DataFrame) -> np.ndarray:
        n_home = occ_profile["n_home"].values.astype(float)
        is_weekend = occ_profile.index.weekday >= 5
        base = 0.05 * n_home
        base[is_weekend] *= 1.2
        return base

    def get_profile(self) -> pd.DataFrame:
        if self._profile is None:
            return self.generate()
        return self._profile


def plot_weekly_total_power(
    profile: pd.DataFrame,
    week_start: str = "2025-01-01",
) -> None:
    import matplotlib.pyplot as plt

    days = pd.date_range(start=week_start, periods=4, freq="D")
    fig, axes = plt.subplots(4, 1, figsize=(8, 10), sharex=True)

    for i, day in enumerate(days):
        day_profile = profile.loc[day.strftime("%Y-%m-%d")]
        axes[i].step(
            day_profile.index.hour,
            day_profile["total_power_kwh"],
            where="post",
            linewidth=2,
        )
        axes[i].set_ylim(0, float(profile["total_power_kwh"].max()) + 0.5)
        axes[i].set_xlim(0, 24)
        axes[i].set_ylabel("Power (kWh)")
        axes[i].set_title(day.strftime("%A, %Y-%m-%d"))
        axes[i].grid(True, axis="y", linestyle="--", alpha=0.5)

    axes[-1].set_xlabel("Hour")
    plt.tight_layout()
    plt.show()
