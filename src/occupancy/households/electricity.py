from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from occupancy.core.equipment import (
    EquipmentSpec,
    generate_equipment_power,
    normalize_equipment_table,
)
from occupancy.core.loader import load_json_resource
from occupancy.households.archetypes import get_archetype
from occupancy.households.household_profile import HouseholdProfile

_PACKAGE = "occupancy.households"
_EQUIPMENT_PATH = "data/equipment.json"

_BASE_EQUIPMENT: dict[str, EquipmentSpec] = normalize_equipment_table(
    load_json_resource(_PACKAGE, _EQUIPMENT_PATH)
)

# One flag can gate several individual equipment items (e.g. "fridge" covers
# every cold-appliance type CREST distinguishes). Every item in
# households/data/equipment.json must appear in exactly one list here.
_LEGACY_FLAG_TO_EQUIPMENT: dict[str, list[str]] = {
    "has_fridge": [
        "chest_freezer",
        "fridge_freezer",
        "refrigerator",
        "upright_freezer",
    ],
    "has_cooking": ["hob", "oven", "microwave", "kettle", "small_cooking_group"],
    "has_laundry": ["dish_washer", "tumble_dryer", "washing_machine", "washer_dryer"],
    "has_cleaning": ["vacuum"],
    "has_ironing": ["iron"],
    "has_tv": ["tv_1", "tv_2", "tv_3", "vcr_dvd", "tv_receiver_box"],
    "has_lighting": ["lighting"],
    "has_other": [
        "answer_machine",
        "cassette_cd_player",
        "clock",
        "cordless_telephone",
        "hi_fi",
        "fax",
        "personal_computer",
        "printer",
    ],
}

# Draws ownership using a seed offset from the main RNG's seed so ownership
# outcomes don't perturb the equipment-trigger draw sequence (and vice versa).
_OWNERSHIP_SEED_OFFSET = 1_000_000


def default_equipment_table() -> dict[str, EquipmentSpec]:
    """A fresh copy of the default household equipment specs."""
    return dict(_BASE_EQUIPMENT)


def _apply_overrides(
    base: dict[str, EquipmentSpec],
    overrides: dict[str, dict[str, np.ndarray]],
) -> dict[str, EquipmentSpec]:
    if not overrides:
        return base
    result = dict(base)
    for name, override in overrides.items():
        spec = result.get(name)
        if spec is None:
            continue
        result[name] = replace(
            spec,
            weekday=spec.weekday * override["weekday"],
            weekend=spec.weekend * override["weekend"],
        )
    return result


@dataclass
class ElectricityConsumptionProfile:
    """Hourly household electricity demand derived from occupancy states.

    Iterates a config-driven list of :class:`~occupancy.core.equipment.EquipmentSpec`
    (loaded from ``households/data/equipment.json``, with any per-archetype
    ``equipment_overrides`` applied) instead of one bespoke method per
    appliance. The ``has_*`` flags are kept as a compatibility shim for
    enabling/disabling whole equipment categories by name. Items with
    ``ownership_probability < 1.0`` are additionally subject to a one-time,
    seeded Bernoulli "does this household own one of these" draw -- so e.g.
    two otherwise-identical households won't both have a dishwasher just
    because ``has_laundry`` is on.
    """

    occupancy_profile: HouseholdProfile
    equipment: dict[str, EquipmentSpec] | None = None
    has_cooking: bool = True
    has_tv: bool = True
    has_laundry: bool = True
    has_cleaning: bool = True
    has_ironing: bool = True
    has_fridge: bool = True
    has_other: bool = True
    has_lighting: bool = True
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.seed is None:
            self.seed = self.occupancy_profile.seed
        self._rng = np.random.default_rng(self.seed)
        self._profile: pd.DataFrame | None = None

        if self.equipment is None:
            archetype = get_archetype(self.occupancy_profile.archetype)
            self.equipment = _apply_overrides(
                default_equipment_table(), archetype.equipment_overrides
            )

    def get_equipment_table(self) -> dict[str, EquipmentSpec]:
        assert self.equipment is not None
        return self.equipment

    def _enabled_by_name(self) -> dict[str, bool]:
        flags = {
            "has_cooking": self.has_cooking,
            "has_tv": self.has_tv,
            "has_laundry": self.has_laundry,
            "has_cleaning": self.has_cleaning,
            "has_ironing": self.has_ironing,
            "has_fridge": self.has_fridge,
            "has_other": self.has_other,
            "has_lighting": self.has_lighting,
        }
        return {
            equipment_name: flags[flag_name]
            for flag_name, equipment_names in _LEGACY_FLAG_TO_EQUIPMENT.items()
            for equipment_name in equipment_names
        }

    def _owned_by_name(self) -> dict[str, bool]:
        assert self.equipment is not None
        ownership_seed = (
            None if self.seed is None else self.seed + _OWNERSHIP_SEED_OFFSET
        )
        ownership_rng = np.random.default_rng(ownership_seed)
        owned: dict[str, bool] = {}
        for name in sorted(self.equipment):
            probability = self.equipment[name].ownership_probability
            owned[name] = probability >= 1.0 or bool(
                ownership_rng.random() < probability
            )
        return owned

    def generate(self) -> pd.DataFrame:
        occ_profile = self.occupancy_profile.get_profile().copy()
        assert self.equipment is not None

        enabled = self._enabled_by_name()
        owned = self._owned_by_name()
        specs = [
            spec
            if enabled.get(name, spec.enabled) and owned.get(name, True)
            else replace(spec, enabled=False)
            for name, spec in self.equipment.items()
        ]

        occ_profile["total_power_kwh"] = generate_equipment_power(
            specs, occ_profile, self._rng
        )
        self._profile = occ_profile
        return occ_profile

    def get_profile(self) -> pd.DataFrame:
        if self._profile is None:
            return self.generate()
        return self._profile
