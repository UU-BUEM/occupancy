"""Load default numerical parameters from the configs/ directory."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

_CONFIGS_DIR = Path(__file__).parent.parent.parent / "configs"


def _read_json(filename: str) -> dict:
    with (_CONFIGS_DIR / filename).open(encoding="utf-8") as fh:
        return json.load(fh)


def _load_occupancy_probabilities() -> tuple[np.ndarray, np.ndarray]:
    data = _read_json("occupancy_probabilities.json")
    return (
        np.asarray(data["home_probabilities"], dtype=float),
        np.asarray(data["active_probabilities"], dtype=float),
    )


def _load_weightage_table() -> dict[str, dict[str, np.ndarray]]:
    data = _read_json("electricity_weightage.json")
    return {
        appliance: {
            "weekday": np.asarray(weights["weekday"], dtype=float),
            "weekend": np.asarray(weights["weekend"], dtype=float),
        }
        for appliance, weights in data.items()
        if not appliance.startswith("_")
    }


(
    HOURLY_HOME_PROBABILITIES,
    HOURLY_ACTIVE_PROBABILITIES,
) = _load_occupancy_probabilities()
WEIGHTAGE_TABLE = _load_weightage_table()
