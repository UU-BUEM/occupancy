from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pandas as pd


@dataclass
class OccupancyResult:
    """Typed output contract shared by household and service-building profiles."""

    profile: pd.DataFrame
    year: int
    num_persons: int
    building_type: str = "household"
    region: str = "NL"
    generated_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())
