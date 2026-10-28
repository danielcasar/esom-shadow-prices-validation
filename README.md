# Replication Package

**"Can shadow prices from energy system optimization models serve as reliable electricity price indicators?"**

Daniel Cäsar¹, Anne Neumann², Sebastian Zwickl-Bernhard¹,²
¹ Energy System Economics Lab, Institute of Net-Zero Energy Systems, Technische Universität Wien, Austria
² Department of Industrial Economics and Technology Management, Norwegian University of Science and Technology, Trondheim, Norway

Corresponding author: Daniel Cäsar — daniel.caesar@tuwien.ac.at

This package contains all data and code needed to reproduce every table,
figure, and number reported in the paper. Table and figure numbers below refer
to the revised manuscript (appendices A–C).

---

## Quick start

```bash
pip install -r requirements.txt
python scripts/run_all.py
```

`run_all.py` runs the complete analysis (29 steps, 5–10 minutes on a
standard laptop) from the data in `data/` and writes all outputs to `results/`.

**Software.** Tested with Python 3.14.3 on Windows 11 using the package
versions pinned in `requirements.txt` (pandas 3.0.0, numpy 2.4.2,
scipy 1.17.0, matplotlib 3.10.8). Figures use the Arial font; matplotlib falls
back to its default font if Arial is not installed, which changes only the
typeface.

**Determinism.** All computations are deterministic. Bootstrap confidence
intervals use `numpy.random.default_rng(42)` with 10,000 draws.

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

Every exhibit is produced by the scripts listed below, all called by
`run_all.py`. Figures are written to `results/figures/`, tables to
`results/tables/`.

### Main text

| Exhibit | Script(s) | Output |
|---------|-----------|--------|
| Figure 1 | `figure_1_france_patterns.py` | `Figure_1_data.csv` (coordinates; the figure is drawn with pgfplots in the manuscript) |
| Figures 2–3, Tables 1–3 | — | Conceptual figures and descriptive tables, no computation |
| Table 4 | `compute_entsoe_cross_country_pearson.py`, `compute_genesys_cross_country_pearson.py`, `table_4_country_clusters.py` | `Table_4.csv` |
| Table 5 | `table_5_distribution_metrics.py` | `Table_5.csv` |
| Figure 4 | `plot_annual_mean_prices.py` | `Figure_4.pdf` |
| Figure 5 | `plot_price_duration_curves.py` | `Figure_5.pdf` |
| Figure 6 | `stage2_t_tests.py`, `plot_dimension_profiles.py` | `Figure_6.pdf` |
| Table 6 | `stage1_kruskal_wallis.py`, `tables_stage1_stage2.py` | `Table_6.csv` |
| Table 7 | `stage2_t_tests.py`, `tables_stage1_stage2.py` | `Table_7.csv` |
| Figure 7 | `stage2_t_tests.py`, `plot_compression_factors.py` | `Figure_7.pdf` |
| Figure 8 | `compute_entsoe_cross_year_pearson.py`, `plot_pearson_stability_decay.py` | `Figure_8.pdf` |
| Table 8 | `tables_benchmark.py` | `values_tables_benchmark.csv` |
| Figure 9 | `compute_genesys_vs_entsoe_year_pearson.py`, `plot_pearson_alignment_heatmap.py` | `Figure_9.pdf` |
| Table 9 | `tables_spreads.py` | `Table_9.csv` (model and ENTSO-E columns; literature ranges are taken from the cited studies) |
| Table 10 | — | Guidelines derived from Figures 9, C.6–C.9 and Table C.5 |
| Table 11 | `compute_compression_factors.py`, `tables_spreads.py` | `Table_11.csv` |

### Appendix C

| Exhibit | Script(s) | Output |
|---------|-----------|--------|
| Tables C.1–C.2 | — | Limitations and country list, no computation |
| Figure C.1 | `plot_country_clusters.py` | `Figure_C1.pdf` |
| Table C.3 | `tables_stage1_stage2.py` | `Table_C3.csv` |
| Figure C.2 | `plot_price_distribution.py` | `Figure_C2.pdf` |
| Figure C.3 | `plot_genesys_cross_scenario_heatmap.py` | `Figure_C3.pdf` |
| Figure C.4 | `plot_genesys_cross_year_heatmap.py` | `Figure_C4.pdf` |
| Figure C.5 | `plot_entsoe_cross_year_heatmap.py` | `Figure_C5.pdf` |
| Table C.4 | `tables_benchmark.py` | `Table_C4.csv` |
| Figures C.6–C.9 | `plot_pearson_benchmark.py` | `Figure_C6.pdf` … `Figure_C9.pdf` |
| Figure C.10 | `stage3_pearson_correlations.py`, `plot_pearson_vs_spearman.py` | `Figure_C10.pdf` |
| Table C.5 | `compute_compression_factors.py`, `tables_spreads.py` | `Table_C5.csv` |
| Table C.6 | `tables_spreads.py` | `Table_C6.csv` |

### Numbers quoted in the text

| Location | Script | Output |
|----------|--------|--------|
| Abstract (compression factors) | `table_5_distribution_metrics.py` | `values_table_5_distribution_metrics.csv` |
| Section 2.2.3 (footnote on shared price nodes) | `table_4_country_clusters.py` | `values_table_4_country_clusters.csv` |
| Section 3.1 (ranges for Figures 4–6) | `table_5_distribution_metrics.py` | `values_table_5_distribution_metrics.csv` |
| Section 3.2 (effect-size ratios, non-significant combinations) | `tables_stage1_stage2.py` | `values_tables_stage1_stage2.csv`, console |
| Section 3.4.1 (bootstrap CI widths) | `tables_benchmark.py` | `bootstrap_ci_by_lag.csv` |
| Section 3.4.2 (footnote on model years after 2030) | `compute_extended_years_pearson.py`, `tables_benchmark.py` | `values_tables_benchmark.csv` |
| Section 3.4.3 (Pearson vs. Spearman MAE) | `tables_benchmark.py` | `values_tables_benchmark.csv` |
| Section 4.2 (daily spreads) | `tables_spreads.py` | `values_tables_spreads.csv` |
| Section 4.2 (value factors) | `compute_value_factors.py` | `values_compute_value_factors.csv` |

Each `values_*.csv` in `results/tables/` lists `exhibit, item, value` for the
numbers a script contributes to the paper.

---

## Data preparation (not part of `run_all.py`)

`prepare_vre_generation.py` documents how the two small solar/wind files in
`data/` were extracted from the full ENTSO-E generation file (139 MB) and the
GENeSYS-MOD production output (1.08 GB), which are not included. It is not
needed for the replication.

The retrieval and processing of all input files are described in
`data/README.md`. A fresh ENTSO-E download can differ slightly from the
shipped files because ENTSO-E revises published data; use the shipped files to
reproduce the paper.

---

## License and citation

Code: MIT License (`LICENSE`). Data: subject to the terms of the original
sources listed in `data/README.md`. Please cite the paper when using this
package (`CITATION.cff`).
