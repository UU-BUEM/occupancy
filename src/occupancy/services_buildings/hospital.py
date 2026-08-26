"""24/7 inpatient hospital service-building type. Loads and registers its
config on import.

Distinct from :mod:`occupancy.services_buildings.clinic` (outpatient,
closes overnight): a hospital never has a single open/close window, so
``data/hospital/schedule.json`` uses the ``hourly_occupancy_curve``
generator (like :mod:`occupancy.services_buildings.hotel`) rather than
``fixed_schedule``, and sets real ``asleep_probabilities`` so inpatients
genuinely sleep overnight (see ``core/occupancy_engine.py``'s module
docstring). See that JSON file's ``_comment`` for full source citations
(Ahmed, Akhondzada, Kurnitski & Olesen 2017; Dobosi et al. 2019).
"""

from occupancy.services_buildings.building_types import load_building_type

HOSPITAL = load_building_type("hospital")
