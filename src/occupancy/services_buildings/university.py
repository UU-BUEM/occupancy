"""University / college academic building service-building type. Loads
and registers its config on import.

Distinct from :mod:`occupancy.services_buildings.school` (primary/
secondary, one whole-building timetable): teaching spaces here are
occupied per rolling class-registration schedules, so no single hour
comes close to full occupancy and evening classes push occupancy past a
school's typical close time -- a shape ``fixed_schedule``'s single open/
close window + flat peak can't represent, hence
``data/university/schedule.json`` uses the ``hourly_occupancy_curve``
generator instead (like :mod:`occupancy.services_buildings.hotel`/
:mod:`occupancy.services_buildings.hospital`), with July-August closure
still expressed via the generic ``closed_months`` param (same mechanism
as ``school``). See that JSON file's ``_comment`` for the full source
citation (Bae, Yoon, Jung, Malhotra & Im, ORNL/DOE college-building
occupancy-schedule study) and its documented simplifications.
"""

from occupancy.services_buildings.building_types import load_building_type

UNIVERSITY = load_building_type("university")
