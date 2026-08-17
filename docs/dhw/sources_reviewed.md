# DHW / cooking heat-demand: literature sources reviewed

Every source consulted while researching buem's `dhw_cooking_heat_handoff.md`
ask, across both research passes (2026-08-17), with **access status** and
**exactly what was extracted and used** in this repo. Written for direct
reuse in a citation list — nothing here is asserted without a paper trail;
where a number could not be independently verified this session, that is
stated explicitly rather than left ambiguous.

See `docs/dhw/design.md` for how these sources map onto
`households/dhw.py` / `households/data/dhw_tapping_categories.csv`, and
`docs/dhw/questions_answered.md` for the direct answers these sources
support.

## Primary sources read in full this session

| # | Citation | Access | What was extracted / how it's used here |
|---|---|---|---|
| 1 | Richardson, I., Thomson, M., Infield, D. (2008). "A high-resolution domestic building occupancy model for energy demand simulations." *Energy and Buildings* 40(8), 1560–1566. `doi:10.1016/j.enbuild.2008.02.006` | Read in full (PDF supplied by user) | The original CREST occupancy model: first-order Markov chain over UK 2000 Time-Use Survey (TUS) diary data, 144 ten-minute transition-probability matrices per household size (1–6) × weekday/weekend. This is the method `core/occupancy_engine.py`'s `markov_chain` generator and `households/crest_tpm.py`'s hourly-composed TPM extraction both implement/extend. No DHW content — occupancy-only, predates CREST's thermal/DHW extension by 8 years. |
| 2 | Richardson, I., Thomson, M., Infield, D., Delahunty, A. (2009). "Domestic lighting: A high-resolution energy demand model." *Energy and Buildings* 41(7), 781–789. `doi:10.1016/j.enbuild.2009.02.010` | Read in full | Two-factor (active occupancy × natural irradiance) stochastic switch-on model per lighting unit; "effective occupancy" sharing curve (from US EIA data); Stokes et al.'s on-duration distribution. Conceptual precedent for this repo's own `lighting` equipment item (a single aggregate estimate, not a bulb-by-bulb model — see `equipment.json`'s own comment). No DHW content. |
| 3 | Richardson, I., Thomson, M., Infield, D., Clifford, C. (2010). "Domestic electricity use: A high-resolution energy demand model." *Energy and Buildings* 42(10), 1878–1887. `doi:10.1016/j.enbuild.2010.05.023` | Read in full | The full 33-appliance electricity model: appliance→activity-profile mapping, TUS-code-derived daily activity probabilities, per-appliance "calibration scalars." **Directly confirms two things used in this session's design**: (a) the "cooking" activity profile is built from TUS codes 3100–3190 (food management/preparation/baking/**dish washing**/preserving/other) — Section 2.1; (b) Section 6.3.5 explicitly states *"the electric hob, oven, microwave **and dish-washer** are all assigned to the cooking activity profile"* for appliance-switch-on **timing** correlation purposes. This is a genuinely different claim from "dishwasher is a cooking/direct-heat appliance" — CREST ties dishwasher timing to cooking because people often run it around mealtimes, not because it is a heat/gas-generating cooking process. This repo's own `equipment.json` already reflects the narrower distinction the user asked for: `dish_washer` (and `washing_machine`/`tumble_dryer`/`washer_dryer`) are filed under category `"laundry"`, separate from `hob`/`oven`/`microwave`/`kettle`/`small_cooking_group`'s `"kitchen"` category — confirmed by direct inspection this session, see `docs/dhw/questions_answered.md` §5. Also explicitly states water heating and electric space heating are **excluded** from CREST's electricity model as thermal loads — the same exclusion this repo's `equipment.json` already documents, now textually confirmed at the source. |
| 4 | Richardson, I. (2010). *Integrated High-resolution Modelling of Domestic Electricity Demand and Low Voltage Electricity Distribution Networks*. PhD thesis, Loughborough University. CC BY-NC-ND. | Read in full (contains papers #1–3 as appendices, plus the LV-network integration work) | No DHW content. Section 11.8 "Potential for further work" explicitly lists *"Inclusion of a thermal model of dwellings in the demand model"* as unstarted future work at time of writing — direct confirmation that DHW/thermal modelling postdates this 2010 body of work and only appears with McKenna & Thomson's 2016 extension (#5 below). Useful only for citation completeness / provenance chain, not for any DHW numbers. |
| 5 | McKenna, E., Thomson, M. (2016). "High-resolution stochastic integrated thermal–electrical domestic demand model." *Applied Energy* 165, 445–461. `doi:10.1016/j.apenergy.2015.12.089` | **Read in full this session** (previously secondary-source-only) | **New this session** — see `docs/dhw/questions_answered.md` for the full extraction. In short: Section 3.4 describes the real hot-water module (stochastic fixture assignment, activity-linked timing, calibrated stochastic volume-per-event); Section 3.5.2 gives a constant 10 °C cold-mains assumption and cylinder sizing; Section 5.2 gives a real UK validation anchor (122.4 L/day/dwelling, EST measured data, vs. the model's own 117.5 L/day/dwelling output); Section 5.4 gives a DHW simultaneity factor of 0.13 at 30 dwellings, cross-checked against an independent model (Baetens & Saelens' StROBe, also 0.13). The exact per-fixture flow-rate/duration/volume numeric tables are **not** published in the paper's main text — they live in the three sources below, none obtained this session. |
| 6 | Jordan, U., Vajen, K. (2005). "DHWcalc: Program to Generate Domestic Hot Water Profiles with Statistical Means for User Defined Conditions." *Proc. ISES Solar World Congress*, Orlando. | Read in full (prior session; free, direct PDF from University of Kassel's own repository) | The real numeric tapping-category table (small/medium/shower/bath: flow rate, duration, volume/event, events/day, portion of daily total) for a 200 L/day single-family-house IEA SHC Task 26 reference case. **Implemented directly** as `households/data/dhw_tapping_categories.csv` — see `docs/dhw/design.md`. |
| 7 | Home Energy Model (HEM), UK government's SAP successor. Technical guide: `home-energy-model.co.uk/technical/hot-water/` | Read in full (prior session; free, current) | Independent (non-CREST, non-DHWcalc) UK cross-check figures: legacy SAP flat bath volume = 73 L; generic tap draw-off default 12 L/min. Not wired into the current implementation (no HEM-based category exists yet) — kept as a validation reference only. |

## Local archive scan (2026-08-18) — the workbook above, found and used

Per the user's direction to scan their own local reading-materials
archive before asking for documents that might already be on hand, the
folder `C:\Users\sahoo002\OneDrive - Universiteit Utrecht\Old computer\
Reading materials\Journal papers\past_work\occupancy\` was listed
(filenames only, cheap) before opening anything, specifically to avoid
burning effort re-requesting sources already sitting there. It contains:

| File | Relevance | Action taken |
|---|---|---|
| `CREST_Demand_Model_v2.3.3.xlsm` | **The DHW-capable CREST workbook** — has `WaterUsage` and `AppliancesAndWaterFixtures` sheets the electricity-only `CREST_Domestic_electricity_demand_model_1.0e.xlsm` this repo already bundles does not. | **Opened and inspected directly** (via `openpyxl`, read-only) — this is the source of the real ownership/flow-rate/duration/volume-distribution numbers now in `dhw_tapping_categories.csv`; see the row below and `docs/dhw/design.md`. |
| `CREST_Demand_Model_v2.2.xlsm` | An older version of the same model. | Not opened — v2.3.3 (above) already gave what was needed. |
| `Pullinger-et-al.-2013_Patterns-of-Water_...pdf` | The exact Pullinger et al. (2013) paper previously listed below as "not accessed." | **Read in full this session** (see the reference-list update below) — a large practice-theory survey report; its own text does not carry a simple per-fixture ownership-percentage table in the form McKenna & Thomson's workbook does, so the workbook (not this paper) remains the operative source for the ownership numbers now in the CSV. |
| `STP09-DHW01_Analysis_of_EST_DHW_data.pdf` | Likely EST (2008)-adjacent DHW consumption analysis. | Not opened this pass — flagged as next-highest-value if the EST figure ever needs primary-source confirmation. |
| `Boait et al. (2012)`, `synPRO_Paper.pdf`, `1-s2.0-S2210422424000935-main.pdf` | Comparison/context papers (DHW production efficiency; a German synPRO load-profile model; an unidentified 2024 Elsevier paper). | Not opened this pass — not needed for the current implementation; noted here so they aren't re-discovered from scratch later. |
| `preview_NTA 8800_2025 nl.pdf` | A Dutch-language NTA 8800:2025 preview document. | Not opened this pass (out of the current scope's critical path — see "Keeping this generic" in `docs/dhw/design.md` for why NTA 8800 was deliberately not made load-bearing this round); flagged for the user if the Dutch-specific cross-check becomes wanted later. |

**What the CREST workbook gave, in full** (see `docs/dhw/design.md` for
the complete derivation): `AppliancesAndWaterFixtures` rows 46–53 —
per-fixture ownership probability, mean flow rate (L/min), mean cycle
duration (min), and an aggregate household hot-water total
(119.62586974793265 L/day) for its own example dwelling, whose
`Dwellings` sheet states `Number of residents = 1`. `WaterUsage`'s own
header cites, verbatim: *"Data estimated from Clarke, A., Grant, N.,
Thornton, J., 2009 Quantifying the energy and carbon effects of water
saving: Final Report for the Environment Agency and Energy Saving
Trust"* — confirming Clarke et al. (2009), not Pullinger et al. (2013),
as the workbook's own cited source for this data, at least at the sheet
level (the workbook's own numbered reference list does not footnote each
row individually, so this is the most specific attribution the source
material itself provides).

## Sources identified previously, still not obtained

| Citation | What it would give us | Status |
|---|---|---|
| Clarke, A., Grant, N., Thornton, J. (2009). "Quantifying the energy and carbon effects of water saving: Final Report for the Environment Agency and Energy Saving Trust." Elemental Solutions, London. | The primary-source version of the per-fixture ownership/volume numbers now used via the CREST workbook's own citation of it (see above) — would let this repo confirm those figures independently of McKenna & Thomson's model. | **Not accessed** — not found in the scanned local archive; the CREST workbook's own citation of it is the closest available source this session. |
| Energy Saving Trust (2008). "Measurement of domestic hot water consumption in dwellings." | The primary source behind the 122.4 L/day/dwelling UK figure quoted (secondhand, via McKenna & Thomson) in row 5 above — would let this repo verify the figure directly instead of through McKenna's citation of it. | **Not accessed** — only the summary figure inside McKenna & Thomson's own text was usable; `STP09-DHW01_Analysis_of_EST_DHW_data.pdf` (found locally, not yet opened) may be adjacent to this and worth checking first before asking the user for anything new. |
| McKenna, E., Thomson, M. (2015). "High-resolution integrated thermal–electrical domestic demand model (Software download)." Loughborough University. `doi:10.17028/rd.lboro.2001129` | Possibly a newer/different release of the workbook now in use, or documentation clarifying the per-fixture daily-volume split this session had to approximate via a DHWcalc-share apportionment (`docs/dhw/design.md`). | **Not accessed as a separate download** — `CREST_Demand_Model_v2.3.3.xlsm`, found locally, already serves this purpose; chasing the 2015 release specifically is now lower-priority than before. |

## NTA 8800 — checked again this session, still not resolved

Two pages the user supplied were checked directly this session:

- `gebouwenergieprestatie.nl/bepalingsmethode/` — the official Dutch
  "Bepalingsmethode" (determination-method) implementation-guidance
  portal for NTA 8800. Confirmed as a legitimate, citable pointer to the
  *official* Dutch government NTA 8800 tooling/guidance ecosystem, but the
  page itself does not publish DHW default figures — it links onward to
  the paid standard purchase page (`nen.nl/nta-8800-2025-c1-2026-nl-349740`).
- `zenronline.eu/.../new-nta-8800-assessment-guidelines...` — a
  third-party news/overview article. Also does not publish DHW numbers;
  suggests contacting NEN directly (`bi@nen.nl`, +31 15 269 0324) for
  substantive technical questions.

**Net result**: the 40.3 L/person/day / 545 kWh/person/year figure carried
in buem's `dhw_cooking_heat_handoff.md` (predating this session) remains
**not independently re-verified against primary NTA 8800 text**, across two
sessions and four distinct access attempts (the base standard, its
Interpretatiedocument, and now these two pointer pages). The base
NTA 8800:2019-06 (and successor 2025+C1:2026) standard is a paid NEN
publication with no free full-text mirror found. If NTA 8800 needs to be
cited with confidence in a journal paper, either purchase the standard from
NEN, or find a secondary academic source that quotes the figure directly
(several Dutch building-energy papers likely do — not searched this
session; flagged as a next step if wanted, see the "asks for the user" note
at the end of `docs/dhw/design.md`).
