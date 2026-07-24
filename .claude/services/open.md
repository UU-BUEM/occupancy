# Open issues / TODOs — service buildings

## >>> NEXT MAJOR TASKS <<<
- [config] **Service-building capacity from scenario config file** — CLI
  `--persons`/config `num_persons` only overrides a service building's
  capacity when passed as an explicit `--persons` CLI flag; a scenario
  JSON's `num_persons` is ignored for `building_type != household` (to
  avoid the household-oriented default of 3 silently clobbering e.g. a
  supermarket's `capacity_default: 80`). Needs a dedicated `capacity`
  config field with its own resolution rule.
- [services_buildings] **More building types** — only supermarket, office,
  restaurant, school exist. Adding one is a config addition
  (`data/<type>/{schedule.json,equipment.json}` + a thin registration
  module) — see `CLAUDE.md` extension points.
