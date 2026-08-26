"""Horticultural glasshouse / greenhouse service-building type. Loads and
registers its config on import.

Unlike every other type in this package, no ASHRAE/DOE/ISO/SIA/REHVA
source in this repo's usual reference set covers a glasshouse -- its
``data/glasshouse/schedule.json``/``equipment.json`` are general
domain-knowledge illustrative defaults, flagged explicitly as such in
those files' ``_comment``. Modeled as sparse, staff-driven occupancy
(``fixed_schedule``, like :mod:`occupancy.services_buildings.warehouse`)
on top of schedule- rather than occupancy-driven climate-control/
grow-lighting/irrigation equipment (``strategy_params.gate: "none"`` --
see ``core/equipment.py``), since a greenhouse's dominant loads run on
the plants' needs, not on whether a person is present.
"""

from occupancy.services_buildings.building_types import load_building_type

GLASSHOUSE = load_building_type("glasshouse")
