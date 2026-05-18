"""Occupancy modeling package for UU-BUEM."""

from occupancy.electricity.electricity_consumption import (
    ElectricityConsumptionProfile,
)
from occupancy.internal_gains.occupancy_profile import (
    OccupancyProfile,
    OccupancyResult,
)

try:
    from occupancy._version import __version__
except ImportError:
    __version__ = "1.1.0"

__all__ = [
    "OccupancyProfile",
    "OccupancyResult",
    "ElectricityConsumptionProfile",
    "__version__",
]
