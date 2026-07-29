"""Occupancy modeling package for UU-BUEM: households and service buildings."""

from occupancy.core.buem_adapter import to_buem_profiles
from occupancy.core.result import OccupancyResult
from occupancy.households import (
    ElectricityConsumptionProfile,
    HouseholdProfile,
)
from occupancy.services_buildings import ServiceBuildingProfile

# Back-compat alias: the pre-restructuring public API exposed a single
# generic `OccupancyProfile`. `HouseholdProfile` is its direct successor.
OccupancyProfile = HouseholdProfile

try:
    from occupancy._version import __version__
except ImportError:
    __version__ = "unknown"

__all__ = [
    "ElectricityConsumptionProfile",
    "HouseholdProfile",
    "OccupancyProfile",
    "OccupancyResult",
    "ServiceBuildingProfile",
    "__version__",
    "to_buem_profiles",
]
