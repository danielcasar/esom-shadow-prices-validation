# Replication Package

**"Can shadow prices from energy system optimization models serve as reliable electricity price indicators?"**

Daniel Cäsar¹, Anne Neumann², Sebastian Zwickl-Bernhard¹,²
¹ Energy System Economics Lab, Institute of Net-Zero Energy Systems, Technische Universität Wien, Austria
² Department of Industrial Economics and Technology Management, Norwegian University of Science and Technology, Trondheim, Norway

Corresponding author: Daniel Cäsar — caesar@eselab.tuwien.ac.at

This package contains all data and code needed to reproduce every table,
figure, and number reported in the paper. Table and figure numbers below refer
to the revised manuscript (appendices A–C).

---

## Overview

The paper compares the temporal structure of hourly shadow prices from the
energy system optimization model GENeSYS-MOD with observed ENTSO-E day-ahead
prices for 22 European countries, at four temporal resolutions (hour of day,
day of week, month of year, season). The analysis has three stages, which the
scripts follow:

1. **Pattern existence:** Kruskal–Wallis tests per country, scenario, and
   resolution (`stage1_kruskal_wallis.py`).
2. **Pattern magnitude:** one-sample t-tests of each calendar group against
   the annual mean, giving the group-mean deviation profiles and the
   compression factors (`stage2_t_tests.py`, `compute_compression_factors.py`).
3. **Pattern alignment:** Pearson correlations between model and market
   profiles, benchmarked against the correlation between observed market
   years (`compute_benchmark_correlations.py`,
   `compute_model_market_correlations.py`, `stage3_pearson_correlations.py`).

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
data/                 Input data (all included; see data/README.md)
scripts/              All analysis, table, and figure scripts
├── config.py         Countries, years, scenarios, clusters, paths
├── run_all.py        Single entry point for the full replication
└── ...
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

**Tables.** `tables.py` produces all computed tables from the intermediate
results and writes them to `results/tables/Table_<number>.csv` (e.g.
`Table_C5.csv`). It also writes every number quoted in the text, each labelled
with its location in the paper, to `results/tables/values_tables.csv`; the
value factors (Section 4.2) come from `compute_value_factors.py`.

**Figures.** Each figure has its own script, which writes
`results/figures/Figure_<number>.pdf`:

| Figure | Script |
|--------|--------|
| 1 | `tables.py` (coordinates in `Figure_1_data.csv`; the figure is drawn in the manuscript) |
| 4 | `plot_annual_mean_prices.py` |
| 5 | `plot_price_duration_curves.py` |
| 6 | `plot_dimension_profiles.py` |
| 7 | `plot_compression_factors.py` |
| 8 | `plot_pearson_stability_decay.py` |
| 9 | `plot_pearson_alignment_heatmap.py` |
| C.1 | `plot_country_clusters.py` |
| C.2 | `plot_price_distribution.py` |
| C.3 | `plot_genesys_cross_scenario_heatmap.py` |
| C.4 | `plot_genesys_cross_year_heatmap.py` |
| C.5 | `plot_entsoe_cross_year_heatmap.py` |
| C.6–C.9 | `plot_pearson_benchmark.py` |
| C.10 | `plot_pearson_vs_spearman.py` |

---

## License and citation

Code: MIT License (`LICENSE`). Data: subject to the terms of the original
sources listed in `data/README.md`. Please cite the paper when using this
package (`CITATION.cff`).
