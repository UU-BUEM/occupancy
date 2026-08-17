# DHW / cooking heat-demand: questions answered

Direct answers to the four questions raised in the 2026-08-17 session,
updated after reading McKenna & Thomson (2016) in full (previously
secondary-source-only — see `docs/dhw/sources_reviewed.md` row 5) and
after clarifying scope with the user. These answers are what
`households/dhw.py`'s design (`docs/dhw/design.md`) is built on.

## 1. Does fixture ownership matter for this scope? — now resolved with real data

**Unchanged conclusion on *why* it matters.** Ownership only affects the
*magnitude* of DHW volume (whether a household has a bath materially
changes its total draw), never the internal-gains term — confirmed
directly against `model_buem.py`: `Q_ia = (Q_ig + elecLoad) * (...)` has
no DHW term of any kind (see `docs/buem_engine_reference.md`).

**Resolved this session, with real data, not a workaround.** The first
pass sidestepped per-fixture ownership entirely (scaling the whole
reference table by household size instead) because the identified source
for real ownership rates — Pullinger et al. (2013) — hadn't been
obtained. Scanning the user's own local reading-materials archive this
session turned up `CREST_Demand_Model_v2.3.3.xlsm`, McKenna & Thomson's
own runtime workbook, whose `AppliancesAndWaterFixtures` sheet carries
real, per-fixture "proportion of dwellings with appliance" figures:
basin 0.994, kitchen sink 1.0, shower 0.997, bath 0.916. `households/
dhw.py` now uses these directly — a seeded Bernoulli draw per fixture,
per household, gating whether that fixture contributes any draws at all
— replacing the household-size-scaling shortcut with the real mechanism
the source model itself uses. (Whether these particular figures trace
back to Pullinger et al. specifically isn't confirmed — the workbook's
own reference list doesn't footnote them at the per-row level — so
obtaining Pullinger et al. directly is still listed as a good
cross-check in `docs/dhw/design.md`'s open items, just no longer a
blocker.)

## 2. Can draw duration reuse the existing kitchen-equipment timing?

**Unchanged conclusion, now implemented exactly as scoped.** Timing
transfers (the `cooking_active` signal now drives kitchen-sink draw
*timing* directly in `households/dhw.py` — zero new data, reuses the
already-shipped signal); duration/volume still needed a literature source,
which DHWcalc supplies (`households/data/dhw_tapping_categories.csv`).

McKenna & Thomson's own fixture-to-activity mapping (Section 3.4: *"Basins,
showers, and baths, are assigned to the 'washing and dressing' activity,
while kitchen sinks are assigned to the 'cooking' activity"*) independently
confirms the mapping this repo already inferred before this session's
full-text read — the design wasn't guessing.

**One honest gap this full-text read surfaced, since improved**: this
repo only has `Act_Cooking` extracted from the bundled CREST 1.0e
workbook (via `crest_tpm.py`'s precedent). It has **no** extracted
`Act_WashDress` timing data — CREST's electricity-only workbook doesn't
carry it either, and the DHW-capable workbook found this session
(`CREST_Demand_Model_v2.3.3.xlsm`) ties its own washing-and-dressing
timing to a per-minute VBA switch-on mechanism not reachable without
decompiling macros. Rather than fall back to a *flat* `n_active` average
— "spread evenly across every hour someone happens to be active," which
undersells how washing-and-dressing behaviour actually clusters —
`generate_dhw_draws()` uses a **transition-weighted** envelope instead:
`n_active + |Δn_active|`, adding extra weight at the hours where active
occupancy *changes* (waking up, going to bed). This reuses a real
methodological precedent already in this repo's literature base:
Richardson et al. (2008) validate their own occupancy model against
counts of "people becoming active"/"people becoming inactive" (their
Figs. 33–34) — the same transition concept, applied here as a timing
proxy built entirely from data this repo already generates, not
fabricated. It is still a proxy, not a measured washing-and-dressing
curve — listed in `docs/dhw/design.md`'s open items as the one piece
that would most benefit from a genuinely sourced replacement — but it is
a considered, literature-grounded proxy, not the weakest available
option.

## 3. What does "flow rate" mean, and does it drive heat demand?

**Unchanged, now on firmer arithmetic footing.** Flow rate × duration =
volume; volume (with a delivery-temperature assumption, which this module
deliberately does not make — see below) is what a future energy
calculation would need. The DHWcalc table implemented in
`dhw_tapping_categories.csv` is now verified *self-consistent*:
`flow_rate_l_per_h × duration_min / 60` reproduces `volume_per_event_l`
exactly for all four rows, and `Σ(volume × events/day)` reproduces the
paper's stated 200 L/day total to within rounding — see
`tests/test_dhw.py::test_tapping_categories_table_is_self_consistent`.

**Where this energy would land, restated for this doc**: nowhere in
buem's 5R1C solve, confirmed directly against `model_buem.py` again this
session (unchanged from the prior finding) — see
`docs/buem_engine_reference.md` for the full walkthrough. This module
therefore outputs **liters only**, never kWh — the delivery-temperature
assumption a kWh conversion needs belongs on buem's side of the ownership
boundary (temperature/ΔT/energy math), the same line CLAUDE.md already
draws for every other occupancy/buem handoff.

## 4. Review of buem's model (`model_buem.py`) — and the reverse

Moved to its own document: `docs/buem_engine_reference.md`. That doc now
also does the *reverse* of what buem's own `.claude/occupancy_module_
activities.md` does for occupancy — it documents buem's engine (the 5R1C
solve, the required-keys contract, where a future DHW term would and
wouldn't plug in) from occupancy's side, so anyone working on this
package's DHW/cooking output has a single place to check what the
downstream consumer actually does with it, without re-deriving it from
buem's source each time.

## 5. The user's cooking clarification — confirmed, no change needed

The user clarified mid-session: "cooking" (for the purposes of
direct-heat/gas-relevant activity, distinct from the internal-gains
contribution *every* appliance makes) should exclude dishwasher and
washing machine even though a dishwasher physically sits in the kitchen.

Checked directly against `households/data/equipment.json`: `dish_washer`,
`washing_machine`, `tumble_dryer`, and `washer_dryer` are all filed under
`"category": "laundry"`. Only `hob`, `oven`, `microwave`, `kettle`, and
`small_cooking_group` carry `"category": "kitchen"`. `cooking_active`
(shipped earlier this session, see `CHANGELOG.md`) sums exactly the
`"kitchen"` category — **dishwasher and washing machine were never
included**, matching the user's definition exactly, with no code change
needed. `docs/dhw/design.md`'s `generate_dhw_draws()` write-up reuses this
same, already-correct `cooking_active` signal for kitchen-sink DHW timing.
