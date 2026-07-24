import numpy as np
import pandas as pd

from occupancy.core.equipment import (
    EquipmentContext,
    EquipmentSpec,
    flat_always_on,
    linear_in_occupants,
    probabilistic_event,
    sessions_per_week,
)
from occupancy.core.occupancy_engine import (
    OccupancyGenerationContext,
    binomial_independent,
    fixed_schedule,
    markov_chain,
)


def _index(hours: int = 72) -> pd.DatetimeIndex:
    return pd.date_range("2026-01-01", periods=hours, freq="h")


def test_binomial_independent_matches_manual_reimplementation() -> None:
    """Regression guard: the extracted strategy function must reproduce the
    exact same draw sequence as a straightforward reimplementation of the
    original per-row algorithm, under the same seed."""
    index = _index(24 * 3)
    home_probabilities = np.full((24, 2), 0.6)
    active_probabilities = np.full((24, 2), 0.4)
    size = 3

    rng_a = np.random.default_rng(123)
    ctx = OccupancyGenerationContext(
        size=size,
        index=index,
        rng=rng_a,
        home_probabilities=home_probabilities,
        active_probabilities=active_probabilities,
    )
    actual = binomial_independent(ctx)

    rng_b = np.random.default_rng(123)
    expected_present = []
    expected_active = []
    for ts in index:
        weekend_index = 1 if ts.weekday() >= 5 else 0
        p_home = home_probabilities[ts.hour][weekend_index]
        p_active = active_probabilities[ts.hour][weekend_index]
        present = int(rng_b.binomial(size, p_home))
        active = int(rng_b.binomial(present, p_active)) if present else 0
        expected_present.append(present)
        expected_active.append(active)

    assert list(actual["n_present"]) == expected_present
    assert list(actual["n_active"]) == expected_active
    assert (actual["n_active"] <= actual["n_present"]).all()


def test_markov_chain_produces_valid_states_and_persists() -> None:
    index = _index(24 * 7)
    size = 4
    home_probabilities = np.full((24, 2), 0.7)
    active_probabilities = np.full((24, 2), 0.5)

    ctx = OccupancyGenerationContext(
        size=size,
        index=index,
        rng=np.random.default_rng(1),
        home_probabilities=home_probabilities,
        active_probabilities=active_probabilities,
        params={"persistence": 0.95},
    )
    frame = markov_chain(ctx)

    assert (frame["n_active"] >= 0).all()
    assert (frame["n_active"] <= size).all()
    assert (frame["n_present"] >= frame["n_active"]).all()
    assert (frame["n_present"] <= size).all()

    # High persistence -> state should change on a minority of timesteps.
    changes = (frame["n_active"].diff().fillna(0) != 0).mean()
    assert changes < 0.5


def test_fixed_schedule_respects_hours_weekends_and_closed_months() -> None:
    index = _index(24 * 40)  # spans into February
    ctx = OccupancyGenerationContext(
        size=10,
        index=index,
        rng=np.random.default_rng(2),
        params={
            "open_hour": 9,
            "close_hour": 17,
            "closed_weekends": True,
            "closed_months": [1],
            "noise": 0.0,
        },
    )
    frame = fixed_schedule(ctx)

    is_weekend = index.weekday >= 5
    is_january = index.month == 1
    closed = is_weekend | is_january
    assert (frame.loc[closed, "n_present"] == 0).all()

    outside_hours = (index.hour < 9) | (index.hour >= 17)
    assert (frame.loc[outside_hours, "n_present"] == 0).all()


def _equipment_context(profile: pd.DataFrame) -> EquipmentContext:
    return EquipmentContext(
        profile=profile,
        rng=np.random.default_rng(0),
        hours=profile.index.hour.to_numpy(),
        is_weekend=profile.index.weekday >= 5,
        weekday_index=profile.index.weekday.to_numpy(),
    )


def _profile(n_present: list[int], n_active: list[int]) -> pd.DataFrame:
    index = _index(len(n_present))
    return pd.DataFrame({"n_present": n_present, "n_active": n_active}, index=index)


def test_flat_always_on_is_constant() -> None:
    spec = EquipmentSpec(name="fridge", rated_power_kw=0.04, strategy="flat_always_on")
    profile = _profile([0, 1, 2], [0, 0, 1])
    power = flat_always_on(spec, _equipment_context(profile))
    assert (power == 0.04).all()


def test_linear_in_occupants_scales_with_presence_and_weekend_multiplier() -> None:
    spec = EquipmentSpec(
        name="other",
        rated_power_kw=0.05,
        strategy="linear_in_occupants",
        strategy_params={"weekend_multiplier": 1.2},
    )
    n_present = [2, 3, 0]
    profile = _profile(n_present, [0, 0, 0])
    power = linear_in_occupants(spec, _equipment_context(profile))
    is_weekend = profile.index.weekday >= 5
    expected = np.array(n_present, dtype=float) * 0.05
    expected = np.where(is_weekend, expected * 1.2, expected)
    np.testing.assert_allclose(power, expected)


def test_sessions_per_week_fires_expected_number_of_times() -> None:
    spec = EquipmentSpec(
        name="ironing",
        rated_power_kw=1.0,
        strategy="sessions_per_week",
        strategy_params={"sessions_per_week": 1},
    )
    n = 24 * 7 * 2  # two weeks
    profile = _profile([1] * n, [1] * n)
    power = sessions_per_week(spec, _equipment_context(profile))
    n_sessions = int((power > 0).sum())
    assert n_sessions == 2


def test_probabilistic_event_zero_outside_gate() -> None:
    spec = EquipmentSpec(
        name="cooking",
        rated_power_kw=1.5,
        weekday=np.full(24, 1.0),
        weekend=np.full(24, 1.0),
        strategy="probabilistic_event",
        strategy_params={"gate": "active", "intercept": 1.0},
    )
    profile = _profile([1, 1, 0], [0, 1, 0])
    power = probabilistic_event(spec, _equipment_context(profile))
    assert power[0] == 0.0  # present but inactive -> gated out
    assert power[2] == 0.0  # not present -> gated out
