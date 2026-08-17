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
    return np.where(
        ctx.is_weekend, spec.weekend[ctx.hours], spec.weekday[ctx.hours]
    )


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


def _event_probability(
    spec: EquipmentSpec, ctx: EquipmentContext
) -> tuple[np.ndarray, np.ndarray]:
    """Shared by :func:`probabilistic_event` and
    :func:`expected_probabilistic_event`: the per-timestep firing
    probability and gate mask, fully deterministic (no RNG use) given
    ``spec``/``ctx`` — the only randomness in ``probabilistic_event`` is
    the single Bernoulli draw made from this probability afterwards."""
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
    return probability, mask


def probabilistic_event(
    spec: EquipmentSpec, ctx: EquipmentContext
) -> np.ndarray:
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
    probability, mask = _event_probability(spec, ctx)

    events = ctx.rng.binomial(1, probability)
    power = np.full(len(probability), spec.standby_power_kw, dtype=float)
    power[~mask] = 0.0
    power[mask & (events == 1)] = spec.rated_power_kw
    return power


def flat_always_on(spec: EquipmentSpec, ctx: EquipmentContext) -> np.ndarray:
    """Constant draw regardless of occupancy (e.g. a fridge)."""
    return np.full(len(ctx.profile), spec.rated_power_kw, dtype=float)


def _session_placement(
    spec: EquipmentSpec, ctx: EquipmentContext
) -> tuple[np.ndarray, int]:
    """Shared by :func:`sessions_per_week` and
    :func:`expected_sessions_per_week`: the eligible (``n_active > 0``)
    hour indices and the deterministic session count (only the
    *placement* among eligible hours is randomized, via
    ``ctx.rng.choice(..., replace=False)`` in ``sessions_per_week``)."""
    n_active = ctx.profile["n_active"].to_numpy()
    possible_hours = np.where(n_active > 0)[0]
    sessions_per_wk = spec.strategy_params.get("sessions_per_week", 1)
    n_sessions = int(len(ctx.profile) / (24 * 7) * sessions_per_wk)
    return possible_hours, n_sessions


def sessions_per_week(
    spec: EquipmentSpec, ctx: EquipmentContext
) -> np.ndarray:
    """Fires a fixed number of sessions per week at random active hours
    (e.g. ironing)."""
    power = np.zeros(len(ctx.profile), dtype=float)
    possible_hours, n_sessions = _session_placement(spec, ctx)
    if len(possible_hours) > 0 and n_sessions > 0:
        chosen = ctx.rng.choice(
            possible_hours,
            size=min(n_sessions, len(possible_hours)),
            replace=False,
        )
        power[chosen] = spec.rated_power_kw
    return power


def linear_in_occupants(
    spec: EquipmentSpec, ctx: EquipmentContext
) -> np.ndarray:
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
            f"Unknown equipment strategy {name!r}. "
            f"Registered: {sorted(_STRATEGIES)}"
        ) from exc


def expected_probabilistic_event(
    spec: EquipmentSpec, ctx: EquipmentContext
) -> np.ndarray:
    """Deterministic expected value of :func:`probabilistic_event`:
    ``E[power_t] = mask_t * (standby_power_kw + probability_t *
    (rated_power_kw - standby_power_kw))``. Used for load disaggregation
    (:func:`occupancy.core.disaggregation.estimate_equipment_usage`) as a
    basis-vector template — computed from the same deterministic
    probability array ``probabilistic_event`` itself derives before making
    its one Bernoulli draw, so no simulation is needed."""
    probability, mask = _event_probability(spec, ctx)
    power = np.full(len(probability), spec.standby_power_kw, dtype=float)
    power[mask] = spec.standby_power_kw + probability[mask] * (
        spec.rated_power_kw - spec.standby_power_kw
    )
    power[~mask] = 0.0
    return power


def expected_sessions_per_week(
    spec: EquipmentSpec, ctx: EquipmentContext
) -> np.ndarray:
    """Deterministic expected value of :func:`sessions_per_week`: by
    symmetry of sampling ``n_sessions`` slots uniformly without replacement
    from the eligible (``n_active > 0``) hours, each eligible slot's
    marginal probability of being chosen is ``n_sessions /
    N_eligible_slots``, so ``E[power_t] = rated_power_kw * n_sessions /
    N_eligible`` on eligible slots, ``0`` elsewhere. This is a valid
    marginal expectation but discards the real placement's clustering/
    spacing — see :func:`occupancy.core.disaggregation.estimate_equipment_usage`
    docstring for the caveat this implies for disaggregation results built
    from it."""
    power = np.zeros(len(ctx.profile), dtype=float)
    possible_hours, n_sessions = _session_placement(spec, ctx)
    n_eligible = len(possible_hours)
    if n_eligible > 0 and n_sessions > 0:
        power[possible_hours] = (
            spec.rated_power_kw * min(n_sessions, n_eligible) / n_eligible
        )
    return power


ExpectedValueFn = Callable[[EquipmentSpec, EquipmentContext], np.ndarray]

_EXPECTED_VALUE_STRATEGIES: dict[str, ExpectedValueFn] = {
    "flat_always_on": flat_always_on,
    "linear_in_occupants": linear_in_occupants,
    "probabilistic_event": expected_probabilistic_event,
    "sessions_per_week": expected_sessions_per_week,
}


def register_expected_value_strategy(name: str, fn: ExpectedValueFn) -> None:
    """Register a deterministic expected-value counterpart for a trigger
    strategy under ``name`` (see :func:`register_strategy`) — needed only
    by callers building a basis template without simulating, e.g.
    :func:`occupancy.core.disaggregation.estimate_equipment_usage`."""
    _EXPECTED_VALUE_STRATEGIES[name] = fn


def get_expected_value_strategy(name: str) -> ExpectedValueFn:
    try:
        return _EXPECTED_VALUE_STRATEGIES[name]
    except KeyError as exc:
        raise ValueError(
            f"No expected-value strategy registered for equipment "
            f"strategy {name!r}. Registered: "
            f"{sorted(_EXPECTED_VALUE_STRATEGIES)}"
        ) from exc


def normalize_equipment_table(
    data: dict[str, Any],
) -> dict[str, EquipmentSpec]:
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
    *,
    category_totals: dict[str, np.ndarray] | None = None,
) -> pd.Series:
    """Sum the power draw of every enabled spec over ``profile``'s index.

    ``category_totals``, if given, is populated in place with each spec's
    ``category`` (e.g. ``"kitchen"``) mapped to the summed power series of
    every enabled spec in that category -- accumulated from the exact same
    per-spec draws used for the returned total, so a category subtotal
    (e.g. household/building callers deriving a ``cooking_active`` signal
    from the ``"kitchen"`` category) stays internally consistent with
    ``total_power_kwh`` rather than requiring a second, independently
    seeded pass over the same specs. Backward compatible: omitting it
    changes nothing about the returned series or the RNG draw sequence.
    """
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
        power = strategy(spec, ctx)
        total += power
        if category_totals is not None:
            if spec.category not in category_totals:
                category_totals[spec.category] = np.zeros(len(profile))
            category_totals[spec.category] += power
    return pd.Series(total, index=profile.index, name="total_power_kwh")
