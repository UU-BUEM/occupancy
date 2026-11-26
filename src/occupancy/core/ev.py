"""Stochastic electric-vehicle (EV) mobility, state-of-charge and charging
model, driven by an already-generated occupancy profile.

Why this is not an :class:`~occupancy.core.equipment.EquipmentSpec`
-------------------------------------------------------------------
Every equipment strategy maps occupancy to an hourly power draw with no
memory. An EV does not work like that: whether and how long it charges
tonight depends on how far it was driven today, how full the battery
already is, whether the driver bothers to plug in, and when the car leaves
tomorrow. This module therefore simulates the car day by day with a
persistent state of charge (SOC), and returns its own columns instead of
adding to ``total_power_kwh``. That separation matters downstream:
``total_power_kwh`` is buem's ``elecLoad``, an *internal heat gain*, and
the charger and car sit in a driveway or garage, so EV charging must never
heat the building model.

Method (see ``docs/ev/design.md`` for the full write-up and sources)
-------------------------------------------------------------------
Per calendar day:

1. **Trip draw.** The car is used with a day-type probability. Departure
   time, arrival time and daily distance are drawn *jointly* through a
   Gaussian copula -- the dependence approach of Lojowska et al. (2012,
   IEEE Trans. Power Systems 27:1960-1968) for Dutch EV load -- with
   empirical hourly marginals for the two times and a lognormal marginal
   for distance whose scale is derived from a target annual mileage.
2. **Presence coupling.** Candidate trips are checked against the
   household's own occupancy profile: a trip is accepted when someone is
   out of the house for most of its window. This keeps the car's absence
   consistent with the people's.
3. **Driving and away charging.** Trip energy = distance x consumption.
   Some of it is replenished away from home (workplace/public/fast
   charging, ``away_charging_mode``), either opportunistically or because
   the trip would otherwise run the battery below its reserve. That energy
   is reported separately; it never reaches the household meter.
4. **Plug-in decision.** On arrival the driver plugs in with a probability
   that falls with the arrival SOC (after Brady & O'Mahony 2016's
   SOC-conditioned charging decision), after a delay drawn from their
   observed distribution (~70% immediately, the rest 15 min - 5 h later).
5. **Charging.** From plug-in until the SOC target is reached or the car
   next leaves, at ``min(charger power, car on-board limit)`` with a
   charging efficiency, slowing linearly above a taper SOC
   (constant-current/constant-voltage approximation). The SOC carries over
   to the next day, so a car with a big battery and short trips charges
   only every few days -- an emergent behaviour, not a fixed rate.

All parameters live in data (``households/data/ev.json`` by default) and
can be overridden per call, so survey-derived distributions slot in
without code changes.
"""

from __future__ import annotations

import copy
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.special import ndtr

#: Columns :func:`simulate_ev` returns, in order.
EV_COLUMNS: tuple[str, ...] = (
    "ev_charging_kw",
    "ev_plugged_in",
    "ev_at_home",
    "ev_soc",
    "ev_stored_kwh",
    "ev_drive_kwh",
    "ev_away_charging_kwh",
)

_CURRENTS = ("ac", "dc")


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------


def _deep_merge(
    base: Mapping[str, Any], overrides: Mapping[str, Any], path: str = ""
) -> dict[str, Any]:
    """Recursively merge ``overrides`` into a copy of ``base``.

    Unknown keys raise, so a typo in a user/survey override fails loudly
    instead of being silently ignored. Keys starting with ``_`` are
    documentation and always allowed. A new entry under
    ``charging_modes`` is allowed too (defining an extra charging mode).
    """
    merged = copy.deepcopy(dict(base))
    for key, value in overrides.items():
        where = f"{path}.{key}" if path else key
        if key.startswith("_"):
            merged[key] = copy.deepcopy(value)
            continue
        if key not in merged:
            if path == "charging_modes":
                merged[key] = copy.deepcopy(value)
                continue
            raise ValueError(
                f"Unknown EV config key {where!r}. Known keys here: "
                f"{sorted(k for k in merged if not k.startswith('_'))}"
            )
        if isinstance(merged[key], Mapping) and isinstance(value, Mapping):
            merged[key] = _deep_merge(merged[key], value, where)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _cholesky(matrix: np.ndarray) -> list[list[float]]:
    """Lower-triangular Cholesky factor of a small symmetric matrix, in
    plain Python; raises ``ValueError`` unless it is positive definite.

    Deliberately avoids ``numpy.linalg`` and the ``@`` operator: both go
    through the BLAS/LAPACK library numpy was built against, and a broken
    BLAS installation (a known failure mode of mixed conda channels on
    Windows) aborts the interpreter outright rather than raising. For a
    3x3 copula correlation matrix, the pure-Python factorisation costs
    nothing and keeps importing this package independent of BLAS.
    """
    n = len(matrix)
    lower = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            partial = sum(lower[i][k] * lower[j][k] for k in range(j))
            if i == j:
                pivot = float(matrix[i][i]) - partial
                if pivot <= 0:
                    raise ValueError(
                        "copula_correlation must be positive definite"
                    )
                lower[i][j] = math.sqrt(pivot)
            else:
                lower[i][j] = (float(matrix[i][j]) - partial) / lower[j][j]
    return lower


def _hour_weights(values: Any, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    _require(array.shape == (24,), f"{name} must have 24 values")
    _require(bool((array >= 0).all()), f"{name} must be non-negative")
    _require(float(array.sum()) > 0, f"{name} must not be all zero")
    return array / array.sum()


@dataclass(frozen=True)
class ChargingMode:
    """One way of charging: a charger rating plus its losses and taper."""

    name: str
    power_kw: float
    current: str
    efficiency: float
    taper_start_soc: float
    taper_end_fraction: float

    def __post_init__(self) -> None:
        _require(self.power_kw > 0, f"{self.name}: power_kw must be > 0")
        _require(
            self.current in _CURRENTS,
            f"{self.name}: current must be one of {_CURRENTS}",
        )
        _require(
            0 < self.efficiency <= 1, f"{self.name}: efficiency in (0, 1]"
        )
        _require(
            0 < self.taper_start_soc <= 1,
            f"{self.name}: taper_start_soc in (0, 1]",
        )
        _require(
            0 < self.taper_end_fraction <= 1,
            f"{self.name}: taper_end_fraction in (0, 1]",
        )

    @classmethod
    def from_mapping(cls, name: str, row: Mapping[str, Any]) -> ChargingMode:
        return cls(
            name=name,
            power_kw=float(row["power_kw"]),
            current=str(row["current"]).lower(),
            efficiency=float(row["efficiency"]),
            taper_start_soc=float(row.get("taper_start_soc", 1.0)),
            taper_end_fraction=float(row.get("taper_end_fraction", 1.0)),
        )


@dataclass(frozen=True)
class EVConfig:
    """Validated EV parameters. Build with :meth:`from_mapping` (or
    :func:`occupancy.households.ev.load_ev_config` for the bundled
    defaults) rather than directly; :meth:`with_overrides` returns a
    modified copy, e.g. ``cfg.with_overrides({"charging_modes": {"slow":
    {"power_kw": 11.0}}})``."""

    raw: dict[str, Any]
    ownership_probability: float
    has_home_charger: bool
    home_mode: ChargingMode
    away_mode: ChargingMode
    battery_capacity_kwh: float
    consumption_kwh_per_km: float
    max_ac_power_kw: float
    max_dc_power_kw: float
    monthly_consumption_multiplier: np.ndarray
    soc_min: float
    soc_target_home: float
    soc_target_away: float
    soc_initial: float
    annual_km: float
    use_probability_weekday: float
    use_probability_weekend: float
    departure_weights: np.ndarray  # (24, 2): [:, 0] weekday, [:, 1] weekend
    arrival_weights: np.ndarray  # (24, 2)
    distance_sigma: float
    max_daily_km: float
    min_trip_hours: float
    copula_correlation: np.ndarray  # (3, 3)
    coupling_enabled: bool
    coupling_max_draws: int
    coupling_min_absent_fraction: float
    plug_soc_edges: np.ndarray
    plug_probability: np.ndarray
    plug_model: str  # "soc_table" or "logistic"
    plug_logistic_mu: float
    plug_logistic_s: float
    plug_immediate_probability: float
    plug_delay_min_hours: float
    plug_delay_max_hours: float
    evening_check_hour: float
    away_probability: float
    away_fraction: float
    home_charging_start_hour: float | None
    warmup_days: int
    substep_hours: float

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> EVConfig:
        data = copy.deepcopy(dict(raw))
        modes = data["charging_modes"]
        home_name = data["home_charging_mode"]
        away_name = data["away_charging_mode"]
        for label, name in (("home", home_name), ("away", away_name)):
            _require(
                name in modes,
                f"{label}_charging_mode {name!r} is not defined in "
                f"charging_modes ({sorted(modes)})",
            )
        vehicle = data["vehicle"]
        battery = data["battery"]
        mobility = data["mobility"]
        plug = data["plug_in"]
        away = data["away_charging"]
        sim = data["simulation"]
        coupling = mobility["presence_coupling"]

        monthly = np.asarray(
            vehicle["monthly_consumption_multiplier"], dtype=float
        )
        correlation = np.asarray(mobility["copula_correlation"], dtype=float)
        edges = np.asarray(plug["soc_bin_upper_edges"], dtype=float)
        probability = np.asarray(plug["probability"], dtype=float)
        # .get(): mappings saved before these keys existed still load.
        logistic = plug.get("logistic", {})
        start_hour = data.get("home_charging_start_hour")

        config = cls(
            raw=data,
            ownership_probability=float(data["ownership_probability"]),
            has_home_charger=bool(data["has_home_charger"]),
            home_mode=ChargingMode.from_mapping(home_name, modes[home_name]),
            away_mode=ChargingMode.from_mapping(away_name, modes[away_name]),
            battery_capacity_kwh=float(vehicle["battery_capacity_kwh"]),
            consumption_kwh_per_km=float(vehicle["consumption_kwh_per_km"]),
            max_ac_power_kw=float(vehicle["max_ac_power_kw"]),
            max_dc_power_kw=float(vehicle["max_dc_power_kw"]),
            monthly_consumption_multiplier=monthly,
            soc_min=float(battery["soc_min"]),
            soc_target_home=float(battery["soc_target_home"]),
            soc_target_away=float(battery["soc_target_away"]),
            soc_initial=float(battery["soc_initial"]),
            annual_km=float(mobility["annual_km"]),
            use_probability_weekday=float(
                mobility["use_probability"]["weekday"]
            ),
            use_probability_weekend=float(
                mobility["use_probability"]["weekend"]
            ),
            departure_weights=np.column_stack(
                [
                    _hour_weights(
                        mobility["departure_hour_weights"][day],
                        f"departure_hour_weights.{day}",
                    )
                    for day in ("weekday", "weekend")
                ]
            ),
            arrival_weights=np.column_stack(
                [
                    _hour_weights(
                        mobility["arrival_hour_weights"][day],
                        f"arrival_hour_weights.{day}",
                    )
                    for day in ("weekday", "weekend")
                ]
            ),
            distance_sigma=float(mobility["distance_lognormal_sigma"]),
            max_daily_km=float(mobility["max_daily_km"]),
            min_trip_hours=float(mobility["min_trip_hours"]),
            copula_correlation=correlation,
            coupling_enabled=bool(coupling["enabled"]),
            coupling_max_draws=int(coupling["max_draws"]),
            coupling_min_absent_fraction=float(
                coupling["min_absent_fraction"]
            ),
            plug_soc_edges=edges,
            plug_probability=probability,
            plug_model=str(plug.get("model", "soc_table")),
            plug_logistic_mu=float(logistic.get("indifference_soc", 0.5)),
            plug_logistic_s=float(logistic.get("sensitivity_soc", 0.0782)),
            plug_immediate_probability=float(plug["immediate_probability"]),
            plug_delay_min_hours=float(plug["delay_min_hours"]),
            plug_delay_max_hours=float(plug["delay_max_hours"]),
            evening_check_hour=float(plug["evening_check_hour"]),
            away_probability=float(away["probability_per_trip_day"]),
            away_fraction=float(away["fraction_of_trip_energy"]),
            home_charging_start_hour=(
                None if start_hour is None else float(start_hour)
            ),
            warmup_days=int(sim["warmup_days"]),
            substep_hours=float(sim["substep_hours"]),
        )
        config._validate()
        return config

    def _validate(self) -> None:
        def unit(value: float, name: str) -> None:
            _require(0 <= value <= 1, f"{name} must be in [0, 1]")

        unit(self.ownership_probability, "ownership_probability")
        _require(self.battery_capacity_kwh > 0, "battery_capacity_kwh > 0")
        _require(self.consumption_kwh_per_km > 0, "consumption_kwh_per_km > 0")
        _require(self.max_ac_power_kw > 0, "max_ac_power_kw > 0")
        _require(self.max_dc_power_kw > 0, "max_dc_power_kw > 0")
        _require(
            self.monthly_consumption_multiplier.shape == (12,)
            and bool((self.monthly_consumption_multiplier > 0).all()),
            "monthly_consumption_multiplier must be 12 positive values",
        )
        for name in ("soc_min", "soc_target_home", "soc_target_away"):
            unit(getattr(self, name), name)
        unit(self.soc_initial, "soc_initial")
        _require(
            self.soc_min < self.soc_target_home,
            "soc_min must be below soc_target_home",
        )
        _require(
            self.soc_min <= self.soc_target_away,
            "soc_min must not exceed soc_target_away",
        )
        _require(self.annual_km >= 0, "annual_km must be >= 0")
        unit(self.use_probability_weekday, "use_probability.weekday")
        unit(self.use_probability_weekend, "use_probability.weekend")
        _require(self.distance_sigma > 0, "distance_lognormal_sigma > 0")
        _require(self.max_daily_km > 0, "max_daily_km > 0")
        _require(0 <= self.min_trip_hours < 24, "min_trip_hours in [0, 24)")
        corr = self.copula_correlation
        _require(corr.shape == (3, 3), "copula_correlation must be 3x3")
        _require(
            bool(np.allclose(corr, corr.T))
            and bool(np.allclose(np.diag(corr), 1.0)),
            "copula_correlation must be symmetric with a unit diagonal",
        )
        _cholesky(corr)  # raises unless positive definite
        _require(self.coupling_max_draws >= 1, "max_draws must be >= 1")
        unit(self.coupling_min_absent_fraction, "min_absent_fraction")
        edges, probability = self.plug_soc_edges, self.plug_probability
        _require(
            edges.ndim == 1
            and edges.shape == probability.shape
            and len(edges) >= 1,
            "plug_in.soc_bin_upper_edges and probability must be equal-"
            "length lists",
        )
        _require(
            bool(np.all(np.diff(edges) > 0)) and edges[-1] >= 1.0,
            "plug_in.soc_bin_upper_edges must increase and end at >= 1.0",
        )
        _require(
            bool(((probability >= 0) & (probability <= 1)).all()),
            "plug_in.probability values must be in [0, 1]",
        )
        _require(
            self.plug_model in ("soc_table", "logistic"),
            "plug_in.model must be 'soc_table' or 'logistic'",
        )
        unit(self.plug_logistic_mu, "plug_in.logistic.indifference_soc")
        _require(
            self.plug_logistic_s > 0,
            "plug_in.logistic.sensitivity_soc must be > 0",
        )
        _require(
            self.home_charging_start_hour is None
            or 0 <= self.home_charging_start_hour < 24,
            "home_charging_start_hour must be null or in [0, 24)",
        )
        unit(self.plug_immediate_probability, "immediate_probability")
        _require(
            0 <= self.plug_delay_min_hours <= self.plug_delay_max_hours,
            "need 0 <= delay_min_hours <= delay_max_hours",
        )
        _require(
            0 <= self.evening_check_hour < 24, "evening_check_hour in [0, 24)"
        )
        unit(self.away_probability, "probability_per_trip_day")
        unit(self.away_fraction, "fraction_of_trip_energy")
        _require(self.warmup_days >= 0, "warmup_days must be >= 0")
        _require(
            0 < self.substep_hours <= 1, "substep_hours must be in (0, 1]"
        )

    # -- convenience ------------------------------------------------------

    def with_overrides(self, overrides: Mapping[str, Any]) -> EVConfig:
        """A new config with ``overrides`` deep-merged over this one."""
        return EVConfig.from_mapping(_deep_merge(self.raw, overrides))

    def to_dict(self) -> dict[str, Any]:
        """The merged parameter mapping (JSON-serializable)."""
        return copy.deepcopy(self.raw)

    def effective_power_kw(self, mode: ChargingMode) -> float:
        """Charging power actually drawn: the lower of the charger rating
        and the car's on-board limit for that current type."""
        limit = (
            self.max_ac_power_kw
            if mode.current == "ac"
            else self.max_dc_power_kw
        )
        return min(mode.power_kw, limit)

    def plug_in_probability(self, soc: float) -> float:
        """Chance of plugging in at home on arrival, given the SOC.

        ``soc_table``: the step table ``plug_in.probability``.
        ``logistic``: Harbrecht et al. (2018) / Fischer et al. (2019)
        connection model, ``1 / (1 + exp((soc - mu) / s))``: the driver is
        indifferent (p = 0.5) at ``mu`` and ``s`` sets how sharply the
        decision switches around it."""
        if self.plug_model == "logistic":
            z = (soc - self.plug_logistic_mu) / self.plug_logistic_s
            return 1.0 / (1.0 + math.exp(min(z, 700.0)))
        index = int(np.searchsorted(self.plug_soc_edges, soc, side="left"))
        index = min(index, len(self.plug_probability) - 1)
        return float(self.plug_probability[index])


def resolve_ev_config(
    value: EVConfig | Mapping[str, Any] | str | Path | None,
    base: EVConfig,
) -> EVConfig:
    """Turn the flexible ``ev_config=`` argument accepted across the API
    into an :class:`EVConfig`: ``None`` -> ``base``; an ``EVConfig`` -> as
    is; a mapping -> deep-merged over ``base``; a path -> a JSON file of
    overrides, deep-merged over ``base``."""
    if value is None:
        return base
    if isinstance(value, EVConfig):
        return value
    if isinstance(value, str | Path):
        with Path(value).open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    if not isinstance(value, Mapping):
        raise TypeError(
            "ev_config must be an EVConfig, a mapping of overrides, a JSON "
            f"file path, or None -- got {type(value).__name__}"
        )
    return base.with_overrides(value)


# --------------------------------------------------------------------------
# Simulation
# --------------------------------------------------------------------------


@dataclass
class _DayPlan:
    """Pre-drawn randomness for every day, so the day loop itself is
    deterministic (and a warm-up can replay the first days exactly)."""

    used: np.ndarray
    departure: np.ndarray  # hours after midnight
    arrival: np.ndarray
    distance_km: np.ndarray
    u_plug: np.ndarray
    plug_delay: np.ndarray
    u_away: np.ndarray
    u_evening: np.ndarray
    evening_delay: np.ndarray


def _hour_of_day_draw(
    u: np.ndarray, cdf: np.ndarray, jitter: np.ndarray
) -> np.ndarray:
    """Inverse-CDF draw of an hour from a 24-bin pmf, plus a uniform
    position within that hour."""
    hours = np.searchsorted(cdf, u, side="right")
    return np.minimum(hours, 23) + jitter


def _draw_plan(
    config: EVConfig,
    n_days: int,
    day_is_weekend: np.ndarray,
    absent_by_day: np.ndarray | None,
    rng: np.random.Generator,
) -> _DayPlan:
    k = config.coupling_max_draws if absent_by_day is not None else 1

    use_p = np.where(
        day_is_weekend,
        config.use_probability_weekend,
        config.use_probability_weekday,
    )
    used = rng.random(n_days) < use_p

    # Lognormal scale so E[annual km] = annual_km over this horizon.
    expected_use_days = float(use_p.sum())
    days_per_year = 365.25
    if expected_use_days > 0 and config.annual_km > 0:
        mean_km = (
            config.annual_km * (n_days / days_per_year) / (expected_use_days)
        )
        mu = math.log(mean_km) - 0.5 * config.distance_sigma**2
    else:
        mu = -math.inf

    chol = _cholesky(config.copula_correlation)
    independent = rng.standard_normal((n_days, k, 3))
    # z = independent x chol-transposed, written out element-wise so no
    # BLAS-backed matrix product is involved (see _cholesky).
    z = np.stack(
        [
            sum(chol[i][j] * independent[..., j] for j in range(i + 1))
            for i in range(3)
        ],
        axis=-1,
    )
    jitter = rng.random((n_days, k, 2))
    wk = day_is_weekend.astype(int)[:, None]
    dep_cdf = np.cumsum(config.departure_weights, axis=0)
    arr_cdf = np.cumsum(config.arrival_weights, axis=0)
    u_dep = ndtr(z[..., 0])
    u_arr = ndtr(z[..., 1])
    departure = np.empty((n_days, k))
    arrival = np.empty((n_days, k))
    for day_type in (0, 1):
        mask = np.broadcast_to(wk == day_type, (n_days, k))
        departure[mask] = _hour_of_day_draw(
            u_dep[mask], dep_cdf[:, day_type], jitter[..., 0][mask]
        )
        arrival[mask] = _hour_of_day_draw(
            u_arr[mask], arr_cdf[:, day_type], jitter[..., 1][mask]
        )
    distance = np.minimum(
        np.exp(mu + config.distance_sigma * z[..., 2]), config.max_daily_km
    )
    valid = (arrival - departure) >= config.min_trip_hours

    if absent_by_day is not None:
        # Fraction of the trip's (whole) hours with someone out.
        cum = np.concatenate(
            [np.zeros((n_days, 1)), np.cumsum(absent_by_day, axis=1)], axis=1
        )
        start = np.floor(departure).astype(int)
        stop = np.minimum(np.ceil(arrival).astype(int), 24)
        stop = np.maximum(stop, start + 1)
        rows = np.arange(n_days)[:, None]
        score = (cum[rows, stop] - cum[rows, start]) / (stop - start)
        score = np.where(valid, score, -1.0)
        good = score >= config.coupling_min_absent_fraction
        first_good = np.argmax(good, axis=1)
        best = np.argmax(score, axis=1)
        choice = np.where(good.any(axis=1), first_good, best)
        chosen_score = score[np.arange(n_days), choice]
        used &= chosen_score > 0
    else:
        choice = np.zeros(n_days, dtype=int)
        used &= valid[:, 0]

    pick = np.arange(n_days), choice
    used &= distance[pick] > 0

    def delays(size: int) -> np.ndarray:
        immediate = rng.random(size) < config.plug_immediate_probability
        late = rng.uniform(
            config.plug_delay_min_hours, config.plug_delay_max_hours, size
        )
        return np.where(immediate, 0.0, late)

    return _DayPlan(
        used=used,
        departure=departure[pick],
        arrival=arrival[pick],
        distance_km=distance[pick],
        u_plug=rng.random(n_days),
        plug_delay=delays(n_days),
        u_away=rng.random(n_days),
        u_evening=rng.random(n_days),
        evening_delay=delays(n_days),
    )


class _Simulator:
    """Day-by-day EV state machine over a continuous time axis in hours
    (t = 0 at the profile's first timestep)."""

    def __init__(
        self,
        config: EVConfig,
        n_hours: int,
        day_month: np.ndarray,
    ) -> None:
        self.cfg = config
        self.n = n_hours
        self.day_month = day_month
        self.cap = config.battery_capacity_kwh
        self.home_power = config.effective_power_kw(config.home_mode)
        self.record = False
        self._reset_outputs()
        self.soc = config.soc_initial
        self.plugged = False
        self.plug_time = 0.0
        self.home_since = 0.0

    def _reset_outputs(self) -> None:
        n = self.n
        self.charging = np.zeros(n)
        self.plugged_frac = np.zeros(n)
        self.home_frac = np.zeros(n)
        self.drive = np.zeros(n)
        self.away = np.zeros(n)
        self.soc_t: list[float] = []
        self.soc_v: list[float] = []

    # -- recording helpers ------------------------------------------------

    def _point(self, t: float) -> None:
        if self.record:
            self.soc_t.append(t)
            self.soc_v.append(self.soc)

    def _spread(self, target: np.ndarray, t0: float, t1: float, total: float):
        """Add ``total`` spread uniformly over [t0, t1) into hourly bins
        (``total`` = 1 per hour gives the time-fraction of each hour)."""
        if not self.record or t1 <= t0:
            return
        rate = total / (t1 - t0)
        t = max(t0, 0.0)
        end = min(t1, float(self.n))
        while t < end - 1e-12:
            hour = int(t)
            step = min(end, hour + 1.0) - t
            target[hour] += rate * step
            t += step

    def _interval(self, target: np.ndarray, t0: float, t1: float) -> None:
        self._spread(target, t0, t1, t1 - t0)

    # -- physics ----------------------------------------------------------

    def _charge_home(self, t0: float, t1: float) -> None:
        """Charge at home from t0 until t1 or the SOC target."""
        cfg = self.cfg
        mode = cfg.home_mode
        target = cfg.soc_target_home
        eff = mode.efficiency
        t = t0
        self._point(t)
        while t < t1 - 1e-9 and self.soc < target - 1e-9:
            if self.soc < mode.taper_start_soc:
                factor = 1.0
                soc_stop = min(target, mode.taper_start_soc)
                need = (
                    (soc_stop - self.soc) * self.cap / (self.home_power * eff)
                )
            else:
                progress = (self.soc - mode.taper_start_soc) / max(
                    1.0 - mode.taper_start_soc, 1e-9
                )
                factor = 1.0 - (1.0 - mode.taper_end_fraction) * progress
                power = self.home_power * factor
                need = min(
                    cfg.substep_hours,
                    (target - self.soc) * self.cap / (power * eff),
                )
            next_hour = math.floor(t) + 1.0
            dt = min(need, t1 - t, next_hour - t)
            if dt <= 0:
                break
            grid_kwh = self.home_power * factor * dt
            self.soc = min(target, self.soc + grid_kwh * eff / self.cap)
            if self.record and 0 <= t < self.n:
                self.charging[int(t)] += grid_kwh
            t += dt
            self._point(t)

    def _close_home_interval(self, t_leave: float) -> None:
        """Book the time at home / plugged in up to ``t_leave`` and charge
        through that window if plugged in."""
        self._interval(self.home_frac, self.home_since, t_leave)
        if self.plugged and self.cfg.has_home_charger:
            start = max(self.plug_time, self.home_since)
            if start < t_leave:
                self._interval(self.plugged_frac, start, t_leave)
                self._charge_home(self._charge_start(start), t_leave)
        self.plugged = False

    def _charge_start(self, plugged_at: float) -> float:
        """When charging begins after plugging in: at once, or with a
        timer (``home_charging_start_hour``) at the next occurrence of that
        clock hour, e.g. the start of an off-peak tariff. The car stays
        connected (and available to a smart-charging optimiser) either
        way."""
        hour = self.cfg.home_charging_start_hour
        if hour is None:
            return plugged_at
        start = 24.0 * math.floor(plugged_at / 24.0) + hour
        if start < plugged_at - 1e-9:
            start += 24.0
        return start

    def _maybe_plug(self, t: float, u: float, delay: float) -> None:
        if not self.cfg.has_home_charger or self.plugged:
            return
        if u < self.cfg.plug_in_probability(self.soc):
            self.plugged = True
            self.plug_time = t + delay

    def _trip(
        self, day: int, t_dep: float, t_arr: float, km: float, u_away: float
    ):
        cfg = self.cfg
        energy = (
            km
            * cfg.consumption_kwh_per_km
            * cfg.monthly_consumption_multiplier[self.day_month[day] - 1]
        )
        soc_after_drive = self.soc - energy / self.cap
        away_kwh = 0.0  # battery side
        if u_away < cfg.away_probability:
            room = (cfg.soc_target_away - soc_after_drive) * self.cap
            away_kwh = max(0.0, min(cfg.away_fraction * energy, room))
        soc_arrival = soc_after_drive + away_kwh / self.cap
        if soc_arrival < cfg.soc_min:  # forced top-up on the way
            away_kwh += (cfg.soc_min - soc_arrival) * self.cap
            soc_arrival = cfg.soc_min
        self._spread(self.drive, t_dep, t_arr, energy)
        self._spread(
            self.away, t_dep, t_arr, away_kwh / cfg.away_mode.efficiency
        )
        self._point(t_dep)
        self.soc = soc_arrival
        self._point(t_arr)
        self.home_since = t_arr

    # -- main loop --------------------------------------------------------

    def run_days(self, plan: _DayPlan, days: range) -> None:
        cfg = self.cfg
        for day in days:
            midnight = 24.0 * day
            if plan.used[day]:
                t_dep = midnight + plan.departure[day]
                t_arr = midnight + plan.arrival[day]
                self._close_home_interval(t_dep)
                self._trip(
                    day, t_dep, t_arr, plan.distance_km[day], plan.u_away[day]
                )
                self._maybe_plug(t_arr, plan.u_plug[day], plan.plug_delay[day])
            elif not self.plugged:
                self._maybe_plug(
                    midnight + cfg.evening_check_hour,
                    plan.u_evening[day],
                    plan.evening_delay[day],
                )

    def finish(self, t_end: float) -> None:
        """Close the open home interval at ``t_end`` (end of horizon)."""
        was_plugged, plug_time = self.plugged, self.plug_time
        self._close_home_interval(t_end)
        self.plugged, self.plug_time = was_plugged, plug_time
        self.home_since = t_end


def _validate_index(index: pd.DatetimeIndex) -> None:
    if len(index) < 24:
        raise ValueError("EV simulation needs at least 24 hourly timesteps")
    step = index[1] - index[0]
    if (
        step != pd.Timedelta(hours=1)
        or not ((index[1:] - index[:-1]) == step).all()
    ):
        raise ValueError("EV simulation needs an evenly hourly index")
    if index[0].hour != 0:
        raise ValueError("EV simulation needs the index to start at 00:00")


def simulate_ev(
    profile: pd.DataFrame,
    *,
    num_persons: int | None,
    config: EVConfig,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Simulate one household EV over ``profile``'s hourly index.

    ``profile`` needs ``n_present`` for presence coupling (pass
    ``num_persons`` too); without either, trips are drawn uncoupled.

    Returns a DataFrame (same index) with :data:`EV_COLUMNS`:

    - ``ev_charging_kw`` -- home charging, grid side, hourly mean kW
      (= kWh in that hour). On the household meter; **not** a heat gain.
    - ``ev_plugged_in`` -- fraction of the hour the car is connected at
      home (the flexibility window a smart-charging optimizer may use).
    - ``ev_at_home`` -- fraction of the hour the car is parked at home.
    - ``ev_soc`` / ``ev_stored_kwh`` -- state of charge at the end of the
      hour, as a fraction and in kWh.
    - ``ev_drive_kwh`` -- battery energy used for driving in the hour.
    - ``ev_away_charging_kwh`` -- grid-side energy charged away from home
      (``away_charging_mode``) in the hour; **not** on the household
      meter.
    """
    index = profile.index
    if not isinstance(index, pd.DatetimeIndex):
        raise TypeError("profile must have a DatetimeIndex")
    _validate_index(index)
    n_hours = len(index)
    n_days = math.ceil(n_hours / 24)
    day_start = pd.date_range(index[0], periods=n_days, freq="D")
    day_is_weekend = np.asarray(day_start.weekday >= 5)
    day_month = np.asarray(day_start.month)

    absent_by_day: np.ndarray | None = None
    if (
        config.coupling_enabled
        and num_persons is not None
        and "n_present" in profile.columns
    ):
        absent = (
            profile["n_present"].to_numpy(dtype=float) < num_persons
        ).astype(float)
        padded = np.zeros(n_days * 24)
        padded[:n_hours] = absent
        absent_by_day = padded.reshape(n_days, 24)

    plan = _draw_plan(config, n_days, day_is_weekend, absent_by_day, rng)

    sim = _Simulator(config, n_hours, day_month)
    warmup = min(config.warmup_days, n_days)
    if warmup:
        sim.run_days(plan, range(warmup))
        sim.finish(24.0 * warmup)
        # Carry the warmed-up state to t = 0.
        sim.plug_time = (
            0.0
            if sim.plug_time <= 24.0 * warmup
            else (sim.plug_time - 24.0 * warmup)
        )
        sim.home_since = 0.0
    sim.record = True
    sim._point(0.0)
    sim.run_days(plan, range(n_days))
    sim.finish(float(n_hours))

    hour_end = np.arange(1, n_hours + 1, dtype=float)
    soc = np.interp(hour_end, sim.soc_t, sim.soc_v)
    return pd.DataFrame(
        {
            "ev_charging_kw": sim.charging,
            "ev_plugged_in": np.clip(sim.plugged_frac, 0.0, 1.0),
            "ev_at_home": np.clip(sim.home_frac, 0.0, 1.0),
            "ev_soc": soc,
            "ev_stored_kwh": soc * config.battery_capacity_kwh,
            "ev_drive_kwh": sim.drive,
            "ev_away_charging_kwh": sim.away,
        },
        index=index,
    )


def no_ev_frame(index: pd.DatetimeIndex) -> pd.DataFrame:
    """:data:`EV_COLUMNS` for a household without an EV: zero energy and
    presence, ``NaN`` state of charge."""
    zeros = np.zeros(len(index))
    return pd.DataFrame(
        {
            "ev_charging_kw": zeros,
            "ev_plugged_in": zeros,
            "ev_at_home": zeros,
            "ev_soc": np.full(len(index), np.nan),
            "ev_stored_kwh": zeros,
            "ev_drive_kwh": zeros,
            "ev_away_charging_kwh": zeros,
        },
        index=index,
    )


def measured_ev_frame(
    index: pd.DatetimeIndex, charging_kw: pd.Series
) -> pd.DataFrame:
    """:data:`EV_COLUMNS` from a *measured* home-charging series (e.g. a
    survey or smart-meter sub-meter): ``ev_charging_kw`` is the measured
    series; ``ev_plugged_in`` marks hours with charging; quantities the
    measurement does not reveal (SOC, driving, away charging, time at
    home) are ``NaN``."""
    aligned = charging_kw.reindex(index)
    if aligned.isna().any():
        raise ValueError(
            "measured EV charging series does not cover the profile's "
            "index after reindexing -- pass a series aligned to it."
        )
    values = aligned.to_numpy(dtype=float)
    if (values < 0).any():
        raise ValueError("measured EV charging series must be >= 0")
    nan = np.full(len(index), np.nan)
    return pd.DataFrame(
        {
            "ev_charging_kw": values,
            "ev_plugged_in": (values > 0).astype(float),
            "ev_at_home": nan,
            "ev_soc": nan,
            "ev_stored_kwh": nan,
            "ev_drive_kwh": nan,
            "ev_away_charging_kwh": nan,
        },
        index=index,
    )


def summarize_ev(frame: pd.DataFrame, config: EVConfig) -> dict[str, float]:
    """Annual indicators for one simulated EV frame: energy by location,
    sessions, session length, equivalent full cycles by charging mode
    (the input a battery-degradation model needs). Useful for checking
    a parameter set against survey or literature values."""
    charging = frame["ev_charging_kw"].to_numpy(dtype=float)
    plugged = frame["ev_plugged_in"].to_numpy(dtype=float)
    years = len(frame) / 8760.0
    active = charging > 1e-9
    starts = int(np.count_nonzero(active & ~np.r_[False, active[:-1]]))
    connected = plugged > 0
    connections = int(
        np.count_nonzero(connected & ~np.r_[False, connected[:-1]])
    )
    home_grid = float(charging.sum())
    away_grid = float(frame["ev_away_charging_kwh"].sum())
    home_batt = home_grid * config.home_mode.efficiency
    away_batt = away_grid * config.away_mode.efficiency
    drive = float(frame["ev_drive_kwh"].sum())
    cap = config.battery_capacity_kwh
    return {
        "drive_kwh_per_year": drive / years,
        "km_per_year": drive / config.consumption_kwh_per_km / years,
        "home_charging_kwh_per_year": home_grid / years,
        "away_charging_kwh_per_year": away_grid / years,
        "home_share_of_charged_energy": (
            home_batt / (home_batt + away_batt)
            if home_batt + away_batt > 0
            else float("nan")
        ),
        "charging_blocks_per_week": starts / (years * 52.18),
        "connections_per_week": connections / (years * 52.18),
        "mean_charging_hours_per_block": (
            float(np.count_nonzero(active)) / starts if starts else 0.0
        ),
        "mean_connected_hours_per_connection": (
            float(plugged.sum()) / connections if connections else 0.0
        ),
        "peak_home_charging_kw": float(charging.max())
        if len(charging)
        else 0.0,
        "equivalent_full_cycles_home_per_year": home_batt / cap / years,
        "equivalent_full_cycles_away_per_year": away_batt / cap / years,
    }


__all__ = [
    "EV_COLUMNS",
    "ChargingMode",
    "EVConfig",
    "measured_ev_frame",
    "no_ev_frame",
    "resolve_ev_config",
    "simulate_ev",
    "summarize_ev",
]
