import pytest

from occupancy.services_buildings import SERVICE_BUILDING_TYPES, ServiceBuildingProfile


def test_all_expected_building_types_registered() -> None:
    assert {
        "supermarket",
        "office",
        "restaurant",
        "school",
    } <= SERVICE_BUILDING_TYPES.keys()


@pytest.mark.parametrize(
    "building_type", ["supermarket", "office", "restaurant", "school"]
)
def test_building_type_generates_valid_profile(building_type: str) -> None:
    profile = ServiceBuildingProfile(
        building_type=building_type, year=2025, seed=1
    ).get_profile()

    assert len(profile) in (8760, 8784)
    assert list(profile.columns) == [
        "n_present",
        "n_active",
        "activity",
        "total_power_kwh",
    ]
    assert (profile["n_active"] <= profile["n_present"]).all()
    assert (profile["total_power_kwh"] >= 0).all()


def test_capacity_defaults_from_building_type() -> None:
    profile = ServiceBuildingProfile(
        building_type="office", year=2025, seed=1
    ).get_profile()
    assert (
        profile["n_present"] <= SERVICE_BUILDING_TYPES["office"].capacity_default
    ).all()


def test_office_is_closed_on_weekends() -> None:
    profile = ServiceBuildingProfile(
        building_type="office", year=2025, seed=1
    ).get_profile()
    is_weekend = profile.index.weekday >= 5
    assert (profile.loc[is_weekend, "n_present"] == 0).all()


def test_school_closed_in_summer_holiday_months() -> None:
    profile = ServiceBuildingProfile(
        building_type="school", year=2025, seed=1
    ).get_profile()
    summer = profile.index.month.isin([7, 8])
    assert (profile.loc[summer, "n_present"] == 0).all()


def test_unknown_building_type_raises() -> None:
    with pytest.raises(ValueError, match="Unknown service building type"):
        ServiceBuildingProfile(building_type="does_not_exist", year=2025)


def test_include_equipment_false_omits_power_column() -> None:
    profile = ServiceBuildingProfile(
        building_type="supermarket", year=2025, seed=1, include_equipment=False
    ).get_profile()
    assert "total_power_kwh" not in profile.columns
