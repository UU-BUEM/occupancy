from occupancy.electricity import ElectricityConsumptionProfile
from occupancy.internal_gains import OccupancyProfile


def test_occupancy_profile_shape_and_columns() -> None:
    profile = OccupancyProfile(num_persons=3, year=2024, seed=1).get_profile()

    assert len(profile) in (8784, 8760)
    assert list(profile.columns) == ["n_home", "n_active", "activity"]
    assert (profile["n_active"] <= profile["n_home"]).all()


def test_electricity_profile_has_total_power() -> None:
    occupancy = OccupancyProfile(num_persons=2, year=2025, seed=42)
    profile = ElectricityConsumptionProfile(
        occupancy_profile=occupancy,
        seed=42,
    ).get_profile()

    assert "total_power_kwh" in profile.columns
    assert (profile["total_power_kwh"] >= 0).all()
