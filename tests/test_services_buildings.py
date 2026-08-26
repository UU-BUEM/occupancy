import pytest

from occupancy.core.equipment import EquipmentSpec
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
    "hospital",
    "university",
    "glasshouse",
]
# These never set asleep_probabilities, so n_asleep stays 0 -- unlike
# hotel/hospital, which genuinely have overnight sleeping guests/patients.
_SLEEPS_OVERNIGHT = ("hotel", "hospital")
_NEVER_SLEEPS = [
    bt for bt in _ALL_BUILDING_TYPES if bt not in _SLEEPS_OVERNIGHT
]


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
        "cooking_active",
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


def test_hospital_has_genuine_sleeping_occupants_overnight() -> None:
    """Same contract as hotel -- a hospital's inpatients genuinely sleep,
    unlike the outpatient `clinic` type."""
    profile = ServiceBuildingProfile(
        building_type="hospital", year=2025, seed=1
    ).get_profile()
    assert (profile["n_asleep"] > 0).any()
    assert (
        profile["n_asleep"] <= profile["n_present"] - profile["n_active"]
    ).all()


def test_hospital_never_fully_empties() -> None:
    """Unlike the outpatient `clinic` type (closes overnight/most of the
    weekend), a 24/7 inpatient hospital's occupancy_fraction curve never
    touches 0 -- see data/hospital/schedule.json's _comment."""
    profile = ServiceBuildingProfile(
        building_type="hospital", year=2025, seed=1
    ).get_profile()
    assert (profile["n_present"] > 0).all()


def test_hospital_uses_hourly_occupancy_curve_generator() -> None:
    assert (
        SERVICE_BUILDING_TYPES["hospital"].generator
        == "hourly_occupancy_curve"
    )


def test_university_closed_on_weekends() -> None:
    """Unlike hotel/hospital (also `hourly_occupancy_curve`), a university
    academic building has no weekend occupancy at all -- expressed via an
    all-zero weekend column in occupancy_fraction (see
    core/occupancy_engine.py's guarantee that a curve cell of exactly 0.0
    stays 0.0 despite noise)."""
    profile = ServiceBuildingProfile(
        building_type="university", year=2025, seed=1
    ).get_profile()
    is_weekend = profile.index.weekday >= 5
    assert (profile.loc[is_weekend, "n_present"] == 0).all()


def test_university_closed_in_summer_holiday_months() -> None:
    profile = ServiceBuildingProfile(
        building_type="university", year=2025, seed=1
    ).get_profile()
    summer = profile.index.month.isin([7, 8])
    assert (profile.loc[summer, "n_present"] == 0).all()


def test_university_has_evening_occupancy_unlike_school() -> None:
    """The defining difference from `school`: rolling class-registration
    schedules mean university teaching spaces stay in use into the
    evening (Bae et al.'s classroom curve rises again 6-7 p.m.), while
    `school` closes at 16:00 (data/school/schedule.json)."""
    profile = ServiceBuildingProfile(
        building_type="university", year=2025, seed=1
    ).get_profile()
    non_summer_weekday = (~profile.index.month.isin([7, 8])) & (
        profile.index.weekday < 5
    )
    evening = non_summer_weekday & (profile.index.hour == 19)
    assert (profile.loc[evening, "n_present"] > 0).any()


def test_university_peak_occupancy_stays_well_under_half_capacity() -> None:
    """Bae et al.: 'fewer than 50% of the classrooms in the college
    building are occupied at the same time' -- unlike `school`, whose
    single whole-building timetable lets it approach its
    peak_occupancy_fraction (0.85)."""
    capacity = SERVICE_BUILDING_TYPES["university"].capacity_default
    profile = ServiceBuildingProfile(
        building_type="university", year=2025, seed=1
    ).get_profile()
    assert profile["n_present"].max() < 0.6 * capacity


def test_glasshouse_open_every_day_unlike_warehouse() -> None:
    """Unlike `warehouse` (hard closed_weekends), a glasshouse needs daily
    plant care -- open every day with a shorter weekend window rather
    than fully closed (data/glasshouse/schedule.json)."""
    profile = ServiceBuildingProfile(
        building_type="glasshouse", year=2025, seed=1
    ).get_profile()
    is_weekend = profile.index.weekday >= 5
    assert (profile.loc[is_weekend, "n_present"] > 0).any()


def test_glasshouse_has_no_area_normalized_gain() -> None:
    """Deliberate: no cited lighting-power-density source exists for this
    type (see the schedule.json _comment) -- gain_w_per_m2 is left None
    rather than guessed, unlike every other registered type."""
    assert SERVICE_BUILDING_TYPES["glasshouse"].gain_w_per_m2 is None
    for building_type, spec in SERVICE_BUILDING_TYPES.items():
        if building_type != "glasshouse":
            assert spec.gain_w_per_m2 is not None


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


def test_get_equipment_table_defaults_to_building_type_table() -> None:
    profile = ServiceBuildingProfile(building_type="office", year=2025, seed=1)
    assert profile.get_equipment_table() == dict(
        SERVICE_BUILDING_TYPES["office"].equipment
    )


def test_custom_equipment_table_excludes_absent_items() -> None:
    base = ServiceBuildingProfile(
        building_type="office", year=2025, seed=1
    ).get_equipment_table()
    assert len(base) > 1
    kept_name = next(iter(base))
    filtered = {kept_name: base[kept_name]}

    profile = ServiceBuildingProfile(
        building_type="office", year=2025, seed=1, equipment=filtered
    )
    assert profile.get_equipment_table() == filtered

    only_kept = ServiceBuildingProfile(
        building_type="office",
        year=2025,
        seed=1,
        equipment={kept_name: base[kept_name]},
    ).get_profile()
    full = ServiceBuildingProfile(
        building_type="office", year=2025, seed=1
    ).get_profile()
    # Excluding items can only reduce (never increase) total power draw.
    assert (
        only_kept["total_power_kwh"] <= full["total_power_kwh"] + 1e-9
    ).all()


def test_include_equipment_false_wins_over_custom_equipment() -> None:
    base = ServiceBuildingProfile(
        building_type="office", year=2025, seed=1
    ).get_equipment_table()
    profile = ServiceBuildingProfile(
        building_type="office",
        year=2025,
        seed=1,
        include_equipment=False,
        equipment=base,
    ).get_profile()
    assert "total_power_kwh" not in profile.columns


def test_empty_equipment_dict_keeps_column_present_but_zero() -> None:
    profile = ServiceBuildingProfile(
        building_type="office", year=2025, seed=1, equipment={}
    ).get_profile()
    assert "total_power_kwh" in profile.columns
    assert (profile["total_power_kwh"] == 0).all()


def test_custom_equipment_spec_contributes_expected_power() -> None:
    spec = EquipmentSpec(
        name="always_on_test_item",
        rated_power_kw=1.0,
        strategy="flat_always_on",
    )
    profile = ServiceBuildingProfile(
        building_type="office",
        year=2025,
        seed=1,
        equipment={"always_on_test_item": spec},
    ).get_profile()
    assert (profile["total_power_kwh"] == 1.0).all()


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


def test_default_seed_is_deterministic_and_varies_with_capacity() -> None:
    """Same rationale/mechanism as HouseholdProfile's matching test --
    seed=None resolves to a stable hash of the profile's own construction
    inputs, not OS entropy (buem's occupancy_gains_handoff.md "Seed
    ownership" ask)."""
    kwargs = dict(building_type="office", year=2025, capacity=20)
    first = ServiceBuildingProfile(**kwargs)
    second = ServiceBuildingProfile(**kwargs)
    assert first.seed is not None
    assert first.seed == second.seed
    assert first.get_profile().equals(second.get_profile())

    other_capacity = ServiceBuildingProfile(
        building_type="office", year=2025, capacity=40
    )
    assert other_capacity.seed != first.seed


def test_cooking_active_present_for_kitchen_equipped_building_types() -> None:
    """restaurant carries "kitchen"-category equipment -- cooking_active
    must show real activity over a full year, same convention as
    ElectricityConsumptionProfile's (buem's dhw_cooking_heat_handoff.md ask
    #2)."""
    profile = ServiceBuildingProfile(
        building_type="restaurant", year=2025, seed=1
    ).get_profile()
    assert profile["cooking_active"].dtype == bool
    assert profile["cooking_active"].any()


def test_cooking_active_false_without_kitchen_equipment() -> None:
    profile = ServiceBuildingProfile(
        building_type="warehouse", year=2025, seed=1
    ).get_profile()
    assert not profile["cooking_active"].any()


@pytest.mark.parametrize("building_type", ["hospital", "university"])
def test_cooking_active_present_for_hospital_and_university_kitchens(
    building_type: str,
) -> None:
    """hospital carries a real patient/staff-meal kitchen item (Dobosi
    et al.'s case-study hospital lists one), university a cafeteria item
    (Bae et al.'s Cafe_OCC_SCH) -- both should show real cooking_active
    activity, same convention as restaurant's."""
    profile = ServiceBuildingProfile(
        building_type=building_type, year=2025, seed=1
    ).get_profile()
    assert profile["cooking_active"].any()


def test_cooking_active_false_for_glasshouse() -> None:
    """No kitchen-category equipment in this type -- its schedule-driven
    climate/lighting/irrigation items are all "process"/"lighting"."""
    profile = ServiceBuildingProfile(
        building_type="glasshouse", year=2025, seed=1
    ).get_profile()
    assert not profile["cooking_active"].any()
