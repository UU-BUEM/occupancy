"""Electric-vehicle sub-model: occupancy.core.ev + its household wiring."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

import occupancy
from occupancy import (
    EV_COLUMNS,
    ElectricityConsumptionProfile,
    HouseholdProfile,
    MultiDwellingProfile,
    load_ev_config,
    subtract_ev_load,
    to_buem_profiles,
)
from occupancy.core.ev import no_ev_frame, simulate_ev, summarize_ev


def _household(seed: int = 7, persons: int = 2) -> HouseholdProfile:
    return HouseholdProfile(
        num_persons=persons, year=2025, archetype="generic", seed=seed
    )


@pytest.fixture(scope="module")
def ev_profile() -> ElectricityConsumptionProfile:
    profile = ElectricityConsumptionProfile(_household())
    profile.get_profile()
    return profile


# -- ownership / has_ev ---------------------------------------------------


def test_individual_household_defaults_to_having_an_ev(ev_profile) -> None:
    assert ev_profile.has_ev is True
    assert ev_profile.ev_owned
    profile = ev_profile.get_profile()
    assert set(EV_COLUMNS) <= set(profile.columns)
    assert profile["ev_charging_kw"].sum() > 0


def test_has_ev_false_gives_zero_ev_columns() -> None:
    profile = ElectricityConsumptionProfile(
        _household(), has_ev=False
    ).get_profile()
    assert (profile["ev_charging_kw"] == 0).all()
    assert profile["ev_soc"].isna().all()
    assert (
        profile["total_power_incl_ev_kwh"] == profile["total_power_kwh"]
    ).all()


def test_ev_never_enters_total_power_or_elec_load(ev_profile) -> None:
    """The bug this sub-model fixes: EV charging used to sit inside
    total_power_kwh, i.e. buem's elecLoad -- an internal heat gain."""
    with_ev = ev_profile.get_profile()
    without_ev = ElectricityConsumptionProfile(
        _household(), has_ev=False
    ).get_profile()
    pd.testing.assert_series_equal(
        with_ev["total_power_kwh"], without_ev["total_power_kwh"]
    )
    np.testing.assert_allclose(
        with_ev["total_power_incl_ev_kwh"],
        with_ev["total_power_kwh"] + with_ev["ev_charging_kw"],
    )
    buem = to_buem_profiles(ev_profile.to_result())
    pd.testing.assert_series_equal(
        buem["elecLoad"],
        with_ev["total_power_kwh"].rename("elecLoad"),
    )
    assert buem["ev_charging_kw"].sum() == pytest.approx(
        with_ev["ev_charging_kw"].sum()
    )


def test_unknown_ownership_draws_from_probability() -> None:
    owned = [
        ElectricityConsumptionProfile(_household(seed=s), has_ev=None).ev_owned
        for s in range(400)
    ]
    assert 0.14 < np.mean(owned) < 0.26  # bundled default 0.20

    always = ElectricityConsumptionProfile(
        _household(), has_ev=None, ev_config={"ownership_probability": 1.0}
    )
    never = ElectricityConsumptionProfile(
        _household(), has_ev=None, ev_config={"ownership_probability": 0.0}
    )
    assert always.ev_owned and not never.ev_owned


def test_ownership_draw_does_not_change_trips() -> None:
    """Separate random streams: whether the EV is drawn as owned must not
    alter the trip simulation of an owned EV."""
    forced = ElectricityConsumptionProfile(_household(), has_ev=True)
    drawn = ElectricityConsumptionProfile(
        _household(), has_ev=None, ev_config={"ownership_probability": 1.0}
    )
    pd.testing.assert_series_equal(
        forced.get_profile()["ev_charging_kw"],
        drawn.get_profile()["ev_charging_kw"],
    )


# -- physics / constraints -------------------------------------------------


def test_soc_and_power_respect_constraints(ev_profile) -> None:
    cfg = ev_profile.get_ev_config()
    profile = ev_profile.get_profile()
    soc = profile["ev_soc"]
    assert soc.min() >= cfg.soc_min - 1e-9
    assert soc.max() <= cfg.soc_target_home + 1e-9
    assert profile["ev_charging_kw"].max() <= (
        cfg.effective_power_kw(cfg.home_mode) + 1e-9
    )
    # Charging only while plugged in, plugged in only while at home.
    charging = profile["ev_charging_kw"] > 0
    assert (profile.loc[charging, "ev_plugged_in"] > 0).all()
    assert (profile["ev_plugged_in"] <= profile["ev_at_home"] + 1e-9).all()
    np.testing.assert_allclose(
        profile["ev_stored_kwh"], soc * cfg.battery_capacity_kwh
    )


def test_energy_balance_closes(ev_profile) -> None:
    """Battery-side energy in (home + away charging, net of losses) equals
    energy out (driving) plus the change in stored energy."""
    cfg = ev_profile.get_ev_config()
    p = ev_profile.get_profile()
    charged = (
        p["ev_charging_kw"].sum() * cfg.home_mode.efficiency
        + p["ev_away_charging_kwh"].sum() * cfg.away_mode.efficiency
    )
    driven = p["ev_drive_kwh"].sum()
    start = (
        p["ev_stored_kwh"].iloc[0]
        + p["ev_drive_kwh"].iloc[0]
        - p["ev_charging_kw"].iloc[0] * cfg.home_mode.efficiency
        - p["ev_away_charging_kwh"].iloc[0] * cfg.away_mode.efficiency
    )
    delta = p["ev_stored_kwh"].iloc[-1] - start
    assert charged - driven == pytest.approx(delta, abs=0.5)


def test_annual_indicators_are_plausible(ev_profile) -> None:
    """Calibration targets: CBS 14.8k km/yr private EV; RVO Nationaal
    Laadonderzoek 2025 ~81% of energy charged at home."""
    s = ev_profile.ev_summary()
    assert 9_000 < s["km_per_year"] < 20_000
    assert 1_500 < s["home_charging_kwh_per_year"] < 3_500
    assert 0.65 < s["home_share_of_charged_energy"] < 0.97
    assert 1.0 < s["charging_blocks_per_week"] < 6.0


def test_faster_charger_shortens_sessions_same_energy() -> None:
    """Charging time follows energy / power; the energy need does not
    depend on the charger."""
    slow = ElectricityConsumptionProfile(_household())
    fast = ElectricityConsumptionProfile(
        _household(),
        ev_config={"charging_modes": {"slow": {"power_kw": 11.0}}},
    )
    s_slow, s_fast = slow.ev_summary(), fast.ev_summary()
    assert s_fast["peak_home_charging_kw"] == pytest.approx(11.0)
    assert (
        s_fast["mean_charging_hours_per_block"]
        < s_slow["mean_charging_hours_per_block"]
    )
    assert s_fast["drive_kwh_per_year"] == pytest.approx(
        s_slow["drive_kwh_per_year"]
    )


def test_vehicle_onboard_limit_caps_charger() -> None:
    cfg = load_ev_config({"charging_modes": {"slow": {"power_kw": 22.0}}})
    assert cfg.effective_power_kw(cfg.home_mode) == 11.0  # car AC limit


def test_home_fast_charging_mode_selectable() -> None:
    profile = ElectricityConsumptionProfile(
        _household(), ev_config={"home_charging_mode": "fast"}
    ).get_profile()
    assert profile["ev_charging_kw"].max() > 11.0


def test_no_home_charger_moves_all_charging_away() -> None:
    p = ElectricityConsumptionProfile(
        _household(), ev_config={"has_home_charger": False}
    ).get_profile()
    assert p["ev_charging_kw"].sum() == 0
    assert p["ev_plugged_in"].sum() == 0
    assert p["ev_away_charging_kwh"].sum() > 0


def test_car_is_away_mostly_when_someone_is_out() -> None:
    """Presence coupling: the car's trips line up with occupant absence,
    well above the household's baseline absence rate. Uses an archetype
    with a persistent (Markov) presence generator -- with independent
    hourly draws (``generic``) absences are scattered and there is little
    to couple to."""
    hh = HouseholdProfile(
        num_persons=2, year=2025, archetype="working_couple", seed=7
    )
    p = ElectricityConsumptionProfile(hh).get_profile()
    away = p["ev_at_home"] < 1e-9
    someone_out = p["n_present"] < hh.num_persons
    assert away.sum() > 0
    assert someone_out[away].mean() > someone_out.mean() + 0.2

    uncoupled = ElectricityConsumptionProfile(
        hh,
        ev_config={"mobility": {"presence_coupling": {"enabled": False}}},
    ).get_profile()
    away_uncoupled = uncoupled["ev_at_home"] < 1e-9
    assert someone_out[away].mean() > someone_out[away_uncoupled].mean()


def test_reproducible_with_same_seed() -> None:
    a = ElectricityConsumptionProfile(_household(seed=3)).get_profile()
    b = ElectricityConsumptionProfile(_household(seed=3)).get_profile()
    pd.testing.assert_frame_equal(a, b)


# -- configuration ----------------------------------------------------------


def test_unknown_override_key_raises() -> None:
    with pytest.raises(ValueError, match="Unknown EV config key"):
        load_ev_config({"vehicle": {"battery_kwh": 70}})


def test_invalid_values_raise() -> None:
    with pytest.raises(ValueError):
        load_ev_config({"battery": {"soc_min": 0.95}})
    with pytest.raises(ValueError, match="positive definite"):
        load_ev_config(
            {
                "mobility": {
                    "copula_correlation": [
                        [1, 0.99, -0.99],
                        [0.99, 1, 0.99],
                        [-0.99, 0.99, 1],
                    ]
                }
            }
        )
    with pytest.raises(ValueError):
        load_ev_config({"home_charging_mode": "turbo"})


def test_survey_overrides_from_json_file(tmp_path) -> None:
    """Survey-derived distributions slot in as a JSON overrides file; raw
    counts are fine (weights are normalized)."""
    arrivals = [0] * 24
    arrivals[17] = 30
    arrivals[18] = 70
    path = tmp_path / "survey.json"
    path.write_text(
        json.dumps(
            {
                "mobility": {
                    "arrival_hour_weights": {
                        "weekday": arrivals,
                        "weekend": arrivals,
                    },
                    "presence_coupling": {"enabled": False},
                }
            }
        )
    )
    p = ElectricityConsumptionProfile(
        _household(), ev_config=path
    ).get_profile()
    arrival_hours = p.index.hour[
        (p["ev_at_home"].diff() > 0) & (p["ev_at_home"].shift() < 1e-9)
    ]
    assert set(arrival_hours) <= {17, 18, 19}


def test_measured_charging_series_replaces_simulation() -> None:
    hh = _household()
    index = hh.get_profile().index
    measured = pd.Series(0.0, index=index)
    measured.iloc[20:23] = 3.7
    p = ElectricityConsumptionProfile(
        hh, has_ev=False, ev_charging_kw=measured
    ).get_profile()
    np.testing.assert_allclose(p["ev_charging_kw"], measured)
    assert p["ev_soc"].isna().all()


# -- downstream helpers -------------------------------------------------------


def test_subtract_ev_load_recovers_appliance_load(ev_profile) -> None:
    p = ev_profile.get_profile()
    remainder = subtract_ev_load(
        p["total_power_incl_ev_kwh"], p["ev_charging_kw"]
    )
    np.testing.assert_allclose(remainder, p["total_power_kwh"], atol=1e-9)
    with pytest.raises(ValueError, match="exceeds the total"):
        subtract_ev_load(p["total_power_kwh"] * 0, p["ev_charging_kw"])


def test_multi_dwelling_sums_evs() -> None:
    building = MultiDwellingProfile(
        dwellings=10,
        mean_num_persons=2.0,
        year=2025,
        seed=11,
        ev_config={"ownership_probability": 0.5},
    )
    p = building.get_profile()
    assert building.has_ev is None
    assert building.n_ev is not None and 0 < building.n_ev <= 10
    assert p["ev_plugged_in"].max() <= building.n_ev + 1e-9
    assert "ev_soc" not in p.columns
    np.testing.assert_allclose(
        p["total_power_incl_ev_kwh"],
        p["total_power_kwh"] + p["ev_charging_kw"],
    )


def test_simulate_ev_rejects_non_hourly_index() -> None:
    index = pd.date_range("2025-01-01", periods=96, freq="30min")
    frame = pd.DataFrame({"n_present": 1}, index=index)
    with pytest.raises(ValueError, match="hourly"):
        simulate_ev(
            frame,
            num_persons=1,
            config=load_ev_config(),
            rng=np.random.default_rng(0),
        )


def test_summary_of_no_ev_is_empty() -> None:
    assert (
        ElectricityConsumptionProfile(_household(), has_ev=False).ev_summary()
        == {}
    )
    index = pd.date_range("2025-01-01", periods=48, freq="h")
    summary = summarize_ev(no_ev_frame(index).fillna(0.0), load_ev_config())
    assert summary["home_charging_kwh_per_year"] == 0


def test_top_level_exports() -> None:
    names = ("EVConfig", "EV_COLUMNS", "load_ev_config", "subtract_ev_load")
    for name in names:
        assert hasattr(occupancy, name)


def test_cholesky_is_blas_free_and_correct() -> None:
    """core.ev factors the copula matrix in plain Python (no numpy.linalg,
    no BLAS-backed matmul): a broken BLAS install aborts the interpreter
    instead of raising, which made `import occupancy` crash outright."""
    import inspect

    from occupancy.core import ev

    corr = np.array([[1.0, 0.3, -0.37], [0.3, 1.0, 0.2], [-0.37, 0.2, 1.0]])
    lower = np.array(ev._cholesky(corr))
    rebuilt = sum(
        np.outer(lower[:, k], lower[:, k]) for k in range(3)
    )  # L L^T without matmul
    np.testing.assert_allclose(rebuilt, corr, atol=1e-12)
    source = inspect.getsource(ev)
    assert "np.linalg" not in source
    assert " @ " not in source


# -- plug-in model and charging timer (Harbrecht et al. 2018) -------------


def test_logistic_plug_in_probability_matches_formula() -> None:
    cfg = load_ev_config({"plug_in": {"model": "logistic"}})
    assert cfg.plug_in_probability(0.5) == pytest.approx(0.5)
    assert cfg.plug_in_probability(0.2) > 0.97
    assert cfg.plug_in_probability(0.9) < 0.01
    # The default stays the calibrated step table.
    assert load_ev_config().plug_in_probability(0.2) == 1.0


def test_logistic_plug_in_gives_plausible_charging_frequency() -> None:
    """Harbrecht et al. (2018) report 0.42 charging events per vehicle-day
    for this parameter set with ~22 kWh cars (MINI E trial: 0.40). With the
    default 60 kWh battery the same thresholds are reached less often
    (~0.2 per day), so only a plausible range is checked."""
    s = ElectricityConsumptionProfile(
        _household(), ev_config={"plug_in": {"model": "logistic"}}
    ).ev_summary()
    per_day = s["connections_per_week"] / 7.0
    assert 0.1 < per_day < 0.7
    assert s["home_share_of_charged_energy"] > 0.6


def test_charging_timer_moves_charging_to_the_night() -> None:
    base = ElectricityConsumptionProfile(_household()).get_profile()
    timed = ElectricityConsumptionProfile(
        _household(), ev_config={"home_charging_start_hour": 23}
    ).get_profile()
    hour = timed.index.hour
    daytime = (hour >= 9) & (hour < 23)
    assert timed.loc[daytime, "ev_charging_kw"].sum() < 0.02 * (
        timed["ev_charging_kw"].sum()
    )
    assert base.loc[daytime, "ev_charging_kw"].sum() > 0.3 * (
        base["ev_charging_kw"].sum()
    )
    # Connection (flexibility window) still starts at plug-in.
    assert timed.loc[daytime, "ev_plugged_in"].sum() > 0
    assert timed["ev_charging_kw"].sum() == pytest.approx(
        base["ev_charging_kw"].sum(), rel=0.15
    )


@pytest.mark.parametrize(
    "override",
    [
        {"plug_in": {"model": "linear"}},
        {"plug_in": {"logistic": {"sensitivity_soc": 0.0}}},
        {"home_charging_start_hour": 24},
    ],
)
def test_invalid_plug_model_or_timer_raises(override) -> None:
    with pytest.raises(ValueError):
        load_ev_config(override)
