"""
run_all.py  —  Full replication pipeline

Executes every analysis script in order and reproduces all tables, figures,
and numbers reported in the paper from the input data in data/. Run from any
directory:

    python scripts/run_all.py

Expected runtime: 5–10 minutes on a standard laptop. Outputs are written to
results/ (figures, tables, intermediate), which is created on the first run.

The data-preparation script prepare_vre_generation.py is not run here; it
documents how two files in data/ were extracted from large raw source files
that are not included (see data/README.md).
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# Force UTF-8 output on Windows (avoids cp1252 encoding errors)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPTS_DIR = Path(__file__).parent
DATA_DIR    = SCRIPTS_DIR.parent / "data"
PYTHON      = sys.executable
ENV         = {**os.environ, "PYTHONIOENCODING": "utf-8", "MPLBACKEND": "Agg"}

REQUIRED_DATA = [
    "ENTSOE_day_ahead_prices.csv",
    "GENeSYS_MOD_prices.csv",
    "ENTSOE_vre_generation_2025.csv",
    "GENeSYS_MOD_vre_production_2025.csv",
]

STEPS = [
    # ── Stage 1 and Stage 2 statistics ───────────────────────────────────────
    ("stage1_kruskal_wallis.py",                "Stage 1: Kruskal-Wallis tests (inputs to Table 6)"),
    ("stage2_t_tests.py",                       "Stage 2: group t-tests (inputs to Tables 7, C.3; Figures 6, 7)"),
    # ── Pearson correlations ─────────────────────────────────────────────────
    ("compute_entsoe_cross_year_pearson.py",    "ENTSO-E cross-year Pearson (Table 8, C.4; Figures 8, 9, C.5-C.9)"),
    ("compute_entsoe_cross_country_pearson.py", "ENTSO-E cross-country Pearson (Table 4; Figure C.1)"),
    ("compute_genesys_cross_country_pearson.py","GENeSYS-MOD cross-country Pearson (Table 4)"),
    ("compute_genesys_vs_entsoe_year_pearson.py","GENeSYS-MOD vs. ENTSO-E Pearson by year (Figures 9, C.6-C.9)"),
    ("compute_extended_years_pearson.py",       "GENeSYS-MOD vs. ENTSO-E Pearson, model years 2018-2060 (Section 3.4.2 footnote)"),
    ("stage3_pearson_correlations.py",          "Stage 3: profile correlations (Section 3.4.3; Figure C.10)"),
    # ── Compression factors and value factors ────────────────────────────────
    ("compute_compression_factors.py",          "Compression factors xi (Tables 11, C.5, C.6)"),
    ("compute_value_factors.py",                "Solar and wind value factors (Section 4.2)"),
    # ── Tables and values quoted in the text ─────────────────────────────────
    ("figure_1_france_patterns.py",             "Figure 1 coordinates"),
    ("table_4_country_clusters.py",             "Table 4 and footnote"),
    ("table_5_distribution_metrics.py",         "Table 5 and Section 3.1 values"),
    ("tables_stage1_stage2.py",                 "Tables 6, 7, C.3"),
    ("tables_benchmark.py",                     "Table 8 values, Table C.4, Sections 3.4.1-3.4.3"),
    ("tables_spreads.py",                       "Tables 9, 11, C.5, C.6 and Section 4.2 spreads"),
    # ── Figures (main text) ──────────────────────────────────────────────────
    ("plot_annual_mean_prices.py",              "Figure 4"),
    ("plot_price_duration_curves.py",           "Figure 5"),
    ("plot_dimension_profiles.py",              "Figure 6"),
    ("plot_compression_factors.py",             "Figure 7"),
    ("plot_pearson_stability_decay.py",         "Figure 8"),
    ("plot_pearson_alignment_heatmap.py",       "Figure 9"),
    # ── Figures (Appendix C) ─────────────────────────────────────────────────
    ("plot_country_clusters.py",                "Figure C.1"),
    ("plot_price_distribution.py",              "Figure C.2"),
    ("plot_genesys_cross_scenario_heatmap.py",  "Figure C.3"),
    ("plot_genesys_cross_year_heatmap.py",      "Figure C.4"),
    ("plot_entsoe_cross_year_heatmap.py",       "Figure C.5"),
    ("plot_pearson_benchmark.py",               "Figures C.6-C.9"),
    ("plot_pearson_vs_spearman.py",             "Figure C.10"),
]


def run(script: str, description: str, i: int, n: int) -> None:
    print(f"\n{'=' * 70}")
    print(f"  [{i}/{n}] {description}")
    print(f"  {script}")
    print(f"{'=' * 70}", flush=True)
    t0 = time.time()
    result = subprocess.run([PYTHON, str(SCRIPTS_DIR / script)], check=False,
                            env=ENV, cwd=SCRIPTS_DIR)
    if result.returncode != 0:
        print(f"\n[FAILED] {script} exited with code {result.returncode}")
        sys.exit(result.returncode)
    print(f"  Done in {time.time() - t0:.1f}s", flush=True)


def main():
    missing = [f for f in REQUIRED_DATA if not (DATA_DIR / f).exists()]
    if missing:
        print("[ERROR] Missing input data in data/:")
        for f in missing:
            print(f"  - {f}")
        print("See data/README.md.")
        sys.exit(1)

    t0 = time.time()
    for i, (script, description) in enumerate(STEPS, start=1):
        run(script, description, i, len(STEPS))

    print(f"\n{'=' * 70}")
    print(f"  All steps completed in {(time.time() - t0) / 60:.1f} min.")
    print("  Figures:              results/figures/")
    print("  Tables and values:    results/tables/")
    print("  Intermediate results: results/intermediate/")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
