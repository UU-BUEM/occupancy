# Resolved issues & settled decisions — service buildings

Do not re-raise. "BY-DESIGN" are deliberate choices.

## BY-DESIGN
- Service-building occupancy uses `fixed_schedule` (deterministic open/
  close hours + noise) by default, not the residential-style
  `binomial_independent`/`markov_chain` strategies — those model presence
  probability per person, which doesn't fit shift/opening-hours-driven
  building occupancy.
- Households and service buildings share one engine
  (`core/occupancy_engine.py` generator registry, `core/equipment.py`
  equipment registry) rather than parallel implementations — service
  buildings are just another config-driven consumer, not special-cased.
