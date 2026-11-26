# Electric vehicles: references

These are all sources behind the household EV model (occupancy), the EV
technologies and costs (conversion-technologies), and the Loenen
optimisation (Calliope). Each entry gives its role and status:

- **used**: values or a method are taken from it;
- **cited via**: known only through a source that was read;
- **related**: for positioning, nothing taken from it.

BibTeX entries are in [`references.bib`](references.bib), with the same keys.
The method is described in [`design.md`](design.md).

## A. EV behaviour and charging models

| Key | Reference | Role in this work | Status |
| --- | --- | --- | --- |
| `brady2016` | Brady, J., O'Mahony, M. (2016). Modelling charging profiles of electric vehicles based on real-world electric vehicle charging data. *Sustainable Cities and Society* 26, 203-216. doi:10.1016/j.scs.2016.06.014 | Weekday first-departure and arrival-home distributions, departure-distance correlation (-0.37), plug-in delay (70% immediate, otherwise 0.25-5 h), charging efficiency 0.92, warm-up idea. Irish trial, 15 cars. | used |
| `lojowska2012` | Lojowska, A., Kurowicka, D., Papaefthymiou, G., van der Sluis, L. (2012). Stochastic modeling of power demand due to EVs using copula. *IEEE Transactions on Power Systems* 27(4), 1960-1968. doi:10.1109/TPWRS.2012.2192139 | Gaussian copula over departure, arrival and distance (Dutch travel survey). Method only: full text not accessed. | used (method) |
| `fischer2019` | Fischer, D., Harbrecht, A., Surmann, A., McKenna, R. (2019). Electric vehicles' impacts on residential electric local profiles -- A stochastic modelling approach considering socio-economic, behavioural and spatial factors. *Applied Energy* 233-234, 644-658. doi:10.1016/j.apenergy.2018.10.010 | Journal version of `harbrecht2018` (synPRO-emobility). Cite this one in the paper. | used (via `harbrecht2018`) |
| `harbrecht2018` | Harbrecht, A., McKenna, R., Fischer, D., Fichtner, W. (2018). Behavior-oriented modeling of electric vehicle load profiles: A stochastic simulation model considering different household characteristics, charging decisions and locations. Working Paper Series in Production and Energy No. 29, KIT-IIP, Karlsruhe. doi:10.5445/IR/1000082537 | Logistic SOC connection model (`plug_in.model = "logistic"`): sensitivity 0.0782 = 14.2 %-SOC x sqrt(3)/pi; home indifference level 50%. Validation benchmark: 0.42 charging events per vehicle-day (MINI E private-household trial 0.40) against our 0.38 (sec. C). Evidence that "always charge on arrival" overestimates charging (2.23 events/day). | used (full text read) |
| `schauble2017` | Schäuble, J., Kaschub, T., Ensslen, A., Jochem, P., Fichtner, W. (2017). Generating electric vehicle load profiles from empirical data of three EV fleets in Southwest Germany. *Journal of Cleaner Production* 150. doi:10.1016/j.jclepro.2017.02.150 | SOC at plug-in, sd 14.2 %-SOC (company fleets): the source of the logistic sensitivity. 0.29 charging events per vehicle-day. | cited via `harbrecht2018` |
| `franke2013` | Franke, T., Krems, J. F. (2013). Understanding charging behaviour of electric vehicle users. *Transportation Research Part F* 21, 75-89. doi:10.1016/j.trf.2013.09.002 | SOC at charging is explained by comfortable range and user-battery interaction style: the behavioural basis of an SOC-dependent plug-in decision. MINI E trial: 83.7% of charging at private charge points. | cited via `harbrecht2018` |
| `babrowski2014` | Babrowski, S., Heinrichs, H., Jochem, P., Fichtner, W. (2014). Load shift potential of electric vehicles in Europe. *Journal of Power Sources* 255, 283-293. doi:10.1016/j.jpowsour.2014.01.019 | Workday and weekend EV charging curves for Germany. | related (cited via `harbrecht2018`) |
| `morrissey2016` | Morrissey, P., Weldon, P., O'Mahony, M. (2016). Future standard and fast charging infrastructure planning: An analysis of electric vehicle charging behaviour. *Energy Policy* 89, 257-270. doi:10.1016/j.enpol.2015.12.001 | Irish charging behaviour: home preferred, fast charging favoured among public options. Supports home = slow, away = fast. | related (cited via `harbrecht2018`) |
| `iqbal2026` | Iqbal, S., Shafiullah, M., Aurangzeb, M. (2026). Stochastic modeling and optimization of electric vehicle fleet integration in smart microgrids: Impacts of charging infrastructure, controlled strategies, and vehicle to grid participation. *Sustainable Energy, Grids and Networks* 46, 102198. doi:10.1016/j.segan.2026.102198 | Closest prior work to the *optimisation* side: Monte Carlo EV demand (1,000 runs) feeding an energy-hub MIP (GAMS/CPLEX) of a campus microgrid; uncontrolled, controlled and V2G modes under a time-of-use tariff. Its EV storage balance (Eq. 8: charging x efficiency - discharge / efficiency - driving energy, with charge and discharge bounded to connected hours, Eqs. 4-5) is the formulation used here in Calliope. See "Positioning". | related (full text read) |
| `iqbal2021` | Iqbal, M. N., Kütt, L., Lehtonen, M., Millar, R. J., Püvi, V., Rassõlkin, A., Demidova, G. L. (2021). Travel activity based stochastic modelling of load and charging state of electric vehicles. *Sustainability* 13(3), 1550. doi:10.3390/su13031550 | Travel-survey (Finland) Monte Carlo of departure, distance and arrival, with SOC; managed and unmanaged weekday charging. Same family of methods as ours; a different group from `iqbal2026`. | related (not read) |
| `gan2012` | Gan, L., Topcu, U., Low, S. H. (2012). Stochastic distributed protocol for electric vehicle charging with discrete charging rate. *IEEE Power and Energy Society General Meeting*, San Diego, July 2012. IEEE Xplore 6344847 | Decentralised coordination of many EVs by a utility price signal, with discrete charging rates. Not used: here charging is scheduled centrally by Calliope against a price. Related work for smart charging only. | related |
| `pasaoglu2012` | Pasaoglu, G. et al. (2012). Driving and parking patterns of European car drivers -- a mobility survey. JRC Scientific and Policy Reports, European Commission. | Candidate European-level source for time of day and distance. | related |

## B. Data and statistics (Netherlands)

| Key | Reference | Role | Status |
| --- | --- | --- | --- |
| `cbs2024km` | CBS (2024). Zakelijke automobilist rijdt meer elektrisch dan op diesel (news release 2024/45); StatLine 85396NED | 14,800 km/yr for a private EV (2023) | used |
| `cbs2025ev` | CBS (2025). Meer dan 1 miljoen stekkerauto's in Nederland (news release 2025/22) | National plug-in share (~6% of private cars), set against the Loenen 20% | used |
| `rvo2025` | RVO (2025). Nationaal Laadonderzoek 2025. Rijksdienst voor Ondernemend Nederland | 81% of km charged at home by drivers who can (calibration target for away charging) | used |
| `elaadnl2022` | ElaadNL (2022). Charge management of electric vehicles at home | Connection time (9.7 h) and session energy; plausibility checks | used |
| `idnl` | id.nl Verbruiksmonitor (real-world consumption tests of 2024 EV models) | 0.18 kWh/km; usable battery range | used |
| `cbsodin` | CBS, Onderweg in Nederland (ODiN), StatLine 84702NED / 85055NED; microdata via CBS/DANS | Recommended replacement for the Irish time-of-day data | planned |

## C. Validation benchmark (from section A)

Plug-in frequency, in charging connections per vehicle per day:

| Source | Value | Note |
| --- | --- | --- |
| MINI E trial, Berlin, private households (`franke2013`, via `harbrecht2018`) | 0.40 | 250 km range car |
| Harbrecht et al. (2018), logistic, home indifference level 50% | 0.42 | ~22 kWh cars |
| Three German fleet trials (`schauble2017`) | 0.29 | mostly company fleets |
| This model, default SOC table, 60 kWh (24 households) | 0.38 (0.36-0.41) | `generic` and `working_couple` |
| This model, logistic 50%, 60 kWh | 0.20 | larger battery: thresholds reached less often |
| This model, logistic 50%, 22 kWh | 0.34 | close to Harbrecht's 0.42 |

The default is in line with the private-household benchmark. The logistic
parameters fitted to small 2010s batteries do not carry over to a 60 kWh
car unchanged. Fit them to the Loenen survey before using them.

## D. Technology costs and prices (conversion-technologies, Loenen)

Full rows, including price basis and access dates, are in
`conversion-technologies/docs/sources/references.csv`.

| BibTeX key | Source id | Reference | Used for |
| --- | --- | --- | --- |
| `brady2016` | `BRADY_2016` | as in section A | Charger efficiency 0.92 |
| `anwb2025` | `ANWB_LAADPAAL` | ANWB (2025). Wat kost een laadpaal? | Home AC charger, ~EUR 2,000 incl. VAT installed -> 150.26 EUR2025/kW |
| `virta2024` | `VIRTA_DC_2024` | Virta (2024). DC charging station costs, delivery times and ideal locations | DC charger ~200 EUR/kW -> 204.25 EUR2025/kW |
| `bnef2024` | `BNEF_BATTERY_2024` | BloombergNEF (2024). Lithium-ion battery pack price survey | BEV pack USD 97/kWh -> V2G wear 0.04576 EUR2025/kWh |
| `ecb2025usd` | `ECB_EXR_USD` | ECB euro reference rates, USD, 2024 annual average 1.08238 | Currency conversion |
| `eurostathicp2026` | `EUROSTAT_HICP` | Eurostat prc_hicp_aind, EA20 | Price-year conversion to EUR2025 |
| `eurostatnrgpc204` | `EUROSTAT_NRG_PC_204` | Eurostat nrg_pc_204, NL households 2,500-4,999 kWh, excl. taxes | Flat grid price EUR 0.26035/kWh |
| `minfin2020discount` | `NL_DISCOUNT_2020` | Ministerie van Financiën (2020). Kabinetsreactie werkgroep Discontovoet | Interest rate 2.25% |
| `energycharts2018` | -- | Fraunhofer ISE, Energy-Charts API: day-ahead price, bidding zone NL, 2018 (data: Bundesnetzagentur, SMARD.de; CC BY 4.0) | Hourly price shape (`grid_price_nl_2018.csv`) |

The V2G hardware premium (350 EUR/kW) is an assumption, with no source.

### Heat and cooling technologies, fuel (Loenen energy system)

| BibTeX key | Source id | Reference | Used for |
| --- | --- | --- | --- |
| `dea2026individual` | `DEA_IND_2026` | Danish Energy Agency (2026). Technology Data for Individual Heating Plants | Household and building boilers and heat pumps; reversible air-to-air heat pump |
| `dea2026eldh` | `DEA_ELDH_2026` | Danish Energy Agency (2026). Technology Data for Generation of Electricity and District Heating | Community heat pumps, electric and pellet boilers, pellet CHP |
| `dea2026largehp` | `DEA_LARGE_HP_BRIEF_2026` | Danish Energy Agency (2026). Technology Brief: large heat pumps, electric boilers, geothermal | Background to the community heat pump data |
| `dittmann2017hre4` | `HRE4_D32_2017` | Dittmann, Rivière, Stabat (2017). Space Cooling Technology in Europe, Heat Roadmap Europe D3.2 | Chillers (compression, absorption): cost, O&M, lifetime, SEER |
| `rvo2026isde` | `RVO_ISDE_HP_2026_11` | RVO (2026). Meldcodelijst Warmtepompen (ISDE) | Household heat pump capacity limits |
| `dea2026soeb` | `DEA_SOEB25` | Danish Energy Agency (2026). Socio-economic calculation assumptions for energy prices 2025 | Wood pellet price |
| `dkkerm2` | `DKK_EUR_ERM2` | Danmarks Nationalbank, ERM II central rate | DKK to EUR conversion |

Interest rate and price-year conversion for these technologies use
`minfin2020discount` and `eurostathicp2026` (above).

## E. Software

| Key | Reference | Used for |
| --- | --- | --- |
| `pfenninger2018` | Pfenninger, S., Pickering, B. (2018). Calliope: a multi-scale energy systems modelling framework. *Journal of Open Source Software* 3(29), 825. doi:10.21105/joss.00825 | Optimisation framework (version 0.7.0) |
| `cbc` | COIN-OR Branch and Cut (CBC) solver | Linear solver |

## Positioning notes for the paper

The two closest papers each cover one half of this work:

| | `fischer2019` / `harbrecht2018` | `iqbal2026` | This work |
| --- | --- | --- | --- |
| Question | EV effect on household load profiles | Charging infrastructure and control on a campus microgrid | EV behaviour and its flexibility in a building-level energy system |
| Behaviour model | Survey-based trips (MiD, Germany), logistic SOC plug-in, charging by location | Monte Carlo over battery size, trip time, arrival time, SOC; distributions not reported | Copula trips tied to household presence, SOC carried across days, SOC plug-in, home slow / away fast |
| Optimisation | None (load-management potential only) | Energy-hub MIP, cost (+ emissions), TOU tariff | Calliope 0.7.0 LP, cost, NL day-ahead price |
| Charging modes | Uncontrolled | Uncontrolled, controlled, V2G | Uncontrolled, timer, smart, V2G |
| Scale | Households and parking locations | 300 fleet/workplace EVs, shared ports with queuing | 264 household EVs in 1,260 buildings, one wallbox each |
| Data | Behaviour data published | "Available on request" | Open code and data sources |

- **Closest prior work on behaviour** is `fischer2019`/`harbrecht2018`:
  survey-based trips, an SOC-dependent logistic plug-in decision, and
  charging by location.
- **Closest prior work on optimisation** is `iqbal2026`. Points worth
  using in the paper:
  - **Same EV formulation.** Their EV fleet is storage whose charging
    and discharging are allowed only while connected, minus driving
    energy (Eqs. 4-5, 8). The Calliope model here does the same per
    household, with the connection series coming from the behaviour
    model instead of fixed plug-in windows.
  - **Smart-charging savings depend on the price spread.** They find
    smart charging cuts charging cost per EV by about a quarter (Table 3,
    USD 5.4 to 4.0) under a TOU tariff of USD 0.082-0.145/kWh, a daily
    spread of about half the price level. Here it saves about 7% (EUR
    0.020/kWh) under the 2018 NL day-ahead shape: a mean daily spread of
    EUR 0.037/kWh on a EUR 0.26/kWh price, 14% of the level.
  - **V2G value depends on what it replaces.** In their case V2G mainly
    offsets cycling of a 6 MWh stationary battery. Here there is no
    stationary battery, and V2G is not bought: the 2018 spread does not
    cover round-trip losses, battery wear and the bidirectional charger.
  - **Shared ports and queuing** matter for workplace and fleet charging
    (their result: more ports and longer plug-in windows raise
    fulfilment from 65% to 97%). Not modelled here: each household has
    its own wallbox. It becomes relevant for service-building charging
    (open item).
  - **Caveats when citing their numbers.** The input distributions are
    not reported, so the behaviour model cannot be reproduced. Some
    figures and tables disagree: average queue times are 65/45/25/10 min
    for 20-50 ports in Table 2 but 4/0/0/0 min in Fig. 12(b), and the
    gas generator is 194 kW in the text but 1,994 kW in Fig. 5. Cite
    their qualitative findings rather than the exact values.
- **This work differs from both** in four ways:
  1. Trips are tied to the household's own simulated presence
     (occupancy), so the car is away when people are away.
  2. EV charging is kept out of the internal heat gains passed to the
     building thermal model, and can be subtracted from metered totals.
  3. The output feeds an optimisation model: the plug-in availability
     becomes a time-varying bound in Calliope 0.7.0, and the household
     battery is modelled as storage.
  4. The defaults are Dutch, with explicit hooks for survey data.
- **Charging strategies compared**:
  - uncontrolled, as in `brady2016` and `harbrecht2018`;
  - timer or off-peak start (`home_charging_start_hour`);
  - cost-optimal smart charging (Calliope);
  - V2G (Calliope).

  `gan2012` is the decentralised alternative to the central scheduling
  used here.
- **Known shared limitation.** Single-day travel diaries (MiD in
  `harbrecht2018`, the Irish trial in `brady2016`) cannot show
  day-to-day regularity. Panel data (MOP) or the Loenen survey would be
  needed for that.
