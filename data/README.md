# Data

All input data used in the paper are included in this folder. The analysis
pipeline (`scripts/run_all.py`) reads only these files; no download or
external model run is needed to reproduce the results.

| File | Content | Source | Size |
|------|---------|--------|------|
| `ENTSOE_day_ahead_prices.csv` | Hourly day-ahead prices, 27 bidding zones, 2015–2025 (analysis uses 22 countries, 2018–2025) | ENTSO-E Transparency Platform | 18 MB |
| `GENeSYS_MOD_prices.csv` | Hourly shadow prices of the power balance, 30 model regions, 4 scenarios, model years 2018–2060 (analysis uses 22 countries, 2018/2025/2030) | GENeSYS-MOD, EnVis-2060 scenarios | 76 MB |
| `ENTSOE_vre_generation_2025.csv` | Hourly solar and wind generation, 22 countries, 2025 (value factors, Section 4.2) | ENTSO-E Transparency Platform | 3 MB |
| `GENeSYS_MOD_vre_production_2025.csv` | Solar and wind production per timeslice, 22 countries, 2025 (value factors, Section 4.2) | GENeSYS-MOD EU-EnVis-2060 v1.2.0 | 0.7 MB |
| `checksums.sha256` | SHA-256 checksums of the files above | — | — |

Country codes are ISO 3166-1 alpha-2 (`UK` in the GENeSYS-MOD files is the
United Kingdom; `NONEU_Balkan` covers AL, BA, XK, ME, MK, RS). The 22 analysis
countries and their ENTSO-E bidding zones are listed in Table C.2 of the paper
and in `scripts/config.py`.

---

## ENTSO-E day-ahead prices — `ENTSOE_day_ahead_prices.csv`

**Source.** ENTSO-E Transparency Platform, *Day-ahead Prices [12.1.D]*,
<https://transparency.entsoe.eu/>, retrieved via the RESTful API with
`entsoe-py` in February 2026. Data published by ENTSO-E are redistributed here
with attribution, as required by the Transparency Platform terms of use.
Cite as: ENTSO-E (2026). Day-ahead electricity prices. ENTSO-E Transparency
Platform.

**Columns.** `timestamp` (start of the hour, UTC, ISO 8601), followed by one
column per country label (EUR/MWh). Each column holds one bidding zone:
`DE` = DE-LU, `IE` = IE-SEM, and all other analysis countries = the zone of
the same code. For multi-zone countries outside the analysis the column holds
one representative zone (`DK` = DK1, `IT` = IT-North, `NO` = NO2, `SE` = SE3).

**Processing** (download with `entsoe-py`):
1. Prices are downloaded per bidding zone for 2015-01-01 to 2026-01-01 (UTC).
2. For AT and DE-LU, the joint DE-AT-LU zone is used before the split on
   2018-10-01.
3. Sub-hourly prices are averaged to hourly values.
4. Isolated missing hours are filled by linear interpolation. In the analysis
   sample (22 countries, 2018–2025, 70,128 hours each) the file has no missing
   values.

All calendar groupings in the analysis (hour of day, day of week, month,
season) are derived from the UTC timestamps.

## GENeSYS-MOD shadow prices — `GENeSYS_MOD_prices.csv`

**Source.** Dual values of the hourly regional power-balance constraint of the
Global Energy System Model (GENeSYS-MOD; Löffler et al., 2017), run with the
scenario inputs of the European Energy Vision 2060 project (EnVis-2060;
Barani et al., 2025) for the four scenarios GoRES, NECP Essentials,
REPowerEU++ and Trinity.

**Columns.** `year` (model year), `scenario`, `Hour` (1–8760, hour of the
model year; hour 1 is mapped to 1 January 00:00 of that year), followed by one
column per model region (EUR/MWh).

**Processing.** The four raw model output files
`output_marginals_{gores,necpessentials,repowereu,trinity}.csv` (long format:
run, region, hour, value; 380 MB in total) were pivoted to one row per
year × scenario × hour. Region-hours that do not appear in the raw output were
set to 0 EUR/MWh. In the analysis sample (22 countries; 2018, 2025, 2030;
4 scenarios) this applies to 6.9% of country-hours.

## Solar and wind generation — `ENTSOE_vre_generation_2025.csv`

**Source.** ENTSO-E Transparency Platform, *Actual Generation per Production
Type [16.1.B&C]*, retrieved via the RESTful API with `entsoe-py` in January
2026 (aggregated generation only, sub-hourly values averaged to hourly means,
MW).

**Columns.** `timestamp` (UTC), `<country>_solar`, `<country>_wind`
(onshore + offshore). Countries without a reported solar or wind series have
no column.

**Processing.** Extracted from the full 2018–2025 generation download (solar
and the sum of onshore and offshore wind, 22 analysis countries, 2025).

## Solar and wind production (model) — `GENeSYS_MOD_vre_production_2025.csv`

**Source.** GENeSYS-MOD EU-EnVis-2060 v1.2.0 production output
(`output_production.csv`, 1.08 GB, not included).

**Columns.** `Model Version`, `PathwayScenario`, `Region`, `carrier`
(`solar` = all PV technologies, `wind` = all wind technologies of the power
sector), `Timeslice` (hour of the model year of the 72 representative
timeslices), `production` (PJ).

**Processing.** Extracted for model year 2025, power sector, 22 analysis
countries and all four scenarios, summing production over all PV and all wind
technologies (the analysis uses GoRES = `Green_CO2_exo_globalLimit`).

## References

- Barani, M., et al. (2025). European Energy Vision 2060: Charting diverse
  pathways for Europe's energy transition. arXiv:2501.12993.
- ENTSO-E (2026). ENTSO-E Transparency Platform. <https://transparency.entsoe.eu/>
- Löffler, K., et al. (2017). Designing a model for the global energy system —
  GENeSYS-MOD: An application of the Open-Source Energy Modeling System
  (OSeMOSYS). *Energies*, 10(10), 1468.
