"""Household occupancy + electricity modeling.

Base linking module: importing this package loads every archetype JSON
under ``data/archetypes/`` into :data:`HOUSEHOLD_ARCHETYPES`.
"""

from occupancy.households.archetypes import (
    HOUSEHOLD_ARCHETYPES,
    ArchetypeSpec,
    get_archetype,
    register_archetype,
)
from occupancy.households.electricity import (
    ElectricityConsumptionProfile,
    default_equipment_table,
)
from occupancy.households.household_profile import HouseholdProfile

__all__ = [
    "HOUSEHOLD_ARCHETYPES",
    "ArchetypeSpec",
    "ElectricityConsumptionProfile",
    "HouseholdProfile",
    "default_equipment_table",
    "get_archetype",
    "register_archetype",
]
