import pytest

import occupancy
from occupancy.households import (
    HOUSEHOLD_ARCHETYPES,
    ElectricityConsumptionProfile,
    HouseholdProfile,
    get_archetype,
)


def test_generic_archetype_shape_and_columns() -> None:
    profile = HouseholdProfile(num_persons=3, year=2024, seed=1).get_profile()

    assert len(profile) in (8784, 8760)
    assert list(profile.columns) == ["n_present", "n_active", "activity"]
    assert (profile["n_active"] <= profile["n_present"]).all()


def test_all_archetypes_are_registered_and_generate() -> None:
    expected = {
        "generic",
        "working_couple",
        "family_with_children",
        "retired_single",
        "student_shared",
    }
    assert expected <= HOUSEHOLD_ARCHETYPES.keys()

    for name, spec in HOUSEHOLD_ARCHETYPES.items():
        profile = HouseholdProfile(
            num_persons=spec.num_persons_default,
            year=2025,
            archetype=name,
            seed=1,
        ).get_profile()
        assert (profile["n_active"] <= profile["n_present"]).all()
        assert (profile["n_present"] <= spec.num_persons_default).all()


def test_unknown_archetype_raises() -> None:
    with pytest.raises(ValueError, match="Unknown household archetype"):
        HouseholdProfile(num_persons=2, year=2025, archetype="does_not_exist")


def test_working_couple_uses_markov_chain_generator() -> None:
    assert get_archetype("working_couple").generator == "markov_chain"


def test_electricity_profile_has_total_power() -> None:
    household = HouseholdProfile(num_persons=2, year=2025, seed=42)
    profile = ElectricityConsumptionProfile(
        occupancy_profile=household,
        seed=42,
    ).get_profile()

    assert "total_power_kwh" in profile.columns
    assert (profile["total_power_kwh"] >= 0).all()


def test_equipment_table_is_config_driven_and_complete() -> None:
    """Regression guard for the CREST-informed equipment expansion: every
    appliance -- including the ones that used to be hardcoded (fridge,
    ironing, other) -- is now a config-driven EquipmentSpec, none silently
    dropped."""
    household = HouseholdProfile(num_persons=2, year=2025, seed=1)
    equipment = ElectricityConsumptionProfile(
        occupancy_profile=household
    ).get_equipment_table()

    # One representative item per has_* category, plus the new lighting item.
    for name in (
        "fridge_freezer",  # has_fridge
        "iron",  # has_ironing
        "personal_computer",  # has_other
        "lighting",  # has_lighting
    ):
        assert name in equipment
        assert equipment[name].rated_power_kw > 0
        assert 0.0 < equipment[name].ownership_probability <= 1.0


def test_has_flags_disable_down_to_cold_appliances_only() -> None:
    household = HouseholdProfile(num_persons=2, year=2025, seed=5)
    electricity = ElectricityConsumptionProfile(
        occupancy_profile=household,
        seed=5,
        has_tv=False,
        has_cooking=False,
        has_laundry=False,
        has_cleaning=False,
        has_ironing=False,
        has_other=False,
        has_lighting=False,
    )
    profile = electricity.get_profile()

    # Only cold appliances (has_fridge, default True) remain -- each is
    # flat_always_on, so the total must be constant across every hour and
    # bounded by the sum of every cold appliance's rated power (ownership is
    # stochastic per household, so we can't assert an exact figure).
    cold_items = ["chest_freezer", "fridge_freezer", "refrigerator", "upright_freezer"]
    equipment = electricity.get_equipment_table()
    max_possible = sum(equipment[name].rated_power_kw for name in cold_items)

    assert profile["total_power_kwh"].nunique() == 1
    total = profile["total_power_kwh"].iloc[0]
    assert 0.0 <= total <= max_possible + 1e-9

    # Same seed -> same ownership draw -> same result, deterministically.
    repeat = ElectricityConsumptionProfile(
        occupancy_profile=HouseholdProfile(num_persons=2, year=2025, seed=5),
        seed=5,
        has_tv=False,
        has_cooking=False,
        has_laundry=False,
        has_cleaning=False,
        has_ironing=False,
        has_other=False,
        has_lighting=False,
    ).get_profile()
    assert repeat["total_power_kwh"].iloc[0] == total


def test_family_with_children_equipment_overrides_applied() -> None:
    household = HouseholdProfile(
        num_persons=4, year=2025, archetype="family_with_children", seed=1
    )
    base = ElectricityConsumptionProfile(
        occupancy_profile=HouseholdProfile(num_persons=4, year=2025, seed=1)
    ).get_equipment_table()
    overridden = ElectricityConsumptionProfile(
        occupancy_profile=household
    ).get_equipment_table()

    assert (
        overridden["washing_machine"].weekday > base["washing_machine"].weekday
    ).all()
    assert (overridden["hob"].weekday > base["hob"].weekday).all()


def test_top_level_backward_compat_aliases() -> None:
    assert occupancy.OccupancyProfile is HouseholdProfile
    profile = occupancy.OccupancyProfile(num_persons=2, year=2025, seed=1).get_profile()
    assert "n_present" in profile.columns
