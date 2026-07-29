import pytest

from occupancy.services_buildings import (
    SERVICE_BUILDING_TYPES,
    ServiceBuildingProfile,
)

_ALL_BUILDING_TYPES = [
    "supermarket",
    "office",
    "restaurant",
    "school",
    "hotel",
    "bakery",
    "warehouse",
    "clinic",
]
# These never set asleep_probabilities, so n_asleep stays 0 -- unlike
# hotel, which genuinely has overnight sleeping guests.
_NEVER_SLEEPS = [bt for bt in _ALL_BUILDING_TYPES if bt != "hotel"]


def test_all_expected_building_types_registered() -> None:
    assert set(_ALL_BUILDING_TYPES) <= SERVICE_BUILDING_TYPES.keys()


@pytest.mark.parametrize("building_type", _ALL_BUILDING_TYPES)
def test_building_type_generates_valid_profile(building_type: str) -> None:
    profile = ServiceBuildingProfile(
        building_type=building_type, year=2025, seed=1
    ).get_profile()

    assert len(profile) in (8760, 8784)
    assert list(profile.columns) == [
        "n_present",
        "n_active",
        "n_asleep",
        "activity",
        "total_power_kwh",
    ]
    assert (profile["n_active"] <= profile["n_present"]).all()
    assert (profile["total_power_kwh"] >= 0).all()


@pytest.mark.parametrize("building_type", _NEVER_SLEEPS)
def test_non_hotel_building_types_never_have_sleeping_occupants(
    building_type: str,
) -> None:
    profile = ServiceBuildingProfile(
        building_type=building_type, year=2025, seed=1
    ).get_profile()
    assert (profile["n_asleep"] == 0).all()


def test_hotel_has_genuine_sleeping_occupants_overnight() -> None:
    profile = ServiceBuildingProfile(
        building_type="hotel", year=2025, seed=1
    ).get_profile()
    assert (profile["n_asleep"] > 0).any()
    assert (
        profile["n_asleep"] <= profile["n_present"] - profile["n_active"]
    ).all()
    # unlike office/school, a hotel never fully empties out
    assert (profile["n_present"] > 0).all()


def test_hotel_uses_hourly_occupancy_curve_generator() -> None:
    assert (
        SERVICE_BUILDING_TYPES["hotel"].generator == "hourly_occupancy_curve"
    )


def test_warehouse_is_closed_on_weekends() -> None:
    profile = ServiceBuildingProfile(
        building_type="warehouse", year=2025, seed=1
    ).get_profile()
    is_weekend = profile.index.weekday >= 5
    assert (profile.loc[is_weekend, "n_present"] == 0).all()


def test_clinic_weekend_window_is_shorter_than_weekday() -> None:
    profile = ServiceBuildingProfile(
        building_type="clinic", year=2025, seed=1
    ).get_profile()
    is_saturday = profile.index.weekday == 5
    # weekend window is 8-13 vs weekday 7-19 -- 14:00 must be empty on
    # Saturday but is a normal open hour on weekdays
    saturday_afternoon = is_saturday & (profile.index.hour == 14)
    assert (profile.loc[saturday_afternoon, "n_present"] == 0).all()


def test_capacity_defaults_from_building_type() -> None:
    profile = ServiceBuildingProfile(
        building_type="office", year=2025, seed=1
    ).get_profile()
    assert (
        profile["n_present"]
        <= SERVICE_BUILDING_TYPES["office"].capacity_default
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


@pytest.mark.parametrize("building_type", _ALL_BUILDING_TYPES)
def test_building_types_have_heat_gain_and_to_result_carries_it(
    building_type: str,
) -> None:
    spec = SERVICE_BUILDING_TYPES[building_type]
    assert spec.heat_gain_present_kw > 0
    assert spec.heat_gain_active_kw > spec.heat_gain_present_kw

    result = ServiceBuildingProfile(
        building_type=building_type, year=2025, seed=1
    ).to_result()
    assert result.heat_gain_present_kw == spec.heat_gain_present_kw
    assert result.heat_gain_active_kw == spec.heat_gain_active_kw
