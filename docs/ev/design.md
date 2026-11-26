# Electric vehicles: design, sources and module boundary

This document describes how occupancy models a household electric vehicle
(EV): what is simulated, where every number comes from, how to replace
the defaults with survey data, and which parts belong in other UU-BUEM
modules (conversion-technologies, the Calliope scenario layer).

Code: `src/occupancy/core/ev.py` (engine), `src/occupancy/households/ev.py`
(defaults loader), `src/occupancy/households/data/ev.json` (parameters).

## 1. Why the EV is a separate sub-model

Until 6.1.x the EV was an `equipment.json` row (`ev_charger`, strategy
`overnight_charging_session`): with probability 0.6 per day, a fixed
4-hour block at 7.4 kW starting between 18:00 and 06:00. That had four
problems:

| Problem | Consequence |
| --- | --- |
| EV power was inside `total_power_kwh`, which `to_buem_profiles()` passes to buem as `elecLoad`, an **internal heat gain** | A 7.4 kW charger heated the modelled living space |
| No battery, trips or state of charge | Charging was unrelated to how far the car was driven; energy was fixed at 7.4 x 4 x 0.6 x 365 ≈ 6,500 kWh/yr, ~2.8x the realistic ~2,300 kWh/yr (section 4) |
| Not linked to occupancy | The car could be "charging at home" while the household was away, and away while everyone was home |
| No expected-value strategy | `estimate_equipment_usage()` warned and skipped it, so EV-inclusive meter data could not be fitted |

An EV is a stateful battery, not an hourly-triggered appliance, so it now
has its own simulation and its own output columns. Its home charging is
on the household meter but is never an internal heat gain.

## 2. The model

Per calendar day, over the occupancy profile's hourly index:

1. **Is the car used?** Bernoulli, `use_probability` weekday/weekend.
2. **Trip draw.** Departure time, arrival time and daily distance are
   drawn jointly through a Gaussian copula: correlated standard normals
   mapped through each variable's marginal. This follows Lojowska et al.
   (2012), who modelled Dutch EV load from (departure, arrival, distance)
   with a normal copula. Marginals: empirical hourly weights for the two
   times, and a lognormal for distance whose scale is derived from
   `annual_km`, so the expected annual mileage matches it. A trip shorter
   than `min_trip_hours` is redrawn.
3. **Presence coupling.** Up to `max_draws` candidate trips are drawn.
   The first one whose window has someone out of the house
   (`n_present < num_persons`) for at least `min_absent_fraction` of its
   hours is accepted; otherwise the best-scoring one is kept. If nobody is
   ever out, the car stays home that day. This ties the car's absence to
   the people's. Its strength depends on the occupancy generator: with
   persistent (Markov) generators such as `working_couple`, the car is
   away during absence ~71% of the time against a 41% baseline. With
   `generic`'s independent hourly draws, absences are scattered and the
   effect is small.
4. **Driving.** Energy = km x `consumption_kwh_per_km` x the month's
   multiplier, spread over the away window.
5. **Charging away from home** (`away_charging_mode`, fast by default):
   - With `probability_per_trip_day`, part of the trip energy is
     recharged away from home (workplace, public), up to
     `soc_target_away`.
   - Any trip that would cross `soc_min` gets a forced top-up.
   - This energy is reported in `ev_away_charging_kwh` and never reaches
     the household meter.
6. **Plug-in decision** on arrival, with a probability that falls with
   arrival SOC (`plug_in.probability` by `soc_bin_upper_edges`).
   - The delay is 0 with `immediate_probability`, else uniform between
     `delay_min_hours` and `delay_max_hours` (Brady & O'Mahony 2016,
     Fig. 7).
   - On a day the car stays home unplugged, the decision is retaken at
     `evening_check_hour`.
7. **Home charging** runs from plug-in until `soc_target_home` or
   departure.
   - Power = `min(charger power_kw, car on-board limit)`
     (`max_ac_power_kw` / `max_dc_power_kw`).
   - Battery energy = grid energy x `efficiency`.
   - Above `taper_start_soc`, power falls linearly to
     `taper_end_fraction` at 100%, approximating constant-current/
     constant-voltage charging.
   - Sub-hourly timing is resolved exactly and binned into hours.
8. **State carries over.** The SOC persists across days: a large battery
   with short trips charges every few days, not daily. This frequency is
   emergent, not a fixed rate. A `warmup_days` burn-in removes the
   dependence on `soc_initial`, the same reason Brady & O'Mahony simulate
   two days and keep the second.

### Output columns

| Column | Meaning | On household meter? | Internal heat gain? |
| --- | --- | --- | --- |
| `ev_charging_kw` | Home charging, grid side, hourly mean kW (= kWh/h) | yes | **no** |
| `ev_plugged_in` | Fraction of the hour connected at home (the smart-charging window) | - | - |
| `ev_at_home` | Fraction of the hour parked at home | - | - |
| `ev_soc`, `ev_stored_kwh` | State of charge at the end of the hour | - | - |
| `ev_drive_kwh` | Battery energy used for driving | - | - |
| `ev_away_charging_kwh` | Grid-side energy charged away from home | no | no |
| `total_power_incl_ev_kwh` | `total_power_kwh` + `ev_charging_kw` (meter level) | yes | partly |

`total_power_kwh` (buem's `elecLoad`) is unchanged in meaning: appliances
and lighting only. `to_buem_profiles()` additionally returns
`ev_charging_kw` as a separate series, for passing on to an energy-system
model.

### API

```python
from occupancy import ElectricityConsumptionProfile, HouseholdProfile, MultiDwellingProfile

hh = HouseholdProfile(num_persons=2, year=2025, archetype="working_couple")

# Individual household: has an EV by default.
elec = ElectricityConsumptionProfile(hh)                      # has_ev=True
elec.get_profile()[["total_power_kwh", "ev_charging_kw", "ev_soc"]]
elec.ev_summary()      # annual km, kWh home/away, sessions, cycles, ...

# 11 kW wallbox instead of 7.4 kW: sessions get shorter, energy unchanged.
ElectricityConsumptionProfile(hh, ev_config={"charging_modes": {"slow": {"power_kw": 11.0}}})

# Community analysis: ownership unknown, drawn with probability 0.20 (Loenen default).
ElectricityConsumptionProfile(hh, has_ev=None)
ElectricityConsumptionProfile(hh, has_ev=None, ev_config={"ownership_probability": 0.35})
MultiDwellingProfile(dwellings=12, mean_num_persons=2.2, year=2025)   # has_ev=None by default
```

CLI: `--ev/--no-ev`, `--ev-ownership-probability P` (implies unknown
ownership), `--ev-charger-kw KW`, `--ev-config overrides.json`. A
scenario JSON takes an `"ev": {"has_ev": true|false|null, "overrides":
{...}}` section.

## 3. Parameters and sources

All values are in `households/data/ev.json`, each with a `_source` note.

| Parameter | Default | Source |
| --- | --- | --- |
| `ownership_probability` | 0.20 | User-specified for Loenen (above the national average). National reference: ~6% of NL private passenger cars are plug-in (CBS 2025), a share of cars, not households |
| Home charger `power_kw` | 7.4 | User-specified default (single-phase 32 A wallbox) |
| Charging `efficiency` | 0.92 slow / 0.93 fast | 95% inverter x 97% battery, Brady & O'Mahony 2016 (after Keane & Flynn 2012); fast is estimated |
| Fast charger `power_kw` | 50 (DC) | Estimated: a common public DC rating |
| Taper (CC-CV) | slow from 95% SOC; fast from 80% to 20% of power | Estimated |
| `battery_capacity_kwh` | 60 usable | Estimated: Dutch tests of 2024 models span ~51-95 kWh net (id.nl) |
| `consumption_kwh_per_km` | 0.18 | Estimated from Dutch real-world tests of 2024 models, 0.168-0.195 kWh/km (id.nl); Brady measured 0.265 for the 2010-era i-MiEV |
| Car on-board limits | 11 kW AC, 130 kW DC | Estimated |
| `soc_min` / `soc_target_home` / `soc_target_away` | 0.10 / 0.90 / 0.80 | Estimated (common battery-care practice) |
| `annual_km` | 14,800 | CBS: private electric car, 2023 average (all EVs incl. business: 18,100 in 2024, provisional) |
| `use_probability` | 0.80 weekday / 0.60 weekend | Estimated |
| Weekday departure weights | first departure from home | Digitised approx. from Brady & O'Mahony 2016, Fig. 3 (Irish trial, 4,021 weekday driving days) |
| Weekday arrival weights | arrivals home | Digitised approx. from Brady & O'Mahony 2016, Fig. 10 ("expected") |
| Weekend departure/arrival | later, wider | Estimated (the trial covered weekdays only) |
| Distance sigma | 0.8 (lognormal) | Estimated to match the shape of Brady Fig. 3 |
| Copula correlation | dep-dist -0.37; dep-arr 0.3; arr-dist 0.2 | -0.37 from Brady's correlation matrix R(1,3); others estimated |
| Plug-in probability by SOC | 1.0 / 0.9 / 0.6 / 0.35 / 0.1 | Estimated, shaped after Brady's SOC-conditioned decision (overall P(charge overnight \| charger available) = 0.55) and Lojowska's SOC < 50% scenario |
| Plug-in model (option) | `plug_in.model = "logistic"`: p = 1 / (1 + exp((SOC - 0.5) / 0.0782)) | Harbrecht et al. 2018 / Fischer et al. 2019: indifference level 50% at home; sensitivity = 14.2 %-SOC x sqrt(3)/pi (SOC-at-plug-in spread, Schäuble et al. 2017). Off by default, see below |
| Plug-in delay | 70% immediate, rest uniform 0.25-5 h | Brady & O'Mahony 2016, Fig. 7 |
| Charging timer (option) | `home_charging_start_hour`: null (start on plug-in) | Off by default. A clock hour (e.g. 23) delays charging to the start of an off-peak tariff |
| `probability_per_trip_day` (away) | 0.27 | Calibrated to RVO Nationaal Laadonderzoek 2025: drivers who can charge at home charge 81% of their km there |

The time-of-day data is Irish (2010s). It is the best open,
trip-resolved EV dataset found; Lojowska et al.'s Dutch marginals could
not be retrieved. Replace these weights first when Loenen survey data
arrives.

### Emergent behaviour with the defaults

Measured over 90 simulated `generic`/`working_couple`/
`family_with_children` households, 2025:

| Indicator | Simulated | Reference |
| --- | --- | --- |
| Driving | 14,940 km/yr (mean) | CBS 14,800 |
| Home share of charged energy | 0.80-0.84 for away probability 0.28-0.22; 0.27 chosen | RVO 0.81 |
| Home charging | ~2,300 kWh/yr (p10-p90 ~2,100-2,500) | 14,800 x 0.18 x 0.81 / 0.92 ≈ 2,345 |
| Plug-in rate | ~2.7 connections/week, ~0.5 per driving day | Brady: 0.55 overnight |
| Connections per vehicle-day | 0.38 (p10-p90 0.36-0.41; 24 households) | MINI E private-household trial 0.40; Harbrecht et al. (2018) model 0.42; German fleet trials 0.29 |
| Charging block | ~3.2 h at 7.4 kW (~22 kWh) | ElaadNL: 22-36 kWh per home/work session (older data) |
| Connection time | ~25-30 h | ElaadNL driver survey: 9.7 h; ours is longer because the car stays connected over non-driving days |
| Battery cycling | ~37 equivalent full cycles/yr at home | |

Retired households drive less (~10,500 km/yr), because presence coupling
keeps the car home when nobody leaves.

### Plug-in model and charging timer

Two alternatives are switched off by default, so existing results are
unchanged:

- **Logistic plug-in decision** (`plug_in.model = "logistic"`). This is
  the connection model of Harbrecht et al. (2018) and Fischer et al.
  (2019). It has two parameters instead of a five-step table, which makes
  it easier to fit to survey data. With their parameters and our 60 kWh
  battery it gives 0.20 connections per vehicle-day, against 0.34 with a
  22 kWh battery. Their value was fitted on small 2010s cars: a large
  battery reaches the same SOC thresholds less often. Fit
  `indifference_soc` to the Loenen survey before using it; 0.65 gives
  0.30 connections per vehicle-day.
- **Charging timer** (`home_charging_start_hour`). The car is connected
  from plug-in, but only starts charging at the given clock hour, for
  example 23:00, the start of a Dutch off-peak tariff. Over 24
  households this changes neither connections (0.39 per vehicle-day) nor
  energy (2,249 vs 2,261 kWh/yr). Daytime and evening charging moves to
  after 23:00. It is the rule-based baseline between uncontrolled and
  optimised charging.

## 4. Is a 4-hour session enough at 7.4 kW?

It is the wrong question for a fixed number: the right session length
follows from the energy actually needed. With the defaults:

- **4 h at 7.4 kW** = 29.6 kWh from the grid = 27.2 kWh into the battery
  (x 0.92) ≈ 150 km of driving.
- **An average day** (14,800 km / 365 = 40.5 km → 7.3 kWh battery side)
  needs ~1.1 h. A typical day therefore needs far less than 4 h.
- **A full recharge** of a 60 kWh battery from 10% to 90% (48 kWh battery
  side, 52 kWh grid side) needs ~7.1 h, plus a little taper. A deep
  recharge therefore needs more than 4 h.
- **Simulated**: because the SOC carries over, cars plug in every few
  days for ~3.2 h (~22 kWh), at the low end of the 22-36 kWh per
  home/work session ElaadNL reports from older data.

The old fixed 4 h x 0.6 days/yr gave ~6,500 kWh/yr at home, about 2.8
times the ~2,300 kWh/yr implied by CBS mileage, real-world consumption
and RVO's home-charging share. Any charger power is accepted now; a
higher one just shortens the sessions, capped at the car's own AC limit
(11 kW by default), so a 22 kW wallbox still charges at 11 kW.

## 5. Plugging in survey data (Loenen)

Everything is data. Survey results go into an overrides JSON or dict,
which is deep-merged over `ev.json`. Unknown keys raise an error, so
typos fail loudly. Hour weights may be raw counts; they are normalised.

| Survey item | Where it goes |
| --- | --- |
| Household has an EV (yes/no) | `has_ev=True/False`; unknown → `has_ev=None` + `ownership_probability` |
| Charger power, single/three-phase | `charging_modes.slow.power_kw`; car limit `vehicle.max_ac_power_kw` |
| Car model / battery size | `vehicle.battery_capacity_kwh`, `consumption_kwh_per_km` |
| Annual km | `mobility.annual_km` |
| Usual departure / arrival times | `mobility.departure_hour_weights`, `arrival_hour_weights` |
| How often / at what SOC they plug in | `plug_in.probability`, `soc_bin_upper_edges` |
| Charge limit set in the car | `battery.soc_target_home` |
| Share charged away from home | `away_charging.probability_per_trip_day` |
| No private charge point | `has_home_charger: false` |
| A **measured** hourly charging profile | `ElectricityConsumptionProfile(..., ev_charging_kw=series)` replaces the simulation |

### Metered household electricity, EV and internal gains

A smart meter measures one number per interval: the household's net
exchange with the grid. Every part of it is real electricity use, and
every part can be modelled; they differ only in whether they heat the
dwelling:

```text
net meter = appliances + lighting + EV charging (+ heat pump, ...)
            - PV generation (+ home battery charging - discharging)
```

| Component | On the meter | Internal heat gain (buem `elecLoad`) | Energy-system demand (Calliope) |
| --- | --- | --- | --- |
| Appliances, lighting | yes | yes | yes |
| EV home charging | yes | **no**: the charger is in the driveway or garage | yes, as its own demand or flexibility |
| PV generation | yes, negative | no | yes, as supply |

So EV load is not dropped, it is only kept apart from the gain term.
occupancy returns `total_power_kwh` (appliances, the gain-relevant part),
`ev_charging_kw` (the EV) and `total_power_incl_ev_kwh` (their sum, the
meter-level demand without PV). buem passes `ev_charging_kw` on as
`ev_charging_kW`, and its hourly export writes it as `ev_kW` next to
`elec_kW`. Total electricity demand for an energy-system model is
`elec_kW + ev_kW`.

To use a measured meter series as internal gains, take the non-appliance
parts out first:

```python
from occupancy import subtract_ev_load, to_buem_profiles

appliances = subtract_ev_load(metered_total, ev_charging_kw)   # measured EV series
cfg.update(to_buem_profiles(result, elec_load=appliances))
```

In buem: `use_provided_elecLoad=True`, `elecLoad_includes_ev=True` and the
measured `ev_charging_kW`.

- **Only a measured EV series can be subtracted hour by hour.** A
  simulated one matches the meter on average, not in timing: subtracting
  it from real data produces negative hours and shifted load. buem
  refuses that combination.
- **PV.** Net meter data of a household with PV is already reduced by its
  generation, so gross use = net + PV generation. buem reconstructs it
  (`elecLoad_net_of_pv`) from a supplied PV output series `pv_kW`:
  inverter data (exact), or a modelled profile from conversion-
  technologies' PV generation (an estimate: it follows the weather data,
  not the real panels). buem computes no PV output itself. With a home
  battery the net reading also hides the battery's flows, and buem
  refuses it.

## 6. Module boundary: occupancy, conversion-technologies, Calliope

The EV is also an independent technology option in EnerPlanET, optimised
in Calliope 0.7.0. The split follows the UU-BUEM rule: occupancy owns
behaviour, other modules own physics and economics.

| Concern | Module | Status |
| --- | --- | --- |
| Ownership, trips, departure/arrival, distance, plug-in behaviour, when the car is connected, driving energy, uncontrolled charging profile | **occupancy** | built |
| `has_ev` and friends as building attributes; EV load reported apart from `elecLoad`; meter-total subtraction | **buem** | built |
| Charger, vehicle-to-grid discharger and traction battery as technologies, with costs; the "only while plugged in" constraint | **conversion-technologies** (`new/ev/`) | built |
| Per-building wiring of occupancy's time series, prices, smart-charging scenarios | **Calliope scenario layer** | not yet for Loenen |

**Is an EV a conversion, demand or flexibility technology?** All three.
From the grid's side it is a flexible demand: the driving energy is fixed
but its timing is free while the car is plugged in. With vehicle-to-grid
it is storage. Physically it is a charger (conversion), a battery
(storage) and a driving demand, linked by their own `ev_electricity`
carrier. The flexibility emerges from the battery: the optimiser can
charge at any connected hour as long as the battery holds enough for the
next trip. See conversion-technologies'
`docs/calliope_schema_mapping.md`, "Electric vehicles", for the technology
table, costs and the required scenario settings: cyclic battery storage, a
fixed capacity for an existing wallbox, and the availability series for
every charger and V2G technology.

Verified in a real `calliope==0.7.0` solve for one household and one
January week with a time-of-use price:

- no charging or discharging while unplugged;
- the same 59.0 kWh as occupancy's uncontrolled profile, but all of it in
  cheap hours (EUR 8.86 instead of EUR 14.90);
- the battery never below its 6 kWh reserve.

Battery size, charger power and efficiency appear on both sides:
occupancy needs them for the uncontrolled baseline, the optimiser as
technology parameters. Neither package imports the other, so a scenario
should feed the same values to both.

**Same formulation as the closest optimisation study.** Iqbal, Shafiullah
& Aurangzeb (2026) model an EV fleet in a campus energy hub as storage
that can charge and discharge only while connected, minus the driving
energy. The Calliope representation here (charger and V2G bounded by
`ev_plugged_in`, battery as storage, driving as demand) is the same
balance per household, with the connection series taken from the
behaviour model. Comparison: `references.md`, "Positioning".

**Discrete charging rates.** Gan, Topcu & Low (2012) schedule EV charging
with a *discrete* rate (a charger is on at its rated power or off) and
coordinate many cars by a stochastic distributed protocol that flattens
the aggregate load. That is a control and optimisation question, so it
belongs to the optimisation layer, not to occupancy's behaviour model.

- **Uncontrolled baseline.** occupancy's simulation already charges at
  the full rate whenever it charges (apart from the taper near full), so
  the baseline has the paper's on/off shape.
- **Calliope.** The model treats charging power as continuous between 0
  and the charger capacity, which is a linear relaxation of the discrete
  problem.
- **Distribution-grid studies.** If one needs block-shaped charging,
  Calliope's MILP mode (integer units) can impose discrete rates.

## 7. Limitations and follow-ups

### Presence coupling, plainly

The coupling decides *when the car is away*, not when it charges. A car
should not be out while everyone is at home, so on each driving day the
model picks a trip window during which at least one household member is
out.

How well that works depends on how realistic the occupancy profile's
absences are. `working_couple` uses a Markov generator, where absences
come in realistic blocks (out 08:00-17:00), so trips line up with them.
`generic` draws each hour's presence independently, so its absences are
scattered single hours, and there is no clean block for a trip to match.
It is a limitation of that occupancy generator, not of the EV model.

Charging timing then follows: the car charges after it comes home, mostly
in the evening and at night, and on weekends also by day, because it is
home more. Simulated over 90 households (share of cars):

| Hour | Plugged in, weekday | Plugged in, weekend | Charging, weekday | Charging, weekend |
| --- | --- | --- | --- | --- |
| 03:00 | 0.53 | 0.57 | 0.02 | 0.01 |
| 10:00 | 0.22 | 0.47 | 0.01 | 0.00 |
| 14:00 | 0.17 | 0.37 | 0.03 | 0.06 |
| 19:00 | 0.36 | 0.52 | 0.17 | 0.15 |
| 22:00 | 0.48 | 0.58 | 0.13 | 0.06 |

The evening charging peak comes from charging starting on plug-in
(uncontrolled). The night-time plugged-in window is the flexibility an
optimiser, or a timer, can use.

### Detecting EV charging in meter data

If a survey gives only total meter readings and no charging log, the EV's
share can still be estimated from the shape of the data.

- **The signal.** Home charging at 7.4 kW shows up as a plateau a few
  kilowatts above the household's normal level, lasting one to several
  hours, mostly in the evening. Ordinary appliances rarely sustain that.
- **What a detector would do.** It flags such blocks (start, duration,
  energy), takes them out as the EV series, and leaves the rest as the
  appliance load.
- **Status and accuracy.** Not built yet. It would be the fallback when no
  charging log exists. It works well at hourly resolution only for
  high-power chargers, and confuses a long oven or heat-pump block with
  charging.

### Service buildings

Workplace and customer charging is a different behaviour: cars arrive
with the occupants (office staff in the morning, shoppers through the
day), stay for the visit, and charge at AC charge points or DC fast
chargers.

- **Data.** The arrivals are already in the occupancy profile (the
  increase in `n_present`). A model needs, per building type: the share of
  occupants arriving by EV, energy per session, and charge-point power.
- **conversion-technologies.** It already has the matching technologies:
  `ev_charger_ac_building` and `ev_charger_dc_community`.
- **Status.** Not built. A Dutch source exists: ElaadNL and 4TU.ResearchData
  publish office car-park charging sessions (arrival, duration, energy).

### Data: Dutch, European, or Irish for now?

- **Dutch, available now.**
  - **ODiN (Onderweg in Nederland, CBS).** The national travel survey.
    StatLine tables 84702NED and 85055NED give trips by departure time,
    purpose and mode. The ODiN microdata (individual trip diaries, with
    departure, arrival and distance per car driver) can be requested by
    researchers through CBS/DANS. It is the best replacement for Brady's
    Irish time-of-day data and for estimating the copula correlations,
    the approach Lojowska et al. took with its predecessor.
  - **ElaadNL open data.** Arrival-time, connection-time and energy
    distributions of real charging sessions at private, workplace and
    public charge points (2018-2020).
  - **RVO Nationaal Laadonderzoek and CBS.** Already used for the
    calibration targets: annual km and home-charging share.
- **European.** The JRC survey "Driving and parking patterns of European
  car drivers" (Pasaoglu et al., 2012) covers six EU countries, not the
  Netherlands. Open tools built on such data (emobpy from German
  mobility data, RAMP-mobility for EU countries) are alternatives, but
  for Loenen they are no closer than ODiN.
- **Recommendation.** Keep Brady's Irish data as a placeholder. Replace
  it with ODiN (time of day and distance) plus the Loenen survey
  (ownership, charger power, battery size, plug-in habits). Every value
  can be swapped through `ev_config` overrides without code changes.

### Other open items

- **Home PV and batteries.** Done 2026-11-24. buem holds the building
  facts only (`has_pv`, `pv_capacity_kwp`, `has_battery`,
  `battery_capacity_kwh`, the roof faces) and accepts a supplied `pv_kW`
  for net meter data. PV generation is conversion-technologies'
  `generation_technologies` (PVWatts v8 via PySAM, identical to
  EnerPlanET's pysam-pv; costs from OpenTech-DB), as a Calliope supply
  technology. Open: wiring PV into the Loenen scenario (export/feed-in
  rules), and battery behaviour: occupancy would own household-battery
  behaviour only if it is rule-based (e.g. self-consumption); an
  optimised battery belongs in conversion-technologies / Calliope.
- **One trip block per day.** A midday return home, overnight trips and
  multi-day trips are not represented.
- **One car per household.**
- **Timer baseline: done** (`home_charging_start_hour`, above). Charging
  starts on plug-in by default. 83% of Dutch EV drivers with a private
  charge point say they charge smart there (self-reported, RVO
  Nationaal Laadonderzoek 2025), so the uncontrolled default overstates
  the evening peak. Use the timer or Calliope's smart charging for
  comparison.
- **Single-day travel data.** The day-to-day regularity of car use (the
  same commute every weekday) is not represented. Days are drawn
  independently, as in Harbrecht et al. (2018), whose German survey (MiD)
  also records one day per household. Panel data (German Mobility Panel)
  or the Loenen survey would be needed.
- **No seasonality.** `monthly_consumption_multiplier` stays neutral until
  a sourced winter uplift is found.
- **Fast-charging battery wear.** Not priced, because the evidence that DC
  fast charging shortens battery life is mixed. conversion-technologies
  prices V2G wear only.

## References

The annotated list for publication, with roles, status and BibTeX, is in
[`references.md`](references.md) and [`references.bib`](references.bib).

- Brady, J., O'Mahony, M. (2016). Modelling charging profiles of electric
  vehicles based on real-world electric vehicle charging data.
  *Sustainable Cities and Society* 26, 203-216.
  doi:10.1016/j.scs.2016.06.014
- Gan, L., Topcu, U., Low, S. H. (2012). Stochastic distributed
  protocol for electric vehicle charging with discrete charging rate.
  *IEEE Power and Energy Society General Meeting*, July 2012. Discussed
  in section 6 (optimisation layer, not the behaviour model).
- Fischer, D., Harbrecht, A., Surmann, A., McKenna, R. (2019). Electric
  vehicles' impacts on residential electric local profiles -- A
  stochastic modelling approach considering socio-economic, behavioural
  and spatial factors. *Applied Energy* 233-234, 644-658.
  doi:10.1016/j.apenergy.2018.10.010
- Harbrecht, A., McKenna, R., Fischer, D., Fichtner, W. (2018).
  Behavior-oriented modeling of electric vehicle load profiles. Working
  Paper Series in Production and Energy No. 29, KIT-IIP.
  doi:10.5445/IR/1000082537
- Schäuble, J., Kaschub, T., Ensslen, A., Jochem, P., Fichtner, W. (2017).
  Generating electric vehicle load profiles from empirical data of three
  EV fleets in Southwest Germany. *Journal of Cleaner Production* 150.
  doi:10.1016/j.jclepro.2017.02.150 (cited via Harbrecht et al. 2018)
- Lojowska, A., Kurowicka, D., Papaefthymiou, G., van der Sluis, L.
  (2012). Stochastic modeling of power demand due to EVs using copula.
  *IEEE Transactions on Power Systems* 27(4), 1960-1968.
  doi:10.1109/TPWRS.2012.2192139. Method only: the full text was not
  accessible, so no values are taken from it.
- CBS (2024). Zakelijke automobilist rijdt meer elektrisch dan op diesel
  (news 2024/45); CBS visualisation "Hoeveel rijden personenauto's?";
  StatLine 85396NED.
- CBS (2025). Meer dan 1 miljoen stekkerauto's in Nederland (news
  2025/22).
- RVO (2025). Nationaal Laadonderzoek 2025.
- ElaadNL (2022). Charge management of electric vehicles at home.
- id.nl Verbruiksmonitor: real-world consumption tests of 2024 EV models.
- CBS, Onderweg in Nederland (ODiN): StatLine 84702NED, 85055NED;
  microdata on request.
- Pasaoglu, G. et al. (2012). Driving and parking patterns of European
  car drivers -- a mobility survey. JRC Scientific and Policy Reports.
