# Replication Package

**"Can shadow prices from energy system optimization models serve as reliable electricity price indicators?"**

Daniel Cäsar¹, Anne Neumann², Sebastian Zwickl-Bernhard¹,²
¹ Energy System Economics Lab, Institute of Net-Zero Energy Systems, Technische Universität Wien, Austria
² Department of Industrial Economics and Technology Management, Norwegian University of Science and Technology, Trondheim, Norway

Corresponding author: Daniel Cäsar — caesar@eselab.tuwien.ac.at

This package contains all data and code needed to reproduce every table,
figure, and number reported in the paper.

---

## Overview

The paper compares the temporal structure of hourly shadow prices from the
energy system optimization model GENeSYS-MOD with observed ENTSO-E day-ahead
prices for 22 European countries, at four temporal resolutions (hour of day,
day of week, month of year, season). The analysis has three stages, which the
scripts follow:

1. **Pattern existence:** Kruskal–Wallis tests per country, scenario, and
   resolution (script 01).
2. **Pattern magnitude:** one-sample t-tests of each calendar group against
   the annual mean, giving the group-mean deviation profiles and the
   compression factors (scripts 02 and 06).
3. **Pattern alignment:** Pearson correlations between model and market
   profiles, benchmarked against the correlation between observed market
   years (scripts 03–05).

The methods are described in Section 2 of the paper.

---

## Quick start

```bash
pip install -r requirements.txt
python scripts/run_all.py
```

`run_all.py` runs the complete analysis from the data in `data/` and writes all outputs to `results/`.

---

## Repository structure

```
data/                                       Input data (all included; see data/README.md)
scripts/
├── run_all.py                              Runs all scripts below in order
├── config.py                               Settings: countries, years, scenarios, clusters, paths
├── helpers.py                              Helper functions for saving tables and numbers
├── 01_stage1_kruskal_wallis.py             Stage 1: Kruskal–Wallis tests
├── 02_stage2_t_tests.py                    Stage 2: t-tests per calendar group
├── 03_stage3_benchmark_correlations.py     Stage 3: correlations between years and countries
├── 04_stage3_model_market_correlations.py  Stage 3: correlations between model and market
├── 05_stage3_pearson_vs_spearman.py        Stage 3: robustness check
├── 06_compression_factors.py               Compression factors
├── 07_value_factors.py                     Value factors (Section 4.2)
├── 08_tables.py                            All tables and the numbers quoted in the text
└── figure_<number>_<topic>.py              One script per figure, e.g. figure_C03_scenario_correlations.py
```

Running `run_all.py` creates `results/` with three subfolders:
`figures/` (figures, named by paper number), `tables/` (tables and the
numbers quoted in the text, as CSV), and `intermediate/` (intermediate
results).

---

## Data availability

All data are included in `data/`; `data/README.md` documents sources,
retrieval dates, variables, units, processing steps, and checksums.

| File | Source |
|------|--------|
| `ENTSOE_day_ahead_prices.csv` | ENTSO-E Transparency Platform, day-ahead prices [12.1.D], 2015–2025 |
| `ENTSOE_vre_generation_2025.csv` | ENTSO-E Transparency Platform, actual generation per production type [16.1.B&C], 2025 |
| `GENeSYS_MOD_prices.csv` | GENeSYS-MOD shadow prices (Löffler et al., 2017) for the EnVis-2060 scenarios (Barani et al., 2025), 2018–2060 |
| `GENeSYS_MOD_vre_production_2025.csv` | GENeSYS-MOD EU-EnVis-2060 v1.2.0 solar and wind production, 2025 |

ENTSO-E data are redistributed with attribution as required by the ENTSO-E
Transparency Platform terms of use.

---

## Output mapping

All outputs are named by their number in the paper.

- **Tables:** `08_tables.py` writes every computed table to
  `results/tables/Table_<number>.csv` (e.g. `Table_C5.csv`), and every number
  quoted in the text, labelled with its location in the paper, to
  `results/tables/values_tables.csv`. The value factors (Section 4.2) come
  from `07_value_factors.py`.
- **Figures:** each script `figure_<number>_<topic>.py` writes
  `results/figures/Figure_<number>.pdf`. Figure 1 is drawn in the manuscript
  from the coordinates in `results/figures/Figure_1_data.csv` (written by
  `08_tables.py`).

---

## License and citation

Code: MIT License (`LICENSE`). Data: subject to the terms of the original
sources listed in `data/README.md`. Please cite the paper when using this
package (`CITATION.cff`).
