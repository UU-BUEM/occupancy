"""Service-building type registry.

Each type is defined by two config files under ``data/<type_id>/``:
``schedule.json`` (occupancy generator + params) and ``equipment.json``
(the type's :class:`~occupancy.core.equipment.EquipmentSpec` rows). Loading
is triggered by each type's thin module (``supermarket.py``, ``office.py``,
...) calling :func:`load_building_type` — importing ``services_buildings``
loads every type in one place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from occupancy.core.equipment import EquipmentSpec, normalize_equipment_table
from occupancy.core.loader import load_json_resource

_PACKAGE = "occupancy.services_buildings"


@dataclass(frozen=True)
class ServiceBuildingTypeSpec:
    """One service-building activity type."""

    id: str
    description: str
    region: str
    capacity_default: int
    generator: str
    generator_params: dict[str, Any]
    equipment: dict[str, EquipmentSpec] = field(default_factory=dict)


SERVICE_BUILDING_TYPES: dict[str, ServiceBuildingTypeSpec] = {}


def register_building_type(spec: ServiceBuildingTypeSpec) -> None:
    """Register a new service-building type (e.g. from a future reference
    occupancy module) under ``spec.id``."""
    SERVICE_BUILDING_TYPES[spec.id] = spec


def get_building_type(name: str) -> ServiceBuildingTypeSpec:
    try:
        return SERVICE_BUILDING_TYPES[name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown service building type {name!r}. "
            f"Registered: {sorted(SERVICE_BUILDING_TYPES)}"
        ) from exc


def load_building_type(type_id: str) -> ServiceBuildingTypeSpec:
    """Load ``data/<type_id>/{schedule,equipment}.json`` and register it."""
    schedule = load_json_resource(_PACKAGE, f"data/{type_id}/schedule.json")
    equipment_data = load_json_resource(_PACKAGE, f"data/{type_id}/equipment.json")
    spec = ServiceBuildingTypeSpec(
        id=schedule["id"],
        description=schedule.get("description", ""),
        region=schedule.get("region", "NL"),
        capacity_default=int(schedule.get("capacity_default", 50)),
        generator=schedule.get("generator", "fixed_schedule"),
        generator_params=schedule.get("generator_params", {}),
        equipment=normalize_equipment_table(equipment_data),
    )
    register_building_type(spec)
    return spec
