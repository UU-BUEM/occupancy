"""Config-driven equipment/appliance model shared by households and
service buildings.

An :class:`EquipmentSpec` is a data row (JSON), not a Python method — adding
or removing an appliance/equipment item is a config change. Each spec picks
a named *trigger strategy* (how/when it draws power); new strategies
register via :func:`register_strategy` for the rare case an item needs
genuinely novel logic.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class EquipmentSpec:
    """One equipment/appliance definition."""

    name: str
    category: str = "other"
    rated_power_kw: float = 0.0
    standby_power_kw: float = 0.0
    weekday: np.ndarray = field(default_factory=lambda: np.zeros(24))
    weekend: np.ndarray = field(default_factory=lambda: np.zeros(24))
    strategy: str = "probabilistic_event"
    strategy_params: dict[str, Any] = field(default_factory=dict)
    ownership_probability: float = 1.0
    enabled: bool = True


@dataclass(frozen=True)
class EquipmentContext:
    """Everything a trigger strategy needs to compute one power series."""

    profile: pd.DataFrame
    rng: np.random.Generator
    hours: np.ndarray
    is_weekend: np.ndarray
    weekday_index: np.ndarray


StrategyFn = Callable[[EquipmentSpec, EquipmentContext], np.ndarray]


def _weight(spec: EquipmentSpec, ctx: EquipmentContext) -> np.ndarray:
    return np.where(ctx.is_weekend, spec.weekend[ctx.hours], spec.weekday[ctx.hours])


def _gate_mask(
    spec: EquipmentSpec, ctx: EquipmentContext
) -> tuple[np.ndarray, np.ndarray]:
    """Return (mask, percent_active) for the strategy's configured gate."""
    n_present = ctx.profile["n_present"].to_numpy(dtype=float)
    n_active = ctx.profile["n_active"].to_numpy(dtype=float)
    percent_active = np.divide(
        n_active, n_present, out=np.zeros_like(n_active), where=n_present > 0
    )

    gate = spec.strategy_params.get("gate", "active")
    if gate == "active":
        mask = n_active > 0
    elif gate == "present":
        mask = n_present > 0
    else:
        mask = np.ones(len(n_present), dtype=bool)

    band = spec.strategy_params.get("activity_band")
    if band is not None:
        mask = mask & (percent_active > band[0]) & (percent_active < band[1])

    return mask, percent_active


def probabilistic_event(spec: EquipmentSpec, ctx: EquipmentContext) -> np.ndarray:
    """Generalized "fires with some hourly probability" trigger, covering
    what were previously bespoke tv/cooking/laundry/cleaning methods.

    ``strategy_params``:
    - ``gate``: ``"active"`` (default), ``"present"``, or ``"none"`` — which
      occupancy count must be > 0 for the item to be eligible at all.
    - ``activity_band``: optional ``[min, max]`` on active/present fraction.
    - ``intercept`` / ``active_fraction_scale``: probability =
      ``intercept + active_fraction_scale * percent_active``, or
    - ``weekday_rate`` / ``weekend_rate``: flat base rate per day-type,
      optionally bumped by ``day_bonus: [{"days": [2, 3], "amount": 0.05}]``.
    Either base-rate mode is then multiplied by the spec's
    ``weekday``/``weekend`` hourly weight array.
    """
    params = spec.strategy_params
    mask, percent_active = _gate_mask(spec, ctx)

    if "weekday_rate" in params:
        base_prob = np.where(
            ctx.is_weekend,
            params.get("weekend_rate", params["weekday_rate"]),
            params["weekday_rate"],
        )
        for bonus in params.get("day_bonus", []):
            bumped = np.isin(ctx.weekday_index, bonus["days"])
            base_prob = base_prob + bumped * bonus["amount"]
    else:
        base_prob = (
            params.get("intercept", 0.0)
            + params.get("active_fraction_scale", 0.0) * percent_active
        )

    probability = np.clip(base_prob * _weight(spec, ctx), 0.0, 1.0)
    probability = np.where(mask, probability, 0.0)

    events = ctx.rng.binomial(1, probability)
    power = np.full(len(probability), spec.standby_power_kw, dtype=float)
    power[~mask] = 0.0
    power[mask & (events == 1)] = spec.rated_power_kw
    return power


def flat_always_on(spec: EquipmentSpec, ctx: EquipmentContext) -> np.ndarray:
    """Constant draw regardless of occupancy (e.g. a fridge)."""
    return np.full(len(ctx.profile), spec.rated_power_kw, dtype=float)


def sessions_per_week(spec: EquipmentSpec, ctx: EquipmentContext) -> np.ndarray:
    """Fires a fixed number of sessions per week at random active hours
    (e.g. ironing)."""
    power = np.zeros(len(ctx.profile), dtype=float)
    n_active = ctx.profile["n_active"].to_numpy()
    possible_hours = np.where(n_active > 0)[0]

    sessions_per_wk = spec.strategy_params.get("sessions_per_week", 1)
    n_sessions = int(len(ctx.profile) / (24 * 7) * sessions_per_wk)
    if len(possible_hours) > 0 and n_sessions > 0:
        chosen = ctx.rng.choice(
            possible_hours, size=min(n_sessions, len(possible_hours)), replace=False
        )
        power[chosen] = spec.rated_power_kw
    return power


def linear_in_occupants(spec: EquipmentSpec, ctx: EquipmentContext) -> np.ndarray:
    """Draw scales linearly with the number of present occupants (e.g. a
    catch-all "other" plug-load category)."""
    n_present = ctx.profile["n_present"].to_numpy(dtype=float)
    base = spec.rated_power_kw * n_present
    weekend_multiplier = spec.strategy_params.get("weekend_multiplier", 1.0)
    base = np.where(ctx.is_weekend, base * weekend_multiplier, base)
    return base


_STRATEGIES: dict[str, StrategyFn] = {
    "probabilistic_event": probabilistic_event,
    "flat_always_on": flat_always_on,
    "sessions_per_week": sessions_per_week,
    "linear_in_occupants": linear_in_occupants,
}


def register_strategy(name: str, fn: StrategyFn) -> None:
    """Register a new equipment trigger strategy under ``name``."""
    _STRATEGIES[name] = fn


def get_strategy(name: str) -> StrategyFn:
    try:
        return _STRATEGIES[name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown equipment strategy {name!r}. Registered: {sorted(_STRATEGIES)}"
        ) from exc


def normalize_equipment_table(data: dict[str, Any]) -> dict[str, EquipmentSpec]:
    """Parse a raw JSON equipment mapping into ``EquipmentSpec`` objects."""
    specs: dict[str, EquipmentSpec] = {}
    for name, row in data.items():
        if name.startswith("_"):
            continue
        specs[name] = EquipmentSpec(
            name=name,
            category=row.get("category", "other"),
            rated_power_kw=float(row.get("rated_power_kw", 0.0)),
            standby_power_kw=float(row.get("standby_power_kw", 0.0)),
            weekday=np.asarray(row["weekday"], dtype=float),
            weekend=np.asarray(row["weekend"], dtype=float),
            strategy=row.get("strategy", "probabilistic_event"),
            strategy_params=row.get("strategy_params", {}),
            ownership_probability=float(row.get("ownership_probability", 1.0)),
            enabled=bool(row.get("enabled", True)),
        )
    return specs


def generate_equipment_power(
    specs: list[EquipmentSpec],
    profile: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.Series:
    """Sum the power draw of every enabled spec over ``profile``'s index."""
    ctx = EquipmentContext(
        profile=profile,
        rng=rng,
        hours=profile.index.hour.to_numpy(),
        is_weekend=profile.index.weekday >= 5,
        weekday_index=profile.index.weekday.to_numpy(),
    )
    total = np.zeros(len(profile), dtype=float)
    for spec in specs:
        if not spec.enabled:
            continue
        strategy = get_strategy(spec.strategy)
        total += strategy(spec, ctx)
    return pd.Series(total, index=profile.index, name="total_power_kwh")
