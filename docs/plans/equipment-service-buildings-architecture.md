# Superseded

This document's proposal (a flat `equipment/`/`activities/` layer) was
superseded during implementation once the household-diversity and
service-building requirements were made concrete with the user, plus a
review of six reference occupancy models (pyCREST, richardsonpy, tsorb,
StROBe, simpy, mesa).

What was actually built — `core/`, `households/`, `services_buildings/`,
the generator/equipment strategy registries, the Markov-chain generator,
and the household archetypes — is implemented in the codebase. See:

- `README.md` — overview, repository layout, buem integration.
- `CONTRIBUTING.md` — scope (what occupancy owns vs. buem), extension
  points, dev commands.
- `CHANGELOG.md` — breaking changes and additions, release by release.
