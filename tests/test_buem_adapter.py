from dataclasses import replace

import numpy as np
import pytest

from occupancy.core.buem_adapter import to_buem_profiles
from occupancy.households import (
    ElectricityConsumptionProfile,
    HouseholdProfile,
)
from occupancy.services_buildings import ServiceBuildingProfile

_EXPECTED_KEYS = {"Q_ig", "elecLoad", "occ_nothome", "occ_sleeping"}


def test_service_building_result_converts_directly() -> None:
    result = ServiceBuildingProfile(
        building_type="office", year=2025, seed=1
    ).to_result()
    buem_profiles = to_buem_profiles(result)

    assert set(buem_profiles) == _EXPECTED_KEYS
    for series in buem_profiles.values():
        assert len(series) == len(result.profile)
        assert series.index.equals(result.profile.index)

    assert (buem_profiles["Q_ig"] >= 0).all()
    assert (buem_profiles["elecLoad"] >= 0).all()
    assert (buem_profiles["occ_nothome"] >= 0).all()
    assert (buem_profiles["occ_nothome"] <= 1).all()
    # office never sets asleep_probabilities -- unlike hotel (see
    # test_hotel_result_produces_genuine_occ_sleeping below), so no
    # sleeping occupants here regardless of hour
    assert (buem_profiles["occ_sleeping"] == 0).all()


def test_hotel_result_produces_genuine_occ_sleeping() -> None:
    """A service-building type CAN sleep -- occ_sleeping must reflect real
    n_asleep output for any building_type, not just households."""
    result = ServiceBuildingProfile(
        building_type="hotel", year=2025, seed=1
    ).to_result()
    buem_profiles = to_buem_profiles(result)

    assert (buem_profiles["occ_sleeping"] > 0).any()
    expected_sleeping = result.profile["n_asleep"] / result.num_persons
    np.testing.assert_allclose(
        buem_profiles["occ_sleeping"].to_numpy(), expected_sleeping.to_numpy()
    )


def test_household_result_needs_equipment_wrapper() -> None:
    bare = HouseholdProfile(num_persons=3, year=2025, seed=1).to_result()
    with pytest.raises(ValueError, match="total_power_kwh"):
        to_buem_profiles(bare)

    household = HouseholdProfile(num_persons=3, year=2025, seed=1)
    with_equipment = ElectricityConsumptionProfile(
        occupancy_profile=household, seed=1
    ).to_result()
    buem_profiles = to_buem_profiles(with_equipment)

    assert set(buem_profiles) == _EXPECTED_KEYS
    # occ_sleeping is real generator output (n_asleep / num_persons), not a
    # heuristic, whenever the profile carries an n_asleep column.
    expected_sleeping = (
        with_equipment.profile["n_asleep"] / with_equipment.num_persons
    )
    np.testing.assert_allclose(
        buem_profiles["occ_sleeping"].to_numpy(), expected_sleeping.to_numpy()
    )
    assert (buem_profiles["occ_sleeping"] >= 0).all()
    assert (buem_profiles["occ_sleeping"] <= 1).all()


def test_sleep_window_only_applies_as_fallback_without_n_asleep_column() -> (
    None
):
    household = HouseholdProfile(num_persons=2, year=2025, seed=2)
    result = ElectricityConsumptionProfile(
        occupancy_profile=household, seed=2
    ).to_result()

    # n_asleep present -> real model output used, sleep_window is ignored.
    with_column = to_buem_profiles(result, sleep_window=None)
    default_window = to_buem_profiles(result)
    np.testing.assert_allclose(
        with_column["occ_sleeping"].to_numpy(),
        default_window["occ_sleeping"].to_numpy(),
    )

    # Simulate an older/hand-built profile lacking n_asleep -> heuristic
    # fallback kicks in, and sleep_window now actually controls the output.
    legacy_profile = result.profile.drop(columns=["n_asleep"])
    legacy_result = replace(result, profile=legacy_profile)

    heuristic_on = to_buem_profiles(legacy_result)
    hours = legacy_profile.index.hour
    is_night = (hours >= 23) | (hours < 7)
    assert (heuristic_on["occ_sleeping"][~is_night] == 0).all()

    heuristic_off = to_buem_profiles(legacy_result, sleep_window=None)
    assert (heuristic_off["occ_sleeping"] == 0).all()


def test_heat_gain_scales_with_active_vs_inactive_occupants() -> None:
    result = ServiceBuildingProfile(
        building_type="supermarket", year=2025, seed=3
    ).to_result()
    buem_profiles = to_buem_profiles(result)

    n_present = result.profile["n_present"].to_numpy(dtype=float)
    n_active = result.profile["n_active"].to_numpy(dtype=float)
    expected_q_ig = (
        n_present - n_active
    ) * result.heat_gain_present_kw + n_active * result.heat_gain_active_kw
    np.testing.assert_allclose(buem_profiles["Q_ig"].to_numpy(), expected_q_ig)


def test_explicit_gain_kwargs_override_per_type_value() -> None:
    result = ServiceBuildingProfile(
        building_type="supermarket", year=2025, seed=3
    ).to_result()
    buem_profiles = to_buem_profiles(
        result, gain_present_kw=0.5, gain_active_kw=0.5
    )

    n_present = result.profile["n_present"].to_numpy(dtype=float)
    np.testing.assert_allclose(
        buem_profiles["Q_ig"].to_numpy(), n_present * 0.5
    )


def test_rejects_zero_num_persons() -> None:
    household = HouseholdProfile(num_persons=1, year=2025, seed=1)
    result = ElectricityConsumptionProfile(
        occupancy_profile=household, seed=1
    ).to_result()
    result.num_persons = 0
    with pytest.raises(ValueError, match="num_persons"):
        to_buem_profiles(result)
